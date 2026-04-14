# =============================================================================
# routes/vm_routes.py
# =============================================================================
# All Virtual Machine related API endpoints live here.
#
# Endpoints:
#   POST   /vms/           → request a new VM (creates a vm_job, calls Proxmox)
#   GET    /vms/           → list all VMs belonging to the current user
#   GET    /vms/{job_id}   → get the details + live status of one VM job
#   DELETE /vms/{job_id}   → stop and permanently destroy a VM
#
# Flow for POST /vms/:
#   1.  Authenticate the user (JWT via get_current_user dependency)
#   2.  Check the user's daily quota (max VMs per day)
#   3.  Ask Proxmox for the next available VMID
#   4.  Save a vm_jobs row with status = "queued"
#   5.  Call ProxmoxClient.create_vm() to actually provision the VM
#   6.  Update the row: status = "done" + store the Proxmox response
#   7.  Write an audit log entry
#   8.  Return the job record to the client
#
# Flow for DELETE /vms/{job_id}:
#   1.  Authenticate the user
#   2.  Fetch the job and verify ownership
#   3.  Guard: reject if job is still queued or running
#   4.  If job is failed, just mark deleted in DB (no Proxmox call needed)
#   5.  Stop the VM on Proxmox if it is currently running
#   6.  Call ProxmoxClient.delete_vm() to destroy the VM + its disk
#   7.  Mark the job row as status = "deleted"
#   8.  Write an audit log entry
#   9.  Return the updated job record
#
# If Proxmox fails at any step, we catch the exception, set status = "failed",
# populate error_message, and return 502 with the job info so the user can
# see what went wrong.
# =============================================================================

import logging
import secrets
import time
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.auth import get_current_user
from db import database
from app.models.user import UserInDB
from app.models.vm import (
    VMStatus,
    VMAction,
    VMCreateRequest,
    VMUpdateRequest,
    VMJobResponse,
    VMEnrichedResponse,
)
from app.proxmox_client import ProxmoxClient, ProxmoxAPIError, CLOUD_TEMPLATE_MAP

logger = logging.getLogger(__name__)

# All routes in this file are mounted under /vms
router = APIRouter(prefix="/vms", tags=["Virtual Machines"])

# ---------------------------------------------------------------------------
# Shared ProxmoxClient instance.
# In a real production app you'd use FastAPI's dependency injection or
# a startup event to initialise this. For Sprint 1 a module-level instance
# is perfectly fine.
# ---------------------------------------------------------------------------
proxmox = ProxmoxClient()


# =============================================================================
# Helper: write an audit log entry
# =============================================================================

def log_event(
    user_id: int,
    action: str,
    target_type: str,
    target_id: str,
    details: dict,
) -> None:
    """
    Insert one row into audit_logs.
    Wrapped in try/except so a logging failure never crashes the main request.
    """
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


