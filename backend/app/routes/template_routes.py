# =============================================================================
# routes/template_routes.py
# =============================================================================
# API for the Sprint 5 "Clone-from-Template" feature.
#
# A teacher publishes a golden VM as a template, then ASSIGNS it to a class.
# Students see assigned templates on their Deploy page and create VMs on
# demand (self-serve). The old "distribute" (auto-deploy to all students)
# is retained as a secondary option for urgent scenarios.
#
# Admin endpoints:
#   POST   /templates                      → publish a template from a VM
#   GET    /templates                      → list templates
#   GET    /templates/{id}                 → template detail
#   PATCH  /templates/{id}                 → update / archive a template
#   POST   /templates/{id}/assign          → grant class access (no VMs)
#   POST   /templates/{id}/distribute      → bulk-clone to a class (legacy)
#   POST   /templates/{id}/revoke          → revoke student access
#   GET    /templates/{id}/assignments     → list assignments for a template
#   GET    /clone-batches/{id}             → live per-student clone progress
#
# Student + Admin endpoints:
#   GET    /templates/available            → student's assigned templates
#   POST   /templates/{id}/deploy          → deploy one VM from template
#
# See docs/design/clone-templates-architecture.md
# =============================================================================

import logging
import os
import re
import time
import uuid
from contextlib import contextmanager
from typing import List

import redis
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user, require_admin
from app.models.user import UserInDB
from app.models.template import (
    CloneMode,
    TemplateStatus,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplateResponse,
    DeployFromTemplateRequest,
    DistributeRequest,
    BatchResponse,
    BatchProgressResponse,
    AssignRequest,
    StudentTemplateResponse,
    AssignmentResponse,
    AssignmentCountResponse,
)
from app.models.vm import VMJobResponse
from app.proxmox_client import ProxmoxClient
from app.tasks.clone_tasks import (
    build_template,
    clone_template_for_student,
    deploy_template_for_user,
)
from db import database
from db import templates as tdb

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Templates & Cloning"])

proxmox = ProxmoxClient()

# Proxmox node clones are created on. Same default as VMCreateRequest.
_DEFAULT_NODE = os.getenv("PROXMOX_NODE", "home")

# Teacher-distributed clones are managed by the teacher, not the 2h auto-expire
# scheduler. None disables auto-expiry; override with CLONE_LEASE_HOURS to set a
# finite lease instead.
_CLONE_LEASE_HOURS_ENV = os.getenv("CLONE_LEASE_HOURS", "").strip()
_CLONE_LEASE_HOURS: int | None = int(_CLONE_LEASE_HOURS_ENV) if _CLONE_LEASE_HOURS_ENV else None

# Redis client for the cross-request VMID allocation lock.
_redis = redis.Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"))
_VMID_LOCK_KEY = "privatecloud:lock:vmid_alloc"


@contextmanager
def _vmid_allocation_lock(timeout: int = 30):
    """
    Serialise VMID allocation across concurrent distribute requests so two bulk
    clones can't read the same in-use set and hand out overlapping VMIDs. The
    lock is best-effort: if Redis is unreachable we proceed (degraded), since
    the DB-reserved exclusion in get_free_vmids still covers the common case.
    """
    token = str(uuid.uuid4())
    acquired = False
    try:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if _redis.set(_VMID_LOCK_KEY, token, nx=True, ex=timeout):
                acquired = True
                break
            time.sleep(0.2)
        yield acquired
    finally:
        # Only release if we still hold it (best-effort; lock self-expires via ex).
        if acquired:
            try:
                if _redis.get(_VMID_LOCK_KEY) == token.encode():
                    _redis.delete(_VMID_LOCK_KEY)
            except redis.RedisError:
                pass


