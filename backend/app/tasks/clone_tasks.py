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
from app.proxmox_client import ProxmoxClient, ProxmoxAPIError
from app.models.vm import VMStatus
from db import database
from db import templates as tdb

logger = logging.getLogger(__name__)

# One ProxmoxClient per worker process (stateless with token auth).
proxmox = ProxmoxClient()

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
_SOURCE_LOCK_WAIT_SECONDS = 600       # how long to wait to acquire the lock
_SOURCE_LOCK_HOLD_SECONDS = 600       # auto-expire so a crashed worker can't deadlock


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
    source_vmid: int,
    new_vmid: int,
    vm_name: str,
    os_choice_value: str,
    cpu_cores: int,
    ram_mb: int,
    node: str,
    full: bool,
) -> dict:
    """
    Clone `source_vmid` → `new_vmid` for one student, configure CPU/RAM, boot,
    poll for an IP, and store credentials. Updates the vm_jobs row, the
    clone_jobs row, and rolls up the parent batch status.

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
            clone_job_id, source_vmid, new_vmid, student_id,
            "full" if full else "linked",
        )

        # ── Clone the template (mode chosen per-template) ────────────────
        # Wrap the clone call AND wait_for_task in a per-source Redis lock.
        # Proxmox flocks /var/lock/qemu-server/lock-<source>.conf for the
        # duration of the clone — two concurrent clones from the same source
        # would otherwise fail with "can't lock file ... got timeout".
        with _source_clone_lock(source_vmid):
            clone_upid = proxmox.clone_vm(
                template_vmid=source_vmid,
                new_vmid=new_vmid,
                name=vm_name,
                node=node,
                full=full,
            )
            proxmox.wait_for_task(node=node, upid=clone_upid, timeout=300)
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
            proxmox_response={"vmid": new_vmid, "result": "OK", "cloned_from": source_vmid},
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
            "source_vmid": source_vmid,
            "vm_name": vm_name,
            "status": final_status,
            "error": final_error,
        },
    )

    return {"clone_job_id": clone_job_id, "status": final_status, "error": final_error}
