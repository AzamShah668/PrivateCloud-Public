# =============================================================================
# routes/setup_routes.py
# =============================================================================
# First-run admin onboarding (Iteration 6, Kanban #53-#55).
#
# The operational config that used to live in .env (Proxmox connector, LLM
# provider, VM creds, Guacamole) is now stored in system_settings and entered
# through a setup wizard on first login. These endpoints drive that wizard:
#
#   GET  /setup/status  → is setup done? what's still missing? (any logged-in user)
#   POST /setup         → apply Proxmox + LLM config, optionally test the
#                         Proxmox connection, mark setup complete (admin only)
#
# Secret values are encrypted at rest by database.set_setting(); this module
# never sees ciphertext and never returns secrets.
# =============================================================================

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app import config
from app.auth import get_current_user, require_admin
from app.models.user import UserInDB
from db import database
from db.config_registry import CONFIG_REGISTRY, REQUIRED_FOR_SETUP

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["Setup"])

_SETUP_COMPLETED_KEY = "setup.completed"

# Keys the wizard may write — everything in the registry except the internal
# completion flag (set by this module, not the client).
_WIZARD_KEYS = {ck.key for ck in CONFIG_REGISTRY if ck.key != _SETUP_COMPLETED_KEY}


class SetupStatusResponse(BaseModel):
    completed: bool
    proxmox_configured: bool
    missing_required: list[str]


class SetupRequest(BaseModel):
    # Map of setting key -> value (e.g. {"proxmox.host": "192.168.1.57", ...}).
    settings: dict[str, Any]
    test_connection: bool = True


class SetupResultResponse(BaseModel):
    ok: bool
    completed: bool
    proxmox_ok: bool | None = None
    error: str | None = None


def _missing_required() -> list[str]:
    """Required keys that are still empty/unset."""
    return [k for k in REQUIRED_FOR_SETUP if config.get_config(k) in (None, "")]


def _to_str(value: Any) -> str:
    """Serialise an incoming JSON value to the TEXT form system_settings stores."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return "" if value is None else str(value)


def _test_proxmox() -> tuple[bool, str | None]:
    """Best-effort live check that the just-saved Proxmox config actually works."""
    try:
        from app.proxmox_client import get_proxmox_client
        client = get_proxmox_client()
        client._ensure_authenticated()
        client.list_vms()
        return True, None
    except Exception as exc:  # noqa: BLE001 - surface the reason to the wizard
        return False, str(exc)


@router.get(
    "/status",
    response_model=SetupStatusResponse,
    summary="First-run setup status (drives the onboarding wizard)",
)
def setup_status(
    current_user: UserInDB = Depends(get_current_user),
) -> SetupStatusResponse:
    stored = bool(database.get_setting(_SETUP_COMPLETED_KEY))
    missing = _missing_required()
    # Treat setup as complete if the admin explicitly finished it OR the required
    # connector is already resolvable (e.g. an existing deployment whose Proxmox
    # config still comes from .env) — so upgrades aren't forced through the wizard.
    completed = stored or not missing
    return SetupStatusResponse(
        completed=completed,
        proxmox_configured=not missing,
        missing_required=missing,
    )


@router.post(
    "",
    response_model=SetupResultResponse,
    summary="Apply first-run setup (Proxmox connector + LLM provider)",
)
def apply_setup(
    body: SetupRequest,
    admin: UserInDB = Depends(require_admin),
) -> SetupResultResponse:
    unknown = sorted(k for k in body.settings if k not in _WIZARD_KEYS)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown setup keys: {', '.join(unknown)}",
        )

    # Persist every provided setting (set_setting handles type + encryption).
    for key, value in body.settings.items():
        database.set_setting(key, _to_str(value), admin.id)

    # Make the new config live immediately (Proxmox/LLM clients rebuild).
    config.invalidate_cache()

    proxmox_ok: bool | None = None
    error: str | None = None
    if body.test_connection:
        proxmox_ok, error = _test_proxmox()

    # Mark setup complete once the required connector fields are present.
    missing = _missing_required()
    completed = not missing
    if completed:
        database.set_setting(_SETUP_COMPLETED_KEY, "true", admin.id)
        config.invalidate_cache()

    try:
        database.add_audit_log(
            user_id=admin.id,
            action="setup.apply",
            target_type="setup",
            target_id="first-run",
            details={
                "keys": sorted(body.settings.keys()),
                "completed": completed,
                "proxmox_ok": proxmox_ok,
            },
        )
    except Exception as exc:  # noqa: BLE001 - audit is non-critical
        logger.warning("Failed to write setup audit log: %s", exc)

    return SetupResultResponse(
        ok=True, completed=completed, proxmox_ok=proxmox_ok, error=error
    )