def _slug(text: str) -> str:
    """Lowercase, hyphenated, DNS-safe fragment for VM names."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s or "vm"


def _student_vm_name(template_name: str, username: str) -> str:
    """
    Build a Proxmox-safe VM name (<=30 chars, letters/digits/hyphens) for a
    student's clone, e.g. "ml-lab-alice". Truncated to satisfy vm_name rules.
    """
    name = f"{_slug(template_name)}-{_slug(username)}"
    return name[:30].rstrip("-") or "clone-vm"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_template(
    req: TemplateCreateRequest,
    admin: UserInDB = Depends(require_admin),
):
    """
    Publish a DEDICATED Proxmox template from one of the admin's VMs.

    Unlike the old behaviour (which only registered a row pointing at a running
    VM), this now builds a real, standalone Proxmox template — exactly like the
    global golden images 9000/9001, but private/scoped to this template row:

      1. Allocate a fresh VMID for the dedicated template.
      2. Create the row in 'building' status.
      3. A Celery task full-clones the source → that VMID, then freezes it with
         `qm template`. The admin's source VM is left untouched and usable.

    Returns 202 immediately; the row flips to 'published' (or 'failed') when the
    background build finishes. Both full and linked clones work off the frozen
    template afterwards.
    """
    source_job = database.get_vm_job(req.vm_job_id)
    if not source_job:
        raise HTTPException(status_code=404, detail=f"Source VM job {req.vm_job_id} not found.")
    # An admin is the platform operator and may publish ANY VM as a template,
    # regardless of which user created it. (No ownership restriction — by design.)
    if not source_job.get("vmid"):
        raise HTTPException(status_code=400, detail="Source VM has no Proxmox VMID yet.")
    if source_job["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Source VM must be in 'done' status (current: {source_job['status']}).",
        )

    source_vmid = source_job["vmid"]
    os_choice = source_job["os_choice"]

    # Allocate a dedicated VMID for the new Proxmox template under the same
    # cross-request lock the distribute path uses, excluding VMIDs already
    # reserved in our DB (queued clones + other building templates).
    with _vmid_allocation_lock() as locked:
        if not locked:
            logger.warning("Proceeding with template VMID allocation WITHOUT lock (Redis unavailable).")
        try:
            proxmox._ensure_authenticated()
            template_vmid = proxmox.get_free_vmids(
                count=1,
                node=_DEFAULT_NODE,
                extra_reserved=database.get_reserved_vmids(),
            )[0]
        except Exception as exc:
            logger.error("Could not allocate a VMID for the template: %s", exc)
            raise HTTPException(status_code=502, detail="Could not reach Proxmox to allocate a VMID.")

        row = tdb.create_template(
            owner_id=admin.id,
            name=req.name,
            source_vmid=source_vmid,
            template_vmid=template_vmid,
            os_choice=os_choice,
            description=req.description,
            clone_mode=req.clone_mode.value,
            default_cpu=req.default_cpu,
            default_ram_mb=req.default_ram_mb,
            status=TemplateStatus.building.value,
        )

    template_name = f"tmpl-{_slug(req.name)}"[:30].rstrip("-") or f"tmpl-{template_vmid}"
    build_template.delay(
        template_id=row["id"],
        owner_id=admin.id,
        source_vmid=source_vmid,
        template_vmid=template_vmid,
        template_name=template_name,
        node=_DEFAULT_NODE,
    )

    database.log_action(
        user_id=admin.id, action_type="template.create",
        action="template.create", target_type="vm_template",
        target_id=str(row["id"]),
        details={
            "name": req.name, "source_vmid": source_vmid,
            "template_vmid": template_vmid, "clone_mode": req.clone_mode.value,
        },
    )
    logger.info(
        "Building template %d '%s': source vmid=%d → template vmid=%d.",
        row["id"], req.name, source_vmid, template_vmid,
    )
    return TemplateResponse.model_validate(row)


@router.get("/templates", response_model=List[TemplateResponse])
def list_templates(
    include_archived: bool = False,
    admin: UserInDB = Depends(require_admin),
):
    return [TemplateResponse.model_validate(t) for t in tdb.list_templates(include_archived)]


# ---------------------------------------------------------------------------
# Student-facing: list available templates
# (Must be declared BEFORE /templates/{template_id} so FastAPI doesn't try to
# parse "available" as an int template_id.)
# ---------------------------------------------------------------------------

@router.get("/templates/available", response_model=List[StudentTemplateResponse])
def list_available_templates(
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Return templates assigned to the current user that are still deployable.

    Used by the student's Deploy page to show template cards. Admins can also
    call this but typically use the full /templates list instead.
    """
    rows = tdb.list_student_assignments(current_user.id)
    return [StudentTemplateResponse.model_validate(r) for r in rows]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(template_id: int, admin: UserInDB = Depends(require_admin)):
    row = tdb.get_template(template_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found.")
    return TemplateResponse.model_validate(row)


@router.patch("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    req: TemplateUpdateRequest,
    admin: UserInDB = Depends(require_admin),
):
    if not tdb.get_template(template_id):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found.")
    row = tdb.update_template(
        template_id,
        name=req.name,
        description=req.description,
        clone_mode=req.clone_mode.value if req.clone_mode else None,
        default_cpu=req.default_cpu,
        default_ram_mb=req.default_ram_mb,
        status=req.status.value if req.status else None,
    )
    return TemplateResponse.model_validate(row)


# ---------------------------------------------------------------------------
# Distribution — bulk clone to a class
# ---------------------------------------------------------------------------

@router.post(
    "/templates/{template_id}/distribute",
    response_model=BatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"description": "Template or class not found"},
        400: {"description": "Class has no enrolled students / template archived"},
        502: {"description": "Could not reach Proxmox to allocate VMIDs"},
    },
)
def distribute_template(
    template_id: int,
    req: DistributeRequest,
    admin: UserInDB = Depends(require_admin),
):
    """
    Clone `template_id` to every active student enrolled in `req.class_id`.

    Pre-allocates one distinct VMID per student up-front (so concurrent Celery
    clone tasks never collide), creates the vm_jobs + clone_jobs rows, then
    fans out one clone task per student. Quota is intentionally NOT checked —
    teacher distribution bypasses the per-student daily limit.
    """
    template = tdb.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found.")
    if template["status"] == TemplateStatus.archived.value:
        raise HTTPException(status_code=400, detail="Cannot distribute an archived template.")
    # The dedicated Proxmox template must have finished building before we can
    # clone from it. Block draft/building/failed templates.
    if template["status"] != TemplateStatus.published.value or not template.get("template_vmid"):
        raise HTTPException(
            status_code=400,
            detail=f"Template is not ready to distribute (status: {template['status']}).",
        )

    if not tdb.get_class(req.class_id):
        raise HTTPException(status_code=404, detail=f"Class {req.class_id} not found.")

    # Resolve effective specs + clone mode (request overrides template defaults).
    # The template is a real Proxmox template, so both full and linked clones
    # work off it regardless of how it was published.
    cpu_cores = req.cpu_cores or template["default_cpu"]
    ram_mb = req.ram_mb or template["default_ram_mb"]
    clone_mode = (req.clone_mode.value if req.clone_mode else template["clone_mode"])
    full = (clone_mode == CloneMode.full.value)
    template_vmid = template["template_vmid"]
    os_choice = template["os_choice"]

    # Guard: block accidental double-distribution (double-click / retry) which
    # would give every student a second identical clone.
    if tdb.get_active_batch(template_id, req.class_id):
        raise HTTPException(
            status_code=409,
            detail="A distribution for this template and class is already in progress.",
        )

    student_ids = tdb.get_enrolled_student_ids(req.class_id)
    if not student_ids:
        raise HTTPException(status_code=400, detail="Class has no enrolled (active) students.")

    # Build a username map up-front to avoid an N+1 lookup inside the loop.
    students = tdb.list_class_students(req.class_id)
    username_by_id = {s["id"]: s["username"] for s in students}

    # Allocate VMIDs + create rows under a cross-request lock so two concurrent
    # distributes never hand out overlapping VMIDs. get_free_vmids also excludes
    # VMIDs already reserved in our DB (queued clones not yet on Proxmox).
    with _vmid_allocation_lock() as locked:
        if not locked:
            logger.warning("Proceeding with VMID allocation WITHOUT lock (Redis unavailable).")
        try:
            proxmox._ensure_authenticated()
            vmids = proxmox.get_free_vmids(
                count=len(student_ids),
                node=_DEFAULT_NODE,
                extra_reserved=database.get_reserved_vmids(),
            )
        except Exception as exc:
            logger.error("Could not allocate VMIDs for distribution: %s", exc)
            raise HTTPException(status_code=502, detail="Could not reach Proxmox to allocate VMIDs.")

        batch = tdb.create_batch(
            template_id=template_id,
            class_id=req.class_id,
            initiated_by=admin.id,
            clone_mode=clone_mode,
            cpu_cores=cpu_cores,
            ram_mb=ram_mb,
            total=len(student_ids),
        )

        dispatch: list[dict] = []
        for student_id, new_vmid in zip(student_ids, vmids):
            username = username_by_id.get(student_id, f"user{student_id}")
            vm_name = _student_vm_name(template["name"], username)

            request_payload = {
                "vm_name": vm_name,
                "os_choice": os_choice,
                "cpu_cores": cpu_cores,
                "ram_mb": ram_mb,
                "node": _DEFAULT_NODE,
                "cloned_from_template": template_id,
                "batch_id": batch["id"],
            }
            # Clones are teacher-managed — disable the 2h auto-expire scheduler.
            vm_job_id = database.create_vm_job(
                user_id=student_id,
                vmid=new_vmid,
                vm_name=vm_name,
                os_choice=os_choice,
                request_payload=request_payload,
                expiry_hours=_CLONE_LEASE_HOURS,
            )
            clone_job_id = tdb.create_clone_job(batch_id=batch["id"], student_id=student_id)
            tdb.update_clone_job(clone_job_id, "queued", vm_job_id=vm_job_id)
            dispatch.append({
                "clone_job_id": clone_job_id, "vm_job_id": vm_job_id,
                "student_id": student_id, "new_vmid": new_vmid, "vm_name": vm_name,
            })

    # Fan out the Celery tasks AFTER the rows are committed and the lock is
    # released — the VMIDs are now reserved in our DB so it's safe.
    for d in dispatch:
        clone_template_for_student.delay(
            clone_job_id=d["clone_job_id"],
            vm_job_id=d["vm_job_id"],
            batch_id=batch["id"],
            student_id=d["student_id"],
            template_vmid=template_vmid,
            new_vmid=d["new_vmid"],
            vm_name=d["vm_name"],
            os_choice_value=os_choice,
            cpu_cores=cpu_cores,
            ram_mb=ram_mb,
            node=_DEFAULT_NODE,
            full=full,
        )

    database.log_action(
        user_id=admin.id, action_type="template.distribute",
        action="template.distribute", target_type="clone_batch",
        target_id=str(batch["id"]),
        details={
            "template_id": template_id, "class_id": req.class_id,
            "students": len(student_ids), "clone_mode": clone_mode,
        },
    )
    logger.info(
        "Distributed template %d to class %d: %d clones queued (batch %d).",
        template_id, req.class_id, len(student_ids), batch["id"],
    )
    return BatchResponse.model_validate(batch)


