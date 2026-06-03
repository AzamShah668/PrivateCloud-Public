"""
Admin-only API endpoints.

All routes require the `require_admin` dependency, which checks
that the authenticated user has role == 'admin'.

Endpoints:
  GET   /admin/stats                         → aggregate dashboard statistics
  GET   /admin/users                         → list all users (I3: status + deleted_at)
  GET   /admin/vms                           → list all VM jobs (across all users)
  GET   /admin/audit-logs                    → list audit log entries (I3: filterable)
  PATCH /admin/users/{id}/role               → change a user's role
  PATCH /admin/users/{id}/quota              → change a user's daily VM quota
  POST  /admin/users/{id}/suspend            → (I3) set status='suspended'
  POST  /admin/users/{id}/delete             → (I3) soft-delete user
  POST  /admin/users/{id}/reactivate         → (I3) restore to status='active'
  GET   /admin/settings                      → (I3) list all platform settings
  PATCH /admin/settings/{key}                → (I3) update a setting value
"""

import logging
from datetime import datetime
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


class AdminUserResponse(BaseModel):
    """Extended user row with I3 soft-delete fields."""
    id: int
    username: str
    role: str
    daily_quota: int
    created_at: datetime
    deleted_at: datetime | None = None
    status: str = "active"

    model_config = {"from_attributes": True}


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
    action_type: str = "system.unknown"
    target_type: str
    target_id: str | None = None
    target_user_id: int | None = None
    actor_username: str | None = None
    target_username: str | None = None
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateRoleRequest(BaseModel):
    role: Literal["user", "admin"]


class UpdateQuotaRequest(BaseModel):
    daily_quota: int = Field(ge=0, le=100)


class SettingResponse(BaseModel):
    key: str
    value: str
    value_type: Literal["string", "integer", "boolean", "json", "secret"]
    typed_value: Any = None
    # For secret-typed settings, value/typed_value are masked (blank). `is_set`
    # tells the UI whether a secret is configured without revealing it.
    is_secret: bool = False
    is_set: bool = False
    description: str | None = None
    updated_at: datetime
    updated_by: int | None = None
    updated_by_username: str | None = None

    model_config = {"from_attributes": True}


class UpdateSettingRequest(BaseModel):
    # Accept any JSON-compatible scalar / object; we serialize to string
    # before persisting, matching the value_type column.
    value: Any


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
    response_model=List[AdminUserResponse],
    summary="List all users (with I3 soft-delete fields)",
)
def list_users(
    admin: UserInDB = Depends(require_admin),
    include_deleted: bool = Query(
        default=False,
        description="Include soft-deleted users (status='deleted')",
    ),
) -> List[AdminUserResponse]:
    users = database.list_all_users_extended(include_deleted=include_deleted)
    return [AdminUserResponse.model_validate(u) for u in users]


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
    verify_proxmox: bool = Query(
        default=False,
        description=(
            "When true, also EXCLUDE from the response any VM whose vmid is "
            "not currently on the live Proxmox node (used by the "
            "Publish-Template picker). Note: DB<->Proxmox reconciliation now "
            "runs on every call regardless of this flag."
        ),
    ),
) -> List[VMJobAdminResponse]:
    jobs = database.list_all_vm_jobs()

    # ── Reconcile the DB against live Proxmox (source of truth) ───────────
    # Any VM that has vanished from the hypervisor (deleted out-of-band in the
    # Proxmox UI) is soft-deleted in the DB here, so admins can't act on stale
    # rows (e.g. publish a template from a deleted VM — debugging journal #14)
    # and the list reflects reality. Best-effort + guarded: if Proxmox is
    # unreachable we leave the DB untouched (guard G1) and return what we have.
    live_vmids: set[int] | None = None
    try:
        from app.proxmox_client import ProxmoxClient
        from app.services.reconciliation import reconcile_vm_existence

        px = ProxmoxClient()
        px._ensure_authenticated()
        live_vmids = {int(v["vmid"]) for v in px.list_vms()}
        reconcile_vm_existence(jobs, live_vmids)
        jobs = database.list_all_vm_jobs()  # re-read: statuses now reflect soft-deletes
    except Exception as exc:
        logger.warning(
            "VM reconciliation skipped (Proxmox unreachable): %s", exc,
        )

    # Explicit "only live VMs" filter for callers that need a clean picker.
    if verify_proxmox and live_vmids is not None:
        jobs = [j for j in jobs if j["vmid"] in live_vmids]

    return [VMJobAdminResponse.model_validate(j) for j in jobs]


# ---------------------------------------------------------------------------
# GET /admin/audit-logs
# ---------------------------------------------------------------------------

