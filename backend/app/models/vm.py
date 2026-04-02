# =============================================================================
# models/vm.py
# =============================================================================
# This file defines everything related to Virtual Machine jobs.
#
# The core table is `vm_jobs` (not `vms`).  Why "jobs"?  Because creating
# a VM is an *asynchronous operation*: the API accepts the request
# immediately (status = queued), hands it off to Proxmox in the background,
# and updates the row when Proxmox confirms success or failure.
# So each row represents a *job request*, not just a static VM record.
#
# Status lifecycle:
#
#     queued → running → done → deleted
#                     ↘ failed  (error_message populated)
#
# Contents of this file:
#   1. VMStatus         — Enum for all possible vm_job states
#   2. OS_Choice        — Enum for allowed OS templates
#   3. VMCreateRequest  — Pydantic: what the client POSTs to create a VM
#   4. VMJobResponse    — Pydantic: what the API returns about a job
#   5. AuditLogResponse — Pydantic: what the API returns about an audit entry
# =============================================================================

from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict

from pydantic import BaseModel, field_validator


# =============================================================================
# ── Enums ─────────────────────────────────────────────────────────────────────
# Using Python Enum keeps the allowed values in one place. If you type a wrong
# status string somewhere in the code, Python raises an error immediately
# instead of silently saving garbage to the DB.
# =============================================================================

class VMStatus(str, Enum):
    """
    All possible states a vm_job row can be in.
    `str` as a base class means the enum value IS the string, so you can
    compare directly: job["status"] == VMStatus.done  →  True
    """
    queued  = "queued"    # accepted by API, not yet sent to Proxmox
    running = "running"   # ProxmoxClient.create_vm() is in progress
    done    = "done"      # Proxmox confirmed VM creation success
    failed  = "failed"    # something went wrong; check error_message
    deleted = "deleted"   # VM was successfully destroyed on Proxmox


class OS_Choice(str, Enum):
    """
    Allowed operating system templates. Add more as you expand the catalog.
    These map to ISO file names stored on the Proxmox node.
    """
    ubuntu_22  = "ubuntu-22.04"
    ubuntu_24  = "ubuntu-24.04"
    debian_12  = "debian-12"
    centos_9   = "centos-9"
    windows_11 = "windows-11"


# =============================================================================
# ── Pydantic Schemas ──────────────────────────────────────────────────────────
# =============================================================================

class VMCreateRequest(BaseModel):
    """
    Body the client must POST to /vms/ to request a new VM.
    All fields are validated by Pydantic before the route handler runs.

    Example JSON body:
    {
        "vm_name": "my-web-server",
        "os_choice": "ubuntu-22.04",
        "cpu_cores": 2,
        "ram_mb": 2048,
        "storage_gb": 20,
        "node": "pve"
    }
    """
    vm_name:    str
    os_choice:  OS_Choice   # must be one of the allowed OS values
    cpu_cores:  int
    ram_mb:     int
    storage_gb: int
    # Proxmox node to create the VM on. Defaults to "pve" (the default node name).
    node: str = "pve"

    @field_validator("vm_name")
    @classmethod
    def vm_name_valid(cls, v: str) -> str:
        """VM names: 3-30 chars, letters/digits/hyphens only."""
        import re
        if not re.match(r'^[a-zA-Z0-9\-]{3,30}$', v):
            raise ValueError(
                "vm_name must be 3-30 characters, letters/digits/hyphens only."
            )
        return v

    @field_validator("cpu_cores")
    @classmethod
    def cpu_cores_range(cls, v: int) -> int:
        if not (1 <= v <= 16):
            raise ValueError("cpu_cores must be between 1 and 16.")
        return v

    @field_validator("ram_mb")
    @classmethod
    def ram_mb_range(cls, v: int) -> int:
        # Minimum 512 MB, max 65536 MB (64 GB)
        if not (512 <= v <= 65536):
            raise ValueError("ram_mb must be between 512 and 65536.")
        return v

    @field_validator("storage_gb")
    @classmethod
    def storage_range(cls, v: int) -> int:
        if not (10 <= v <= 500):
            raise ValueError("storage_gb must be between 10 and 500.")
        return v


class VMJobResponse(BaseModel):
    """
    What the API returns for a vm_job row.
    Maps 1-to-1 with the vm_jobs DB table (minus internal implementation details).
    """
    id:               int
    user_id:          int
    vmid:             int
    vm_name:          str
    os_choice:        str
    status:           str
    request_payload:  Dict[str, Any]
    proxmox_response: Optional[Dict[str, Any]] = None
    error_message:    Optional[str]            = None
    created_at:       datetime
    updated_at:       datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    """Response schema for audit log entries."""
    id:          int
    user_id:     Optional[int]
    action:      str
    target_type: str
    target_id:   Optional[str]
    details:     Dict[str, Any]
    created_at:  datetime

    model_config = {"from_attributes": True}