@router.get("/clone-batches/{batch_id}", response_model=BatchProgressResponse)
def get_batch_progress(batch_id: int, admin: UserInDB = Depends(require_admin)):
    batch = tdb.get_batch_progress(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found.")
    return BatchProgressResponse.model_validate(batch)


# ---------------------------------------------------------------------------
# Assign template to a class (student self-serve — no VMs created)
# ---------------------------------------------------------------------------

@router.post(
    "/templates/{template_id}/assign",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"description": "Template or class not found"},
        400: {"description": "Template not ready / class empty"},
    },
)
def assign_template(
    template_id: int,
    req: AssignRequest,
    admin: UserInDB = Depends(require_admin),
):
    """
    Grant every student in `class_id` access to deploy from this template.

    This is a metadata-only operation — zero Proxmox calls, instant, no VMs
    created. Students will see the template on their Deploy page and create
    VMs on demand. Idempotent: re-assigning resets revoked assignments.
    """
    template = tdb.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found.")
    if template["status"] != TemplateStatus.published.value or not template.get("template_vmid"):
        raise HTTPException(
            status_code=400,
            detail=f"Template is not ready to assign (status: {template['status']}).",
        )
    if not tdb.get_class(req.class_id):
        raise HTTPException(status_code=404, detail=f"Class {req.class_id} not found.")

    cpu_cores = req.cpu_cores or template["default_cpu"]
    ram_mb = req.ram_mb or template["default_ram_mb"]
    clone_mode = (req.clone_mode.value if req.clone_mode else template["clone_mode"])

    student_ids = tdb.get_enrolled_student_ids(req.class_id)
    if not student_ids:
        raise HTTPException(status_code=400, detail="Class has no enrolled (active) students.")

    for sid in student_ids:
        tdb.create_or_update_assignment(
            template_id=template_id,
            student_id=sid,
            class_id=req.class_id,
            assigned_by=admin.id,
            cpu_cores=cpu_cores,
            ram_mb=ram_mb,
            clone_mode=clone_mode,
        )

    database.log_action(
        user_id=admin.id, action_type="template.distribute",
        action="template.assign", target_type="vm_template",
        target_id=str(template_id),
        details={
            "class_id": req.class_id, "students": len(student_ids),
            "cpu_cores": cpu_cores, "ram_mb": ram_mb, "clone_mode": clone_mode,
        },
    )
    logger.info(
        "Assigned template %d to class %d: %d students granted access.",
        template_id, req.class_id, len(student_ids),
    )
    return {"assigned": len(student_ids), "template_id": template_id, "class_id": req.class_id}




