# =============================================================================
# tasks/clone_tasks.py
# =============================================================================
# Celery task that clones a teacher's template into one student's VM.
#
# The distribute API endpoint fans out ONE of these tasks per enrolled
# student (after pre-allocating a distinct VMID for each and creating the
# vm_jobs + clone_jobs rows synchronously, so concurrent workers never race
# for the same VMID).
#
# This mirrors tasks/vm_tasks.py:provision_vm but:
#   - clones the template's source_vmid (not the OS golden image)
#   - honours the per-template clone mode (full vs linked)
#   - updates BOTH the vm_jobs row (so the student's dashboard works) AND the
#     clone_jobs row (lineage/progress), then rolls up the batch status.
#
# See docs/design/clone-templates-architecture.md
# =============================================================================

import logging
import os
import time
import uuid
from contextlib import contextmanager

import redis

from app.celery_app import celery_app
from app.proxmox_client import ProxmoxAPIError, proxmox
from app.models.vm import VMStatus
from db import database
from db import templates as tdb

logger = logging.getLogger(__name__)

# `proxmox` is the shared client proxy: it delegates to a ProxmoxClient built
# lazily on first use from DB-backed config (setup wizard) with .env fallback.
# (A celery-worker restart picks up later config changes — the worker already
# requires a restart for task/code changes.)

# Redis lock to serialise CONCURRENT CLONES OF THE SAME SOURCE VMID.
# Proxmox itself holds an exclusive flock on /var/lock/qemu-server/lock-<vmid>.conf
# during the clone operation. Two of our Celery workers cloning the same source
# at the same time will collide on that file lock — the second clone fails with
# "can't lock file ... got timeout". This wraps the clone_vm + wait_for_task
# block in a per-source Redis lock so workers queue politely behind each other
# (other Celery work — clones of DIFFERENT sources, normal provisions — keeps
# its full concurrency).
_redis = redis.Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"))
_SOURCE_LOCK_KEY = "privatecloud:lock:clone_source:{vmid}"
# A full clone of a large (esp. Windows) disk can take many minutes, and clones
# of the SAME source are serialised behind this lock — so the wait window has to
# comfortably exceed several back-to-back Windows clones. Hold auto-expires so a
# crashed worker can't deadlock the system.
_SOURCE_LOCK_WAIT_SECONDS = 3600      # how long to wait to acquire the lock
_SOURCE_LOCK_HOLD_SECONDS = 1800      # auto-expire so a crashed worker can't deadlock


# Proxmox clone duration depends heavily on disk size + OS. Windows golden disks
# are large, so their full clone needs a far longer wait than a slim Linux image.
def _clone_wait_timeout(os_choice_value: str) -> int:
    """Seconds to wait for a Proxmox clone task to finish, by OS family."""
    return 1500 if os_choice_value == "windows-11" else 600


@contextmanager
def _source_clone_lock(source_vmid: int):
    """
    Acquire an exclusive Redis lock for a given source VMID. Blocks (polling)
    up to _SOURCE_LOCK_WAIT_SECONDS waiting for it. The lock self-expires
    after _SOURCE_LOCK_HOLD_SECONDS so a worker crash can't deadlock the system.
    """
    key = _SOURCE_LOCK_KEY.format(vmid=source_vmid)
    token = str(uuid.uuid4())
    acquired = False
    deadline = time.time() + _SOURCE_LOCK_WAIT_SECONDS
    try:
        while time.time() < deadline:
            if _redis.set(key, token, nx=True, ex=_SOURCE_LOCK_HOLD_SECONDS):
                acquired = True
                break
            time.sleep(1.0)
        if not acquired:
            logger.warning(
                "Source-VMID lock not acquired for vmid=%d after %ds — proceeding "
                "unlocked (Proxmox may reject the clone).",
                source_vmid, _SOURCE_LOCK_WAIT_SECONDS,
            )
        yield acquired
    finally:
        if acquired:
            try:
                # Only release if we still own the token (cheap CAS-style check).
                if _redis.get(key) == token.encode():
                    _redis.delete(key)
            except redis.RedisError:
                pass


