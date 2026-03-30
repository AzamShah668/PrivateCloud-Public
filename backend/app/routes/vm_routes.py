# =============================================================================
# routes/vm_routes.py
# =============================================================================
# All Virtual Machine related API endpoints live here.
#
# Endpoints:
#   POST /vms/           → request a new VM (creates a vm_job, calls Proxmox)
#   GET  /vms/           → list all VMs belonging to the current user
#   GET  /vms/{job_id}   → get the details + live status of one VM job
#
# Flow for POST /vms/:
#   1.  Authenticate the user (JWT via get_current_user dependency)
#   2.  Check the user's daily quota (max VMs per day)
#   3.  Ask Proxmox for the next available VMID
#   4.  Save a vm_jobs row with status = "queued"
#   5.  Call ProxmoxClient.create_vm() to actually provision the VM
#   6.  Update the row: status = "running" + store the Proxmox response
#   7.  Write an audit log entry
#   8.  Return the job record to the client
#
# If Proxmox fails at step 5, we catch the exception, set status = "failed",
# populate error_message, and still return a 200 (or 500) with the job info
# so the user can see what went wrong.
# =============================================================================

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.auth import get_current_user
from db import database
from app.models.user import UserInDB
from app.models.vm import (
    VMStatus,
    VMCreateRequest,
    VMJobResponse,
)
from app.proxmox_client import ProxmoxClient, ProxmoxAPIError

logger = logging.getLogger(__name__)

# All routes here are under /vms
router = APIRouter(prefix="/vms", tags=["Virtual Machines"])

# ---------------------------------------------------------------------------
# Shared ProxmoxClient instance.
# In a real production app you'd use FastAPI's dependency injection or
# a startup event to initialise this. For Sprint 1 a module-level instance
# is perfectly fine.
# ---------------------------------------------------------------------------
proxmox = ProxmoxClient()


# =============================================================================
# Helper: write an audit log entry (same pattern as auth_routes.py)
# =============================================================================

def log_event(user_id: int, action: str,
              target_type: str, target_id: str, details: dict) -> None:
    try:
        database.add_audit_log(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    except Exception as exc:
        logger.error(f"Failed to write audit log [{action}]: {exc}")


# =============================================================================
# Helper: check the user's daily quota
# =============================================================================

def check_daily_quota(user: UserInDB) -> None:
    """
    Count how many vm_jobs this user has created today (UTC).
    Raises HTTP 429 Too Many Requests if they've hit their limit.
    """
    jobs_today = database.count_user_jobs_today(user.id)

    if jobs_today >= user.daily_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Daily quota exceeded. You have already created "
                f"{jobs_today} VM(s) today (limit: {user.daily_quota}). "
                f"Your quota resets at midnight UTC."
            ),
        )


# =============================================================================
# POST /vms/  — Create a new VM
# =============================================================================

