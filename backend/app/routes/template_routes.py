# =============================================================================
# routes/template_routes.py
# =============================================================================
# Admin-only API for the Sprint 5 "Clone-from-Template" feature.
#
# A teacher publishes a golden VM as a template, then distributes one clone
# per student to a whole class in a single action. The cloned VMs land in the
# existing vm_jobs table, so the student dashboard / console / RDP all keep
# working unchanged.
#
# Endpoints (all require admin):
#   POST   /templates                      → publish a template from a VM
#   GET    /templates                      → list templates
#   GET    /templates/{id}                 → template detail
#   PATCH  /templates/{id}                 → update / archive a template
#   POST   /templates/{id}/distribute      → bulk-clone to a class
#   GET    /clone-batches/{id}             → live per-student clone progress
#
# Teacher-distributed clones BYPASS the per-student daily quota by design —
# the whole point is that everyone gets one instantly.
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

from app.auth import require_admin
from app.models.user import UserInDB
from app.models.template import (
    CloneMode,
    TemplateStatus,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplateResponse,
    DistributeRequest,
    BatchResponse,
    BatchProgressResponse,
)
from app.proxmox_client import ProxmoxClient, ProxmoxAPIError
from app.tasks.clone_tasks import clone_template_for_student
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

@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    req: TemplateCreateRequest,
    admin: UserInDB = Depends(require_admin),
):
    """
    Publish a template from one of the admin's existing VMs (by vm_job_id).

    For a LINKED template we also convert the source VM into a Proxmox template
    (`qm template`) so it can be linked-cloned. The source VM must be stopped;
    if Proxmox rejects the conversion we surface the error.
    """
    source_job = database.get_vm_job(req.vm_job_id)
    if not source_job:
        raise HTTPException(status_code=404, detail=f"Source VM job {req.vm_job_id} not found.")
    # An admin is the platform operator and may publish ANY VM as a template,
    # regardless of which user created it. (No ownership restriction — by design.)
    # Note: publishing a LINKED template freezes the source VM into a Proxmox
    # template irreversibly, so the UI should make that clear to the admin.
    if not source_job.get("vmid"):
        raise HTTPException(status_code=400, detail="Source VM has no Proxmox VMID yet.")
    # Must be a finished VM. Proxmox also requires the VM to be stopped before
    # `qm template` (linked mode) — surfaced as a 502 if it isn't.
    if source_job["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Source VM must be in 'done' status (current: {source_job['status']}).",
        )

    source_vmid = source_job["vmid"]
    os_choice = source_job["os_choice"]

    # Linked clones require the source to be frozen as a Proxmox template.
    template_status = TemplateStatus.draft.value
    if req.clone_mode == CloneMode.linked:
        try:
            proxmox._ensure_authenticated()
            proxmox.convert_to_template(vmid=source_vmid, node=_DEFAULT_NODE)
            template_status = TemplateStatus.published.value
        except ProxmoxAPIError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Could not convert the source VM into a Proxmox template "
                    f"(required for linked clones). Stop the VM and retry. ({exc})"
                ),
            )
    else:
        template_status = TemplateStatus.published.value

    row = tdb.create_template(
        owner_id=admin.id,
        name=req.name,
        source_vmid=source_vmid,
        os_choice=os_choice,
        description=req.description,
        clone_mode=req.clone_mode.value,
        default_cpu=req.default_cpu,
        default_ram_mb=req.default_ram_mb,
        status=template_status,
    )
    database.log_action(
        user_id=admin.id, action_type="template.create",
        action="template.create", target_type="vm_template",
        target_id=str(row["id"]),
        details={"name": req.name, "source_vmid": source_vmid, "clone_mode": req.clone_mode.value},
    )
    return TemplateResponse.model_validate(row)


@router.get("/templates", response_model=List[TemplateResponse])
def list_templates(
    include_archived: bool = False,
    admin: UserInDB = Depends(require_admin),
):
    return [TemplateResponse.model_validate(t) for t in tdb.list_templates(include_archived)]


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

    if not tdb.get_class(req.class_id):
        raise HTTPException(status_code=404, detail=f"Class {req.class_id} not found.")

    # Resolve effective specs + clone mode (request overrides template defaults).
    cpu_cores = req.cpu_cores or template["default_cpu"]
    ram_mb = req.ram_mb or template["default_ram_mb"]
    clone_mode = (req.clone_mode.value if req.clone_mode else template["clone_mode"])
    full = (clone_mode == CloneMode.full.value)
    source_vmid = template["source_vmid"]
    os_choice = template["os_choice"]

    # Guard: a linked clone needs the source frozen as a Proxmox template, which
    # only happens when the template was PUBLISHED as linked. Block a full-mode
    # template being distributed as linked — Proxmox would reject every clone.
    if clone_mode == CloneMode.linked.value and template["clone_mode"] != CloneMode.linked.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot distribute as linked: this template was not published as linked.",
        )

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
            source_vmid=source_vmid,
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