# ---------------------------------------------------------------------------
# Revoke assignment
# ---------------------------------------------------------------------------

@router.post(
    "/templates/{template_id}/revoke",
    status_code=200,
)
def revoke_template_assignments(
    template_id: int,
    admin: UserInDB = Depends(require_admin),
):
    """
    Revoke all 'available' assignments for a template. Already-deployed VMs
    are unaffected (they live in vm_jobs independently).
    """
    assignments = tdb.list_template_assignments(template_id)
    revoked = 0
    for a in assignments:
        if a["status"] == "available":
            tdb.revoke_assignment(a["id"])
            revoked += 1
    logger.info("Revoked %d assignments for template %d.", revoked, template_id)
    return {"revoked": revoked, "template_id": template_id}


# ---------------------------------------------------------------------------
# Admin view: assignments for a template
# ---------------------------------------------------------------------------

@router.get(
    "/templates/{template_id}/assignments",
    response_model=List[AssignmentResponse],
)
def get_template_assignments(
    template_id: int,
    admin: UserInDB = Depends(require_admin),
):
    """List all assignments (any status) for a template."""
    if not tdb.get_template(template_id):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found.")
    rows = tdb.list_template_assignments(template_id)
    return [AssignmentResponse.model_validate(r) for r in rows]


@router.get(
    "/templates/{template_id}/assignments/count",
    response_model=AssignmentCountResponse,
)
def get_template_assignment_counts(
    template_id: int,
    admin: UserInDB = Depends(require_admin),
):
    """Quick summary counts for a template's assignments."""
    if not tdb.get_template(template_id):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found.")
    return AssignmentCountResponse.model_validate(tdb.count_template_assignments(template_id))