# =============================================================================
# Helper: enforce the user's daily VM creation quota
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
    responses={
        429: {"description": "Daily quota exceeded"},
        503: {"description": "Cannot reach Proxmox to allocate a VMID"},
        502: {"description": "Proxmox failed to create the VM"},
    },
)
def create_vm(
    vm_request: VMCreateRequest,
    response: Response,
    current_user: UserInDB = Depends(get_current_user),
) -> VMJobResponse:
    """
    Submit a VM creation request.

    The VM is created synchronously inside this request. If Proxmox succeeds
    the job status will be 'done'; if Proxmox fails it will be 'failed' and
    the response status code will be 502.
    """

    # ── Step 1: quota check ───────────────────────────────────────────────
    check_daily_quota(current_user)

    # ── Step 2: get the next available VMID from Proxmox ─────────────────
    try:
        vmid = proxmox.get_next_vmid()
    except Exception as exc:
        logger.error("Failed to get next VMID from Proxmox: %s", exc)
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
        "VM job %s created for user '%s' (vmid=%s, os=%s)",
        job_id, current_user.username, vmid, vm_request.os_choice,
    )

    # ── Step 5: call Proxmox to actually create the VM ────────────────────
    os_val = vm_request.os_choice.value

    proxmox_failed = False

    try:
        # Mark the job as running before the Proxmox call
        database.update_vm_job(job_id=job_id, status=VMStatus.running.value)

        # ── Step 5a: fast path — clone a golden template (only if requested) ─
        # ── Step 5b: fallback — ISO install (default) ────────────────────
        template_vmid = CLOUD_TEMPLATE_MAP.get(os_val) if vm_request.use_template else None
        if template_vmid is not None:
            provision_result = _provision_from_template(
                template_vmid=template_vmid,
                vm_request=vm_request,
                new_vmid=vmid,
            )
            returned_vmid = provision_result["vmid"]
        else:
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
            returned_vmid = proxmox.create_vm(proxmox_config)
            provision_result = {"vmid": returned_vmid, "result": "OK"}

        # ── Step 6a: success — update job to "done" ───────────────────────
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.done.value,
            proxmox_response=provision_result,
        )
        logger.info("VM job %s completed. Proxmox vmid=%s", job_id, returned_vmid)

    except ProxmoxAPIError as exc:
        # ── Step 6b: Proxmox-specific failure ─────────────────────────────
        proxmox_failed = True
        logger.error("Proxmox API error for job %s: %s", job_id, exc)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.failed.value,
            error_message=str(exc),
        )

    except Exception as exc:
        # ── Step 6c: unexpected failure ────────────────────────────────────
        proxmox_failed = True
        logger.error("Unexpected error for job %s: %s", job_id, exc)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.failed.value,
            error_message=f"Unexpected server error: {exc}",
        )

    if proxmox_failed:
        response.status_code = status.HTTP_502_BAD_GATEWAY

    # Fetch the freshest job state to return to the client
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
    response_model=List[VMEnrichedResponse],
    summary="List all VMs belonging to the current user with live status",
)
def list_my_vms(
    current_user: UserInDB = Depends(get_current_user),
) -> List[VMEnrichedResponse]:
    """
    Returns all vm_job rows owned by the authenticated user, enriched with
    live Proxmox data (status, CPU/memory usage, uptime, network I/O).

    Makes ONE bulk API call to Proxmox (list_vms) instead of hitting Proxmox
    once per VM — much faster when the user has many VMs.

    If Proxmox is unreachable, returns DB data with live_status="unknown".
    """
    jobs = database.list_user_vm_jobs(current_user.id)
    logger.debug("Listing %s VMs for user '%s'", len(jobs), current_user.username)

    # ── Fetch all live VM statuses from Proxmox in one call ───────────────
    live_status_map: dict = {}  # vmid → Proxmox status dict
    try:
        all_vms = proxmox.list_vms()
        # Build a lookup by vmid for fast matching
        live_status_map = {vm["vmid"]: vm for vm in all_vms}
    except Exception as exc:
        # Proxmox unreachable — we still return DB data, just without live info
        logger.warning("Could not fetch live VM list from Proxmox: %s", exc)

    # ── Merge DB records with live Proxmox data ──────────────────────────
    enriched = []
    for job in jobs:
        # Start with the base DB fields
        result = dict(job)

        # Try to match this job's vmid to the live Proxmox data
        vmid = job.get("vmid")
        live = live_status_map.get(vmid) if vmid else None

        if live:
            result["live_status"] = live.get("status", "unknown")
            result["cpu_usage"]   = live.get("cpu")           # fractional
            result["mem_usage"]   = live.get("mem")            # bytes used
            result["max_mem"]     = live.get("maxmem")         # bytes allocated
            result["uptime"]      = live.get("uptime")         # seconds
            result["netin"]       = live.get("netin")          # bytes
            result["netout"]      = live.get("netout")         # bytes
        else:
            result["live_status"] = "unknown"

        enriched.append(VMEnrichedResponse.model_validate(result))

    return enriched


# =============================================================================
# GET /vms/{job_id}  — Get a single VM job with live Proxmox status
# =============================================================================