@router.post(
    "/",
    response_model=VMJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request creation of a new Virtual Machine",
)
def create_vm(
    vm_request: VMCreateRequest,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Submit a VM creation request.
    ... [docstring omitted for brevity] ...
    """

    # ── Step 1: quota check ───────────────────────────────────────────────
    check_daily_quota(current_user)

    # ── Step 2: get the next available VMID from Proxmox ─────────────────
    try:
        proxmox._ensure_authenticated()
        vmid = proxmox.get_next_vmid()
    except Exception as exc:
        logger.error(f"Failed to get next VMID from Proxmox: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot reach Proxmox server. Please try again later.",
        )

    # ── Step 3: build the full request payload (stored for audit/replay) ──
    request_payload = {
        "vm_name":    vm_request.vm_name,
        "os_choice":  vm_request.os_choice,
        "cpu_cores":  vm_request.cpu_cores,
        "ram_mb":     vm_request.ram_mb,
        "storage_gb": vm_request.storage_gb,
        "node":       vm_request.node,
    }

    # ── Step 4: insert the job row with status = queued ───────────────────
    job_id = database.create_vm_job(
        user_id=current_user.id,
        vmid=vmid,
        vm_name=vm_request.vm_name,
        os_choice=vm_request.os_choice.value,
        request_payload=request_payload,
    )

    logger.info(
        f"VM job {job_id} created for user '{current_user.username}' "
        f"(vmid={vmid}, os={vm_request.os_choice})"
    )

    # ── Step 5: call Proxmox to actually create the VM ────────────────────
    os_val = vm_request.os_choice.value
    proxmox_config = {
        "node":      vm_request.node,
        "vmid":      vmid,
        "name":      vm_request.vm_name,
        "ostype":    _map_os_to_proxmox_type(os_val),
        "cores":     vm_request.cpu_cores,
        "memory":    vm_request.ram_mb,
        "storage":   "local-lvm",
        "disk_size": str(vm_request.storage_gb),
        "iso":       _map_os_to_iso(os_val),
    }

    try:
        # Update status to "running" before the Proxmox call
        database.update_vm_job(job_id=job_id, status=VMStatus.running.value)

        returned_vmid = proxmox.create_vm(proxmox_config)

        # ── Step 6a: success — update job to "done" ───────────────────────
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.done.value,
            proxmox_response={"vmid": returned_vmid, "result": "OK"}
        )

        logger.info(f"VM job {job_id} completed. Proxmox vmid={returned_vmid}")

    except ProxmoxAPIError as exc:
        # ── Step 6b: failure — update job to "failed" ─────────────────────
        logger.error(f"Proxmox API error for job {job_id}: {exc}")
        database.update_vm_job(job_id=job_id, status=VMStatus.failed.value, error_message=str(exc))

    except Exception as exc:
        logger.error(f"Unexpected error for job {job_id}: {exc}")
        database.update_vm_job(job_id=job_id, status=VMStatus.failed.value, error_message=f"Unexpected server error: {exc}")

    # fetch updated job state to return
    updated_job = database.get_vm_job(job_id)

    # ── Step 7: write audit log ───────────────────────────────────────────
    log_event(
        user_id=current_user.id,
        action="vm.create",
        target_type="vm_job",
        target_id=str(job_id),
        details={
            "vmid":      vmid,
            "vm_name":   vm_request.vm_name,
            "os_choice": vm_request.os_choice.value,
            "status":    updated_job["status"],
        },
    )

    # ── Step 8: return the job ────────────────────────────────────────────
    return VMJobResponse.model_validate(updated_job)


# =============================================================================
# GET /vms/  — List the current user's VMs
# =============================================================================

@router.get(
    "/",
    response_model=List[VMJobResponse],
    summary="List all VMs belonging to the current user",
)
def list_my_vms(
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Returns all vm_job rows owned by the authenticated user,
    ordered newest-first.

    No body required — the user identity comes from the JWT token.

    The sequence diagram shows that for each VM we should also fetch the
    live status from Proxmox. For Sprint 1 we return the DB status.
    In Sprint 2 you can enhance this to call proxmox.get_vm_status() per VM.
    """
    jobs = database.list_user_vm_jobs(current_user.id)

    logger.debug(f"Listing {len(jobs)} VMs for user '{current_user.username}'")

    return [VMJobResponse.model_validate(job) for job in jobs]


# =============================================================================
# GET /vms/{job_id}  — Get a single VM job with live Proxmox status
# =============================================================================

@router.get(
    "/{job_id}",
    response_model=VMJobResponse,
    summary="Get details and live status of a specific VM job",
)
def get_vm(
    job_id: int,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Returns the vm_job row for `job_id`, plus a live status check from Proxmox
    if the job is in 'running' or 'done' state.

    Authorization: users can only see their own VMs. Admins can see all.

    Errors:
        404 Not Found  — job doesn't exist or belongs to another user.
        503 Unavailable — Proxmox unreachable (only when fetching live status).
    """
    # ── Fetch the job from DB ─────────────────────────────────────────────
    job = database.get_vm_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VM job with id={job_id} not found.",
        )

    # ── Ownership check ───────────────────────────────────────────────────
    # Normal users can only see their own jobs.
    # Admins can see all jobs (useful for support/debugging).
    if current_user.role != "admin" and job["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this VM job.",
        )

    # ── Optional: enrich with live Proxmox status ─────────────────────────
    # If the job is done, try to get the live runtime status from Proxmox.
    # We intentionally don't fail the whole request if Proxmox is unreachable —
    # we just return what we have in the DB.
    if job["status"] in (VMStatus.done.value, VMStatus.running.value) and job.get("vmid"):
        try:
            proxmox._ensure_authenticated()
            live_status = proxmox.get_vm_status(job["vmid"])
            # Merge live status into the proxmox_response field so the
            # client gets the most up-to-date info.
            job["proxmox_response"] = {
                **(job.get("proxmox_response") or {}),
                "live_status": live_status,
            }
        except Exception as exc:
            logger.warning(
                f"Could not fetch live status for vmid={job['vmid']}: {exc}"
            )

    return VMJobResponse.model_validate(job)


# =============================================================================
# Utility: map OS choice string to Proxmox ostype parameter
# =============================================================================

_OS_MAP = {
    "ubuntu-22.04": {"ostype": "l26",   "iso": "local:iso/ubuntu-22.04-live-server-amd64.iso"},
    "ubuntu-24.04": {"ostype": "l26",   "iso": "local:iso/ubuntu-24.04-live-server-amd64.iso"},
    "debian-12":    {"ostype": "l26",   "iso": "local:iso/debian-12-netinst-amd64.iso"},
    "centos-9":     {"ostype": "l26",   "iso": "local:iso/CentOS-Stream-9-latest-x86_64-dvd1.iso"},
    "windows-11":   {"ostype": "win11", "iso": "local:iso/Win11_23H2_English_x64.iso"},
}


def _map_os_to_proxmox_type(os_choice: str) -> str:
    return _OS_MAP.get(os_choice, {}).get("ostype", "l26")


def _map_os_to_iso(os_choice: str) -> str | None:
    return _OS_MAP.get(os_choice, {}).get("iso")
