"""
Admin-only API endpoints.

All routes require the `require_admin` dependency, which checks
that the authenticated user has role == 'admin'.

Endpoints:
  GET  /admin/stats       → aggregate dashboard statistics
  GET  /admin/users       → list all users
  GET  /admin/vms         → list all VM jobs (across all users)
  GET  /admin/audit-logs  → list audit log entries
  PATCH /admin/users/{id}/role   → change a user's role
  PATCH /admin/users/{id}/quota  → change a user's daily VM quota
"""

import logging
from datetime import datetime
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import require_admin
from app.models.user import UserInDB, UserResponse
from db import database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class AdminStatsResponse(BaseModel):
    total_users: int
    total_admins: int
    total_vms: int
    active_vms: int
    failed_vms: int
    queued_vms: int
    deleted_vms: int
    total_audit_entries: int
    vms_created_today: int


class VMJobAdminResponse(BaseModel):
    """VM job with owner username for admin views."""
    id: int
    user_id: int
    owner_username: str
    vmid: int
    vm_name: str
    os_choice: str
    status: str
    request_payload: dict
    proxmox_response: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    target_type: str
    target_id: str | None = None
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateRoleRequest(BaseModel):
    role: Literal["user", "admin"]


class UpdateQuotaRequest(BaseModel):
    daily_quota: int = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# GET /admin/stats
# ---------------------------------------------------------------------------

@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get aggregate dashboard statistics",
)
def get_stats(
    admin: UserInDB = Depends(require_admin),
) -> AdminStatsResponse:
    stats = database.get_admin_stats()
    return AdminStatsResponse(**stats)


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users",
)
def list_users(
    admin: UserInDB = Depends(require_admin),
) -> List[UserResponse]:
    users = database.list_all_users()
    return [UserResponse.model_validate(u) for u in users]


# ---------------------------------------------------------------------------
# GET /admin/vms
# ---------------------------------------------------------------------------

@router.get(
    "/vms",
    response_model=List[VMJobAdminResponse],
    summary="List all VM jobs across all users",
)
def list_all_vms(
    admin: UserInDB = Depends(require_admin),
) -> List[VMJobAdminResponse]:
    jobs = database.list_all_vm_jobs()
    return [VMJobAdminResponse.model_validate(j) for j in jobs]


# ---------------------------------------------------------------------------
# GET /admin/audit-logs
# ---------------------------------------------------------------------------

@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="List audit log entries",
)
def list_audit_logs(
    admin: UserInDB = Depends(require_admin),
) -> List[AuditLogResponse]:
    logs = database.list_audit_logs(limit=200)
    return [AuditLogResponse.model_validate(log) for log in logs]


# ---------------------------------------------------------------------------
# PATCH /admin/users/{user_id}/role
# ---------------------------------------------------------------------------

@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Change a user's role",
)
def change_user_role(
    user_id: int,
    body: UpdateRoleRequest,
    admin: UserInDB = Depends(require_admin),
) -> UserResponse:
    # Prevent admins from demoting themselves (could lock out all admins)
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot change their own role.",
        )

    updated = database.update_user_role(user_id, body.role)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    database.add_audit_log(
        user_id=admin.id,
        action="admin.update_role",
        target_type="user",
        target_id=str(user_id),
        details={"new_role": body.role},
    )

    return UserResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# PATCH /admin/users/{user_id}/quota
# ---------------------------------------------------------------------------

@router.patch(
    "/users/{user_id}/quota",
    response_model=UserResponse,
    summary="Change a user's daily VM quota",
)
def change_user_quota(
    user_id: int,
    body: UpdateQuotaRequest,
    admin: UserInDB = Depends(require_admin),
) -> UserResponse:
    # Pydantic Field(ge=0, le=100) handles bounds validation automatically
    updated = database.update_user_quota(user_id, body.daily_quota)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    database.add_audit_log(
        user_id=admin.id,
        action="admin.update_quota",
        target_type="user",
        target_id=str(user_id),
        details={"new_quota": body.daily_quota},
    )

    return UserResponse.model_validate(updated)