@router.get(
    "/{job_id}",
    response_model=VMJobResponse,
    summary="Get details and live status of a specific VM job",
    responses={
        404: {"description": "VM job not found"},
        403: {"description": "Not your VM"},
    },
)
def get_vm(
    job_id: int,
    current_user: UserInDB = Depends(get_current_user),
) -> VMJobResponse:
    """
    Returns the vm_job row for `job_id`, enriched with a live status check
    from Proxmox if the job is in 'running' or 'done' state.

    Authorization: users can only see their own VMs. Admins can see all.

    If Proxmox is unreachable we silently fall back to the DB-cached status
    rather than failing the whole request.
    """
    # ── Fetch the job from DB ─────────────────────────────────────────────
    job = database.get_vm_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VM job with id={job_id} not found.",
        )

    # ── Ownership check ───────────────────────────────────────────────────
    if current_user.role != "admin" and job["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this VM job.",
        )

    # ── Optional: enrich with live Proxmox status ─────────────────────────
    # Only bother hitting Proxmox if the VM should actually exist there.
    if job["status"] in (VMStatus.done.value, VMStatus.running.value) and job.get("vmid"):
        try:
            live_status = proxmox.get_vm_status(job["vmid"])
            job["proxmox_response"] = {
                **(job.get("proxmox_response") or {}),
                "live_status": live_status,
            }
        except Exception as exc:
            logger.warning(
                "Could not fetch live status for vmid=%s: %s", job["vmid"], exc
            )

    return VMJobResponse.model_validate(job)


# =============================================================================
# PATCH /vms/{job_id}  — Update a VM (start/stop/restart/resize)
# =============================================================================

@router.patch(
    "/{job_id}",
    response_model=VMJobResponse,
    summary="Update a VM — start, stop, restart, or resize",
    responses={
        404: {"description": "VM job not found"},
        403: {"description": "Not your VM"},
        409: {"description": "VM is not in a valid state for this action"},
        502: {"description": "Proxmox failed to execute the action"},
    },
)
def update_vm(
    job_id: int,
    update: VMUpdateRequest,
    response: Response,
    current_user: UserInDB = Depends(get_current_user),
) -> VMJobResponse:
    """
    Perform an action on an existing VM.

    Supported actions:
      - **start**: Boot a stopped VM
      - **stop**: Hard-stop a running VM
      - **restart**: Reboot a running VM
      - **resize**: Change CPU cores and/or RAM (VM must be stopped)

    Authorization: users can only update their own VMs. Admins can update any.
    """

    # ── Step 1: fetch job + ownership check ───────────────────────────────
    job = database.get_vm_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VM job with id={job_id} not found.",
        )

    if current_user.role != "admin" and job["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this VM.",
        )

    # ── Step 2: guard — VM must be in 'done' state ───────────────────────
    # Only a successfully created VM can be started/stopped/resized.
    if job["status"] != VMStatus.done.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"VM job {job_id} is '{job['status']}'. "
                "Only VMs with status 'done' can be updated."
            ),
        )

    vmid = job["vmid"]
    node = job["request_payload"].get("node", proxmox.default_node)
    action = update.action

    # ── Step 3: execute the action on Proxmox ─────────────────────────────
    try:
        if action == VMAction.start:
            proxmox.start_vm(vmid, node)
            logger.info("VM %s start requested by user '%s'", vmid, current_user.username)

        elif action == VMAction.stop:
            proxmox.stop_vm(vmid, node)
            logger.info("VM %s stop requested by user '%s'", vmid, current_user.username)

        elif action == VMAction.restart:
            proxmox.restart_vm(vmid, node)
            logger.info("VM %s restart requested by user '%s'", vmid, current_user.username)

        elif action == VMAction.resize:
            # Build the config update — only include fields that were provided
            config_update = {}
            if update.cpu_cores is not None:
                config_update["cores"] = update.cpu_cores
            if update.ram_mb is not None:
                config_update["memory"] = update.ram_mb

            proxmox.update_vm_config(vmid, node, **config_update)
            logger.info(
                "VM %s resized by user '%s': %s",
                vmid, current_user.username, config_update,
            )

    except ProxmoxAPIError as exc:
        logger.error("Proxmox error during %s on VM %s: %s", action.value, vmid, exc)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        # Don't change the job status — the VM still exists, the action just failed
        log_event(
            user_id=current_user.id,
            action=f"vm.{action.value}",
            target_type="vm_job",
            target_id=str(job_id),
            details={"vmid": vmid, "error": str(exc)},
        )
        return VMJobResponse.model_validate(database.get_vm_job(job_id))

    except Exception as exc:
        logger.error("Unexpected error during %s on VM %s: %s", action.value, vmid, exc)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        log_event(
            user_id=current_user.id,
            action=f"vm.{action.value}",
            target_type="vm_job",
            target_id=str(job_id),
            details={"vmid": vmid, "error": str(exc)},
        )
        return VMJobResponse.model_validate(database.get_vm_job(job_id))

    # ── Step 4: audit log ─────────────────────────────────────────────────
    details: dict = {"vmid": vmid, "action": action.value}
    if action == VMAction.resize:
        if update.cpu_cores is not None:
            details["cpu_cores"] = update.cpu_cores
        if update.ram_mb is not None:
            details["ram_mb"] = update.ram_mb

    log_event(
        user_id=current_user.id,
        action=f"vm.{action.value}",
        target_type="vm_job",
        target_id=str(job_id),
        details=details,
    )

    # ── Step 5: return the current job state ──────────────────────────────
    return VMJobResponse.model_validate(database.get_vm_job(job_id))


