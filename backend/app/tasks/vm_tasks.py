# =============================================================================
# tasks/vm_tasks.py
# =============================================================================
# Celery task that provisions a VM on Proxmox.
#
# This is essentially the same code that was in vm_routes.py's
# _provision_vm_background() function, but now it runs in a SEPARATE
# Celery worker process instead of inside the FastAPI web server process.
#
# Why this matters:
#   Before:  FastAPI's BackgroundTasks ran the clone/start/IP-polling
#            inside the SAME process.  If uvicorn restarted, all in-flight
#            provisioning jobs were silently lost.
#   Now:     Celery workers are independent processes.  If the web server
#            restarts, the worker keeps running.  If the worker crashes,
#            Redis still holds the task and it gets retried.
# =============================================================================

import logging
from app.celery_app import celery_app
from app.proxmox_client import ProxmoxAPIError, proxmox
from app.models.vm import VMStatus
from db import database

logger = logging.getLogger(__name__)

# `proxmox` is the shared client proxy: it delegates to a ProxmoxClient built
# lazily on first use from DB-backed config (setup wizard) with .env fallback.
# (A celery-worker restart is needed to pick up later config changes — the
# worker already requires a restart for task/code changes.)


def _log_event(user_id, action, target_type, target_id, details):
    """Insert one row into audit_logs (best-effort, never crashes the task)."""
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
    name="vm.provision",
    max_retries=1,
    default_retry_delay=30,
    acks_late=True,
)
def provision_vm(
    self,
    job_id: int,
    vmid: int,
    user_id: int,
    vm_name: str,
    os_choice_value: str,
    cpu_cores: int,
    ram_mb: int,
    node: str,
) -> dict:
    """
    Celery task: clone a golden template, configure CPU/RAM, start the VM,
    and poll for an IP address.

    This is a long-running task (1-10 minutes depending on OS type and
    disk speed).  It runs in a dedicated Celery worker process, completely
    independent of the FastAPI web server.

    Args:
        self:             Celery task instance (for retry support).
        job_id:           Primary key in our vm_jobs table.
        vmid:             Proxmox VM ID allocated for this VM.
        user_id:          Owner's user ID (for audit logging).
        vm_name:          Human-readable VM name.
        os_choice_value:  OS string (e.g. "ubuntu-22.04", "windows-11").
        cpu_cores:        Number of CPU cores to assign.
        ram_mb:           RAM in megabytes.
        node:             Proxmox node name.

    Returns:
        dict with final status and any error message.
    """
    # ── Ensure DB pool is initialised in this worker process ─────────────
    # Celery workers are separate processes — they don't share the FastAPI
    # lifespan.  We must make sure the database connection pool exists.
    if not database._pool:
        database.init_db()

    final_status = VMStatus.failed.value
    final_error = None

    try:
        database.update_vm_job(job_id=job_id, status=VMStatus.running.value)

        template_vmid = proxmox.get_clone_template_vmid(os_choice_value)
        logger.info(
            "Provisioning job=%d os=%s: cloning template vmid=%d → new vmid=%d",
            job_id, os_choice_value, template_vmid, vmid,
        )

        # ── Clone the OS-specific golden template ───────────────────────
        clone_upid = proxmox.clone_vm(
            template_vmid=template_vmid,
            new_vmid=vmid,
            name=vm_name,
            node=node,
        )
        logger.info(
            "Waiting for clone task to finish (job=%d, vmid=%d, upid=%s)…",
            job_id, vmid, clone_upid,
        )
        proxmox.wait_for_task(node=node, upid=clone_upid, timeout=300)
        logger.info("Clone complete for vmid=%d.", vmid)

        # ── Apply requested CPU / RAM ────────────────────────────────────
        proxmox.update_vm_config(
            vmid=vmid,
            node=node,
            cores=cpu_cores,
            memory=ram_mb,
        )
        logger.info("VM %d configured: %d cores, %d MB RAM.", vmid, cpu_cores, ram_mb)

        # ── Start the VM ─────────────────────────────────────────────────
        start_upid = proxmox.start_vm(vmid=vmid, node=node)
        logger.info("Waiting for VM %d to start (upid=%s)…", vmid, start_upid)
        proxmox.wait_for_task(node=node, upid=start_upid, timeout=120)
        logger.info("VM %d is running.", vmid)

        # ── Poll the QEMU guest agent for an IP ──────────────────────────
        ip_timeout = 600 if os_choice_value == "windows-11" else 300
        vm_ip = proxmox.get_vm_ip_from_agent(
            vmid=vmid,
            node=node,
            timeout=ip_timeout,
            poll_interval=5,
        )

        if vm_ip:
            logger.info("VM %d (job %d) got IP: %s", vmid, job_id, vm_ip)
        else:
            logger.warning(
                "IP polling timed out for vmid=%d (job=%d). "
                "VM is running but guest agent never reported an IP.",
                vmid, job_id,
            )

        vm_user, vm_pass = proxmox.get_post_provision_credentials(os_choice_value)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.done.value,
            proxmox_response={"vmid": vmid, "result": "OK"},
            vm_ip=vm_ip,
            vm_username=vm_user,
            vm_password=vm_pass,
        )
        logger.info("VM job %d completed (vmid=%d, ip=%s).", job_id, vmid, vm_ip)
        final_status = VMStatus.done.value

    except ProxmoxAPIError as exc:
        logger.error("Proxmox API error for job %d: %s", job_id, exc)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.failed.value,
            error_message=str(exc),
        )
        final_error = str(exc)

    except Exception as exc:
        logger.error("Unexpected error for job %d: %s", job_id, exc)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.failed.value,
            error_message=f"Unexpected server error: {exc}",
        )
        final_error = f"Unexpected server error: {exc}"

    # Audit log (best-effort)
    updated = database.get_vm_job(job_id) or {}
    _log_event(
        user_id=user_id,
        action="vm.create",
        target_type="vm_job",
        target_id=str(job_id),
        details={
            "vmid":      vmid,
            "vm_name":   vm_name,
            "os_choice": os_choice_value,
            "status":    final_status,
            "ip":        updated.get("vm_ip"),
            "error":     final_error,
        },
    )

    return {"job_id": job_id, "status": final_status, "error": final_error}