# ---------------------------------------------------------------------------
# Deploy a single VM from a template (admin OR student with assignment)
# ---------------------------------------------------------------------------

@router.post(
    "/templates/{template_id}/deploy",
    response_model=VMJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        403: {"description": "Student does not have access to this template"},
        404: {"description": "Template not found"},
        400: {"description": "Template not ready / not published"},
        409: {"description": "Student already deployed from this template"},
        502: {"description": "Could not reach Proxmox to allocate a VMID"},
    },
)
def deploy_template(
    template_id: int,
    req: DeployFromTemplateRequest,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Deploy ONE VM from a published template.

    - **Admin**: can deploy any published template (unchanged behaviour).
    - **Student**: can deploy only if they have an 'available' assignment for
      this template. On success the assignment is marked 'deployed'. Students
      can adjust CPU/RAM from the admin-set defaults.

    The VM lands in vm_jobs like any other provision, so the dashboard /
    console / RDP all work unchanged.
    """
    template = tdb.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found.")
    if template["status"] != TemplateStatus.published.value or not template.get("template_vmid"):
        raise HTTPException(
            status_code=400,
            detail=f"Template is not ready to deploy (status: {template['status']}).",
        )

    is_admin = current_user.role == "admin"
    assignment = None

    if not is_admin:
        # Student path: must have an assignment (available or previously deployed)
        assignment = tdb.get_assignment(template_id, current_user.id)
        if not assignment or assignment["status"] not in ("available", "deployed"):
            raise HTTPException(
                status_code=403,
                detail="You don't have access to deploy this template.",
            )

    # Resolve specs: student can override CPU/RAM from assignment defaults;
    # admin overrides from template defaults.
    if is_admin:
        cpu_cores = req.cpu_cores or template["default_cpu"]
        ram_mb = req.ram_mb or template["default_ram_mb"]
        clone_mode = (req.clone_mode.value if req.clone_mode else template["clone_mode"])
    else:
        cpu_cores = req.cpu_cores or assignment["cpu_cores"]
        ram_mb = req.ram_mb or assignment["ram_mb"]
        clone_mode = assignment["clone_mode"]

    full = (clone_mode == CloneMode.full.value)
    template_vmid = template["template_vmid"]
    os_choice = template["os_choice"]

    # Allocate a VMID under the cross-request lock (excludes DB-reserved ids).
    with _vmid_allocation_lock() as locked:
        if not locked:
            logger.warning("Proceeding with deploy VMID allocation WITHOUT lock (Redis unavailable).")
        try:
            proxmox._ensure_authenticated()
            new_vmid = proxmox.get_free_vmids(
                count=1,
                node=_DEFAULT_NODE,
                extra_reserved=database.get_reserved_vmids(),
            )[0]
        except Exception as exc:
            logger.error("Could not allocate a VMID for template deploy: %s", exc)
            raise HTTPException(status_code=502, detail="Could not reach Proxmox to allocate a VMID.")

        request_payload = {
            "vm_name": req.vm_name,
            "os_choice": os_choice,
            "cpu_cores": cpu_cores,
            "ram_mb": ram_mb,
            "node": _DEFAULT_NODE,
            "deployed_from_template": template_id,
        }
        # Assigned template deploys bypass the per-student daily quota (the
        # admin explicitly granted access) — use expiry_hours=None same as
        # teacher-distributed clones.
        vm_job_id = database.create_vm_job(
            user_id=current_user.id,
            vmid=new_vmid,
            vm_name=req.vm_name,
            os_choice=os_choice,
            request_payload=request_payload,
            expiry_hours=_CLONE_LEASE_HOURS,
        )

    deploy_template_for_user.delay(
        job_id=vm_job_id,
        user_id=current_user.id,
        template_vmid=template_vmid,
        new_vmid=new_vmid,
        vm_name=req.vm_name,
        os_choice_value=os_choice,
        cpu_cores=cpu_cores,
        ram_mb=ram_mb,
        node=_DEFAULT_NODE,
        full=full,
    )

    database.log_action(
        user_id=current_user.id, action_type="vm.create",
        action="template.deploy", target_type="vm_job",
        target_id=str(vm_job_id),
        details={
            "template_id": template_id, "template_vmid": template_vmid,
            "vmid": new_vmid, "vm_name": req.vm_name, "clone_mode": clone_mode,
            "is_student_deploy": not is_admin,
        },
    )
    logger.info(
        "Deploying template %d for %s '%s': template vmid=%d → new vmid=%d (job %d).",
        template_id, "student" if not is_admin else "admin",
        current_user.username, template_vmid, new_vmid, vm_job_id,
    )
    return VMJobResponse.model_validate(database.get_vm_job(vm_job_id))