# =============================================================================
# DELETE /vms/{job_id}  — Stop and permanently destroy a VM
# =============================================================================

@router.delete(
    "/{job_id}",
    response_model=VMJobResponse,
    summary="Stop and permanently delete a Virtual Machine",
    responses={
        404: {"description": "VM job not found"},
        403: {"description": "Not your VM"},
        409: {"description": "VM is still being created and cannot be deleted yet"},
        502: {"description": "Proxmox error during stop or deletion"},
    },
)
def delete_vm(
    job_id: int,
    response: Response,
    current_user: UserInDB = Depends(get_current_user),
) -> VMJobResponse:
    """
    Permanently destroy the VM associated with `job_id`.

    This operation is IRREVERSIBLE — the VM and its disk are wiped from
    Proxmox. The vm_job row is kept in the database with status='deleted'
    so there is always a full audit trail.

    Flow:
      1. Fetch the job and verify ownership.
      2. Reject if the job is still 'queued' or 'running' (VM creation
         may be in progress — deleting mid-creation would corrupt state).
      3. If the job is 'failed', just mark it deleted locally (no Proxmox
         call needed because the VM may never have been created).
      4. Ask Proxmox for the VM's live state. If it is running, send a
         hard-stop first. Wait briefly for Proxmox to finish the stop.
      5. Call ProxmoxClient.delete_vm() — this sends DELETE to Proxmox
         with purge + destroy-unreferenced-disks flags so no storage leaks.
      6. Mark the job row as 'deleted' in the DB.
      7. Write an audit log entry.

    Authorization: users can only delete their own VMs. Admins can delete any.
    """

    # ── Step 1: fetch job + ownership check ───────────────────────────────
    job = database.get_vm_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VM job with id={job_id} not found.",
        )

    if current_user.role != "admin" and job["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this VM.",
        )

    # ── Step 2: guard — cannot delete while creation is in flight ─────────
    # 'queued'  → the job hasn't reached Proxmox yet; VMID may not be reserved.
    # 'running' → create_vm() is executing right now; deleting is unsafe.
    if job["status"] in (VMStatus.queued.value, VMStatus.running.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"VM job {job_id} is currently '{job['status']}'. "
                "Wait until it is 'done' or 'failed' before deleting."
            ),
        )

    # ── Step 3: shortcut for failed jobs ──────────────────────────────────
    # A failed job may have no corresponding VM in Proxmox (creation never
    # completed), so we just clean up the DB record and return early.
    if job["status"] == VMStatus.failed.value:
        database.update_vm_job(job_id=job_id, status=VMStatus.deleted.value)
        log_event(
            user_id=current_user.id,
            action="vm.delete",
            target_type="vm_job",
            target_id=str(job_id),
            details={
                "vmid":    job.get("vmid"),
                "vm_name": job.get("vm_name"),
                "note":    "job was already failed — no Proxmox call needed",
            },
        )
        logger.info(
            "VM job %s was 'failed'; marked deleted without Proxmox call.", job_id,
        )
        return VMJobResponse.model_validate(database.get_vm_job(job_id))

    # ── Step 4: stop the VM if it is currently running ────────────────────
    # Proxmox refuses to delete a running VM, so we must stop it first.
    # We check the live state before sending the stop to avoid an unnecessary
    # stop request (and its brief delay) when the VM is already stopped.
    vmid = job["vmid"]
    node = job["request_payload"].get("node", proxmox.default_node)

    try:
        live = proxmox.get_vm_status(vmid)

        if live.get("status") == "running":
            logger.info("VM %s is running — sending hard stop before deletion.", vmid)
            stop_upid = proxmox.stop_vm(vmid)
            _wait_for_task(node=node, upid=stop_upid, timeout=30)
            logger.info("Stop confirmed for VM %s. Proceeding to delete.", vmid)

    except ProxmoxAPIError as exc:
        # If we can't even check/stop the VM, abort rather than risk leaving
        # Proxmox in a broken state.
        logger.error("Could not stop VM %s before deletion: %s", vmid, exc)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.failed.value,
            error_message=f"Pre-deletion stop failed: {exc}",
        )
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return VMJobResponse.model_validate(database.get_vm_job(job_id))

    except Exception as exc:
        # Non-Proxmox errors (network blip, etc.) — same behaviour: abort.
        logger.error("Unexpected error stopping VM %s: %s", vmid, exc)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.failed.value,
            error_message=f"Unexpected error during pre-deletion stop: {exc}",
        )
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return VMJobResponse.model_validate(database.get_vm_job(job_id))

    # ── Step 5: delete the VM on Proxmox ──────────────────────────────────
    try:
        proxmox.delete_vm(vmid)
        logger.info("Deletion task submitted to Proxmox for VM %s.", vmid)

    except ProxmoxAPIError as exc:
        logger.error("Proxmox refused to delete VM %s: %s", vmid, exc)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.failed.value,
            error_message=f"Deletion failed on Proxmox: {exc}",
        )
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return VMJobResponse.model_validate(database.get_vm_job(job_id))

    except Exception as exc:
        logger.error("Unexpected error deleting VM %s: %s", vmid, exc)
        database.update_vm_job(
            job_id=job_id,
            status=VMStatus.failed.value,
            error_message=f"Unexpected deletion error: {exc}",
        )
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return VMJobResponse.model_validate(database.get_vm_job(job_id))

    # ── Step 6: mark the job as deleted in the DB ─────────────────────────
    database.update_vm_job(job_id=job_id, status=VMStatus.deleted.value)

    # ── Step 7: write audit log ───────────────────────────────────────────
    log_event(
        user_id=current_user.id,
        action="vm.delete",
        target_type="vm_job",
        target_id=str(job_id),
        details={
            "vmid":    vmid,
            "vm_name": job.get("vm_name"),
        },
    )

    logger.info(
        "VM job %s (vmid=%s) deleted by user '%s'.",
        job_id, vmid, current_user.username,
    )

    # ── Step 8: return the final state of the job ─────────────────────────
    return VMJobResponse.model_validate(database.get_vm_job(job_id))