@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="List audit log entries (filterable by action_type + target user)",
)
def list_audit_logs(
    admin: UserInDB = Depends(require_admin),
    action_type: Optional[str] = Query(
        default=None,
        description="Filter by action_type enum value (e.g. 'vm.create')",
    ),
    target_user_id: Optional[int] = Query(
        default=None,
        description="Filter to actions affecting this user",
    ),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> List[AuditLogResponse]:
    logs = database.list_audit_logs_filtered(
        action_type=action_type,
        target_user_id=target_user_id,
        limit=limit,
        offset=offset,
    )
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
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot change their own role.",
        )

    old = database.get_user_by_id(user_id)
    if not old:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    updated = database.update_user_role(user_id, body.role)

    database.log_action(
        user_id=admin.id,
        action_type="user.role_change",
        action=f"Changed role of user {user_id} from {old['role']} to {body.role}",
        target_type="user",
        target_id=str(user_id),
        target_user_id=user_id,
        details={"old_role": old["role"], "new_role": body.role},
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
    old = database.get_user_by_id(user_id)
    if not old:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    updated = database.update_user_quota(user_id, body.daily_quota)

    database.log_action(
        user_id=admin.id,
        action_type="user.quota_change",
        action=f"Changed quota of user {user_id} from {old['daily_quota']} to {body.daily_quota}",
        target_type="user",
        target_id=str(user_id),
        target_user_id=user_id,
        details={"old_quota": old["daily_quota"], "new_quota": body.daily_quota},
    )

    return UserResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# I3: POST /admin/users/{user_id}/suspend
# ---------------------------------------------------------------------------

@router.post(
    "/users/{user_id}/suspend",
    response_model=AdminUserResponse,
    summary="(I3) Suspend a user (status='suspended')",
)
def suspend_user(
    user_id: int,
    admin: UserInDB = Depends(require_admin),
) -> AdminUserResponse:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot suspend themselves.",
        )

    updated = database.suspend_user(user_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    database.log_action(
        user_id=admin.id,
        action_type="user.suspend",
        action=f"Suspended user {updated['username']}",
        target_type="user",
        target_id=str(user_id),
        target_user_id=user_id,
        details={"username": updated["username"]},
    )

    return AdminUserResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# I3: POST /admin/users/{user_id}/delete (soft-delete)
# ---------------------------------------------------------------------------

@router.post(
    "/users/{user_id}/delete",
    response_model=AdminUserResponse,
    summary="(I3) Soft-delete a user (status='deleted', deleted_at=NOW)",
)
def delete_user(
    user_id: int,
    admin: UserInDB = Depends(require_admin),
) -> AdminUserResponse:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot delete themselves.",
        )

    updated = database.soft_delete_user(user_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    database.log_action(
        user_id=admin.id,
        action_type="user.delete",
        action=f"Soft-deleted user {updated['username']}",
        target_type="user",
        target_id=str(user_id),
        target_user_id=user_id,
        details={"username": updated["username"]},
    )

    return AdminUserResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# I3: POST /admin/users/{user_id}/reactivate
# ---------------------------------------------------------------------------

@router.post(
    "/users/{user_id}/reactivate",
    response_model=AdminUserResponse,
    summary="(I3) Reactivate a suspended or soft-deleted user",
)
def reactivate_user(
    user_id: int,
    admin: UserInDB = Depends(require_admin),
) -> AdminUserResponse:
    updated = database.reactivate_user(user_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    database.log_action(
        user_id=admin.id,
        action_type="user.reactivate",
        action=f"Reactivated user {updated['username']}",
        target_type="user",
        target_id=str(user_id),
        target_user_id=user_id,
        details={"username": updated["username"]},
    )

    return AdminUserResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# I3: GET /admin/settings
# ---------------------------------------------------------------------------

@router.get(
    "/settings",
    response_model=List[SettingResponse],
    summary="(I3) List all platform settings",
)
def list_platform_settings(
    admin: UserInDB = Depends(require_admin),
) -> List[SettingResponse]:
    return [SettingResponse.model_validate(s) for s in database.list_settings()]


# ---------------------------------------------------------------------------
# I3: PATCH /admin/settings/{key}
# ---------------------------------------------------------------------------

@router.patch(
    "/settings/{key}",
    response_model=SettingResponse,
    summary="(I3) Update a platform setting value",
)
def update_platform_setting(
    key: str,
    body: UpdateSettingRequest,
    admin: UserInDB = Depends(require_admin),
) -> SettingResponse:
    # Serialize the incoming value to the TEXT format system_settings expects.
    # Type coercion happens on read via _cast_setting_value().
    raw_value = body.value
    if isinstance(raw_value, bool):
        str_value = "true" if raw_value else "false"
    elif isinstance(raw_value, (int, float)):
        str_value = str(raw_value)
    elif isinstance(raw_value, (dict, list)):
        import json as _json
        str_value = _json.dumps(raw_value)
    else:
        str_value = str(raw_value)

    # Record the old value so the audit entry shows the diff (non-secrets only).
    old = database.get_setting(key)

    updated = database.set_setting(key, str_value, admin.id)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Setting key '{key}' not found. Settings are seeded at "
                "database init — new keys cannot be created at runtime."
            ),
        )

    # Refresh the config cache so the new value takes effect immediately — the
    # Proxmox/LLM clients rebuild on their next call (config generation bumps).
    from app import config as app_config
    app_config.invalidate_cache()

    # Never write secret plaintext into the audit log.
    if updated.get("is_secret"):
        audit_details = {"key": key, "secret": True, "is_set": updated.get("is_set")}
    else:
        audit_details = {"key": key, "old": old, "new": updated["typed_value"]}

    database.log_action(
        user_id=admin.id,
        action_type="settings.change",
        action=f"Changed setting '{key}'",
        target_type="setting",
        target_id=key,
        target_user_id=None,
        details=audit_details,
    )

    return SettingResponse.model_validate(updated)