def _log_event(user_id, action, target_type, target_id, details):
    """Best-effort audit log — never crashes the task."""
    try:
        database.add_audit_log(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    except Exception as exc:
        logger.error("Failed to write audit log [%s]: %s", action, exc)


@celery_app.task(
    bind=True,
    name="clone.template_for_student",
    max_retries=1,
    default_retry_delay=30,
    acks_late=True,
)
def clone_template_for_student(
    self,
    clone_job_id: int,
    vm_job_id: int,
    batch_id: int,
    student_id: int,
    template_vmid: int,
    new_vmid: int,
    vm_name: str,
    os_choice_value: str,
    cpu_cores: int,
    ram_mb: int,
    node: str,
    full: bool,
) -> dict:
    """
    Clone the dedicated Proxmox template `template_vmid` → `new_vmid` for one
    student, configure CPU/RAM, boot, poll for an IP, and store credentials.
    Updates the vm_jobs row, the clone_jobs row, and rolls up the parent batch
    status.

    Args mirror the values pre-computed by the distribute endpoint. `full`
    selects full (True) vs linked (False) clone.
    """
    # Celery workers are separate processes — ensure the DB pool exists.
    if not database._pool:
        database.init_db()

    final_status = VMStatus.failed.value
    final_error = None

    try:
        tdb.update_clone_job(clone_job_id, "cloning")
        database.update_vm_job(job_id=vm_job_id, status=VMStatus.running.value)

        logger.info(
            "Clone job=%d: cloning template vmid=%d → vmid=%d for student=%d (%s)",
            clone_job_id, template_vmid, new_vmid, student_id,
            "full" if full else "linked",
        )

        # ── Clone the template (mode chosen per-template) ────────────────
        # Wrap the clone call AND wait_for_task in a per-source Redis lock.
        # Proxmox flocks /var/lock/qemu-server/lock-<source>.conf for the
        # duration of the clone — two concurrent clones from the same source
        # would otherwise fail with "can't lock file ... got timeout".
        with _source_clone_lock(template_vmid):
            clone_upid = proxmox.clone_vm(
                template_vmid=template_vmid,
                new_vmid=new_vmid,
                name=vm_name,
                node=node,
                full=full,
            )
            proxmox.wait_for_task(
                node=node, upid=clone_upid, timeout=_clone_wait_timeout(os_choice_value),
            )
        logger.info("Clone complete for vmid=%d.", new_vmid)

        # ── Apply requested CPU / RAM ────────────────────────────────────
        proxmox.update_vm_config(vmid=new_vmid, node=node, cores=cpu_cores, memory=ram_mb)

        # ── Start the VM ─────────────────────────────────────────────────
        start_upid = proxmox.start_vm(vmid=new_vmid, node=node)
        proxmox.wait_for_task(node=node, upid=start_upid, timeout=120)
        logger.info("VM %d is running.", new_vmid)

        # ── Poll the guest agent for an IP ───────────────────────────────
        ip_timeout = 600 if os_choice_value == "windows-11" else 300
        vm_ip = proxmox.get_vm_ip_from_agent(
            vmid=new_vmid, node=node, timeout=ip_timeout, poll_interval=5,
        )
        if not vm_ip:
            logger.warning(
                "IP polling timed out for vmid=%d (clone_job=%d). VM running, "
                "no IP yet — GET self-heal will recover it later.",
                new_vmid, clone_job_id,
            )

        vm_user, vm_pass = proxmox.get_post_provision_credentials(os_choice_value)
        database.update_vm_job(
            job_id=vm_job_id,
            status=VMStatus.done.value,
            proxmox_response={"vmid": new_vmid, "result": "OK", "cloned_from": template_vmid},
            vm_ip=vm_ip,
            vm_username=vm_user,
            vm_password=vm_pass,
        )
        tdb.update_clone_job(clone_job_id, "done", vm_job_id=vm_job_id)
        final_status = VMStatus.done.value
        logger.info("Clone job %d completed (vmid=%d, ip=%s).", clone_job_id, new_vmid, vm_ip)

    except ProxmoxAPIError as exc:
        final_error = str(exc)
        logger.error("Proxmox API error for clone_job %d: %s", clone_job_id, exc)
        database.update_vm_job(job_id=vm_job_id, status=VMStatus.failed.value, error_message=final_error)
        tdb.update_clone_job(clone_job_id, "failed", error_message=final_error)

    except Exception as exc:
        final_error = f"Unexpected server error: {exc}"
        logger.error("Unexpected error for clone_job %d: %s", clone_job_id, exc)
        database.update_vm_job(job_id=vm_job_id, status=VMStatus.failed.value, error_message=final_error)
        tdb.update_clone_job(clone_job_id, "failed", error_message=final_error)

    # Roll up the batch status now that this clone has finished (best-effort).
    try:
        tdb.rollup_batch_status(batch_id)
    except Exception as exc:
        logger.error("Failed to roll up batch %d status: %s", batch_id, exc)

    _log_event(
        user_id=student_id,
        action="clone.create",
        target_type="clone_job",
        target_id=str(clone_job_id),
        details={
            "batch_id": batch_id,
            "vmid": new_vmid,
            "template_vmid": template_vmid,
            "vm_name": vm_name,
            "status": final_status,
            "error": final_error,
        },
    )

    return {"clone_job_id": clone_job_id, "status": final_status, "error": final_error}


@celery_app.task(
    bind=True,
    name="clone.build_template",
    max_retries=1,
    default_retry_delay=30,
    acks_late=True,
)
def build_template(
    self,
    template_id: int,
    owner_id: int,
    source_vmid: int,
    template_vmid: int,
    template_name: str,
    node: str,
) -> dict:
    """
    Build a DEDICATED Proxmox template from a source VM, exactly like the
    global golden images 9000/9001 — but private/scoped to this template row.

    Steps:
      1. Full-clone the admin's source VM (source_vmid) → a new VM (template_vmid).
         A FULL clone keeps the new template independent of the source, so the
         admin's working VM stays usable and can even be deleted later.
      2. Convert that new VM into a Proxmox template via `qm template`
         (frozen, read-only, clonable — full or linked).
      3. Mark the vm_templates row 'published' (or 'failed').

    The source VM may be running; Proxmox can clone a running VM. We hold the
    per-source Redis lock for the clone so we don't collide with a student
    distribution that also clones the same source.
    """
    if not database._pool:
        database.init_db()

    final_status = "failed"
    final_error = None

    try:
        logger.info(
            "Building template id=%d: clone source vmid=%d → template vmid=%d (%s)",
            template_id, source_vmid, template_vmid, template_name,
        )

        # ── Full-clone the source into the dedicated template VM ─────────
        with _source_clone_lock(source_vmid):
            clone_upid = proxmox.clone_vm(
                template_vmid=source_vmid,
                new_vmid=template_vmid,
                name=template_name,
                node=node,
                full=True,
            )
            proxmox.wait_for_task(node=node, upid=clone_upid, timeout=1500)
        logger.info("Template clone complete (vmid=%d). Freezing → Proxmox template.", template_vmid)

        # ── Freeze the clone into a read-only Proxmox template ───────────
        proxmox.convert_to_template(vmid=template_vmid, node=node)

        tdb.update_template(template_id, status="published")
        final_status = "published"
        logger.info("Template id=%d published (template vmid=%d).", template_id, template_vmid)

    except ProxmoxAPIError as exc:
        final_error = str(exc)
        logger.error("Proxmox API error building template %d: %s", template_id, exc)
        tdb.update_template(template_id, status="failed")
    except Exception as exc:
        final_error = f"Unexpected server error: {exc}"
        logger.error("Unexpected error building template %d: %s", template_id, exc)
        tdb.update_template(template_id, status="failed")

    _log_event(
        user_id=owner_id,
        action="template.build",
        target_type="vm_template",
        target_id=str(template_id),
        details={
            "source_vmid": source_vmid,
            "template_vmid": template_vmid,
            "status": final_status,
            "error": final_error,
        },
    )
    return {"template_id": template_id, "status": final_status, "error": final_error}


@celery_app.task(
    bind=True,
    name="clone.deploy_for_user",
    max_retries=1,
    default_retry_delay=30,
    acks_late=True,
)
def deploy_template_for_user(
    self,
    job_id: int,
    user_id: int,
    template_vmid: int,
    new_vmid: int,
    vm_name: str,
    os_choice_value: str,
    cpu_cores: int,
    ram_mb: int,
    node: str,
    full: bool,
) -> dict:
    """
    Deploy a single VM from a published template (admin self-serve from the
    Deploy page). Mirrors vm_tasks.provision_vm but clones the dedicated
    template `template_vmid` instead of an OS golden image. The resulting VM
    lands in vm_jobs like any other, so the dashboard/console/RDP work as usual.
    """
    if not database._pool:
        database.init_db()

    final_status = VMStatus.failed.value
    final_error = None

    try:
        database.update_vm_job(job_id=job_id, status=VMStatus.running.value)

        logger.info(
            "Deploy job=%d: cloning template vmid=%d → vmid=%d for user=%d (%s)",
            job_id, template_vmid, new_vmid, user_id, "full" if full else "linked",
        )

        with _source_clone_lock(template_vmid):
            clone_upid = proxmox.clone_vm(
                template_vmid=template_vmid,
                new_vmid=new_vmid,
                name=vm_name,
                node=node,
                full=full,
            )
            proxmox.wait_for_task(
                node=node, upid=clone_upid, timeout=_clone_wait_timeout(os_choice_value),
            )

        proxmox.update_vm_config(vmid=new_vmid, node=node, cores=cpu_cores, memory=ram_mb)

        start_upid = proxmox.start_vm(vmid=new_vmid, node=node)
        proxmox.wait_for_task(node=node, upid=start_upid, timeout=120)

        ip_timeout = 600 if os_choice_value == "windows-11" else 300
        vm_ip = proxmox.get_vm_ip_from_agent(
            vmid=new_vmid, node=node, timeout=ip_timeout, poll_interval=5,
        )
        if not vm_ip:
            logger.warning(
                "IP polling timed out for vmid=%d (job=%d). VM running, no IP yet.",
                new_vmid, job_id,
            )

        vm_user, vm_pass = proxmox.get_post_provision_credentials(os_choice_value)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.done.value,
            proxmox_response={"vmid": new_vmid, "result": "OK", "cloned_from": template_vmid},
            vm_ip=vm_ip,
            vm_username=vm_user,
            vm_password=vm_pass,
        )
        final_status = VMStatus.done.value
        logger.info("Deploy job %d completed (vmid=%d, ip=%s).", job_id, new_vmid, vm_ip)

    except ProxmoxAPIError as exc:
        final_error = str(exc)
        logger.error("Proxmox API error for deploy job %d: %s", job_id, exc)
        database.update_vm_job(job_id=job_id, status=VMStatus.failed.value, error_message=final_error)
    except Exception as exc:
        final_error = f"Unexpected server error: {exc}"
        logger.error("Unexpected error for deploy job %d: %s", job_id, exc)
        database.update_vm_job(job_id=job_id, status=VMStatus.failed.value, error_message=final_error)

    _log_event(
        user_id=user_id,
        action="vm.create",
        target_type="vm_job",
        target_id=str(job_id),
        details={
            "vmid": new_vmid,
            "template_vmid": template_vmid,
            "vm_name": vm_name,
            "status": final_status,
            "error": final_error,
        },
    )
    return {"job_id": job_id, "status": final_status, "error": final_error}