# =============================================================================
# Utility helpers: map OS choice → Proxmox ostype / ISO path
# =============================================================================

_OS_MAP = {
    "ubuntu-22.04": {
        "ostype": "l26",
        "iso":    "local:iso/ubuntu-22.04-live-server-amd64.iso",
    },
    "ubuntu-24.04": {
        "ostype": "l26",
        "iso":    "local:iso/ubuntu-24.04.4-desktop-amd64.iso",
    },
    "debian-12": {
        "ostype": "l26",
        "iso":    "local:iso/debian-12-netinst-amd64.iso",
    },
    "centos-9": {
        "ostype": "l26",
        "iso":    "local:iso/CentOS-Stream-9-latest-x86_64-dvd1.iso",
    },
    "windows-11": {
        "ostype": "win11",
        "iso":    "local:iso/Win11_23H2_English_x64.iso",
    },
}


def _map_os_to_proxmox_type(os_choice: str) -> str:
    """Return the Proxmox ostype string for the given OS choice."""
    return _OS_MAP.get(os_choice, {}).get("ostype", "l26")


def _map_os_to_iso(os_choice: str) -> str | None:
    """Return the Proxmox ISO path for the given OS choice, or None."""
    return _OS_MAP.get(os_choice, {}).get("iso")


# =============================================================================
# Helper: provision a VM by cloning a golden template
# =============================================================================

# Default cloud-init username for cloned VMs.
_DEFAULT_CIUSER = "ubuntu"


def _generate_ci_password(length: int = 16) -> str:
    """Generate a unique random cloud-init password for each new VM clone."""
    return secrets.token_urlsafe(length)

# How long to wait for the Proxmox clone task to finish before giving up.
_CLONE_TIMEOUT_SECONDS = 180
_CLONE_POLL_INTERVAL   = 2


def _wait_for_task(node: str, upid: str, timeout: int = _CLONE_TIMEOUT_SECONDS) -> None:
    """
    Block until a Proxmox task finishes or times out.

    Raises ProxmoxAPIError if the task fails or does not finish in time.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = proxmox.get_task_status(node=node, upid=upid)
        if task.get("status") == "stopped":
            exit_status = task.get("exitstatus", "")
            if exit_status != "OK":
                raise ProxmoxAPIError(
                    f"Proxmox task {upid} failed: {exit_status}"
                )
            return
        time.sleep(_CLONE_POLL_INTERVAL)

    raise ProxmoxAPIError(
        f"Proxmox task {upid} did not finish within {timeout}s"
    )


def _provision_from_template(
    template_vmid: int,
    vm_request: VMCreateRequest,
    new_vmid: int,
) -> Dict[str, object]:
    """
    Fast path: clone a pre-built golden template, then resize disk and
    configure cloud-init so the new VM boots with the user's requested
    CPU/RAM/disk and a login account.

    Steps:
      1. Clone the template → new VMID (async, wait for task to finish).
      2. Update CPU + memory on the new VM.
      3. Resize scsi0 up to the requested disk size.
      4. Set cloud-init user/password and DHCP networking.
      5. Start the VM.

    If any step after cloning fails, the orphaned clone is deleted before
    re-raising the error so it doesn't waste resources on Proxmox.

    Returns a dict with vmid, ci_username, and ci_password.
    Raises ProxmoxAPIError on failure (caller converts to a failed job row).
    """
    node = vm_request.node

    # 1. Clone (async task on Proxmox)
    clone_upid = proxmox.clone_template(
        template_vmid=template_vmid,
        new_vmid=new_vmid,
        name=vm_request.vm_name,
        node=node,
        full=True,
    )
    _wait_for_task(node=node, upid=clone_upid)

    # Generate a unique password for this VM
    ci_password = _generate_ci_password()

    try:
        # 2. Apply CPU + memory (template defaults to 2 cores / 2 GB)
        proxmox.update_vm_config(
            vmid=new_vmid,
            node=node,
            cores=vm_request.cpu_cores,
            memory=vm_request.ram_mb,
        )

        # 3. Grow the cloned disk to match the requested size.
        #    Template disks are small (~2 GB); resize is non-destructive.
        proxmox.resize_disk(
            vmid=new_vmid,
            size_gb=vm_request.storage_gb,
            disk="scsi0",
            node=node,
        )

        # 4. Cloud-init credentials + DHCP — applied at first boot by cloud-init
        proxmox.set_cloudinit_user(
            vmid=new_vmid,
            ciuser=_DEFAULT_CIUSER,
            cipassword=ci_password,
            node=node,
        )

        # 5. Start the VM so the user can actually use it
        proxmox.start_vm(vmid=new_vmid, node=node)

    except Exception:
        # Rollback: delete the orphaned clone so it doesn't waste resources
        logger.warning(
            "Post-clone configuration failed for VM %s. Attempting cleanup.",
            new_vmid,
        )
        try:
            proxmox.delete_vm(vmid=new_vmid, node=node)
        except Exception as cleanup_exc:
            logger.error(
                "Cleanup of orphaned VM %s also failed: %s",
                new_vmid, cleanup_exc,
            )
        raise  # re-raise the original error so the caller marks the job as failed

    logger.info(
        "Provisioned VM %s by cloning template %s "
        "(cores=%s, ram=%sMB, disk=%sG)",
        new_vmid, template_vmid, vm_request.cpu_cores,
        vm_request.ram_mb, vm_request.storage_gb,
    )
    return {
        "vmid": new_vmid,
        "ci_username": _DEFAULT_CIUSER,
        "ci_password": ci_password,
    }