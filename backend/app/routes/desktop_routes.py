# =============================================================================
# backend/app/routes/desktop_routes.py
# =============================================================================
# Apache Guacamole integration: mint in-browser RDP sessions for Windows VMs.
# =============================================================================

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.models.user import UserInDB
from app.models.vm import VMStatus
from app.services import guacamole_client
from db import database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vms", tags=["Remote Desktop"])


class DesktopSessionResponse(BaseModel):
    """URL the browser loads to open the Guacamole HTML5 RDP client."""

    client_url: str
    connection_name: str


@router.post(
    "/{job_id}/desktop-session",
    response_model=DesktopSessionResponse,
    summary="Open an in-browser RDP session (Apache Guacamole) for a Windows VM",
)
def create_windows_desktop_session(
    job_id: int,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Creates (or refreshes) a Guacamole RDP connection for this VM job and returns
    a `client_url` suitable for an iframe or new tab.

    Requirements:
      - Job must belong to the current user (or admin — same rule as other VM routes).
      - `os_choice` must be `windows-11`.
      - Job must be `done` with `vm_ip`, `vm_username`, and `vm_password` populated.
    """
    job = database.get_vm_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VM job with id={job_id} not found.",
        )

    if current_user.role != "admin" and job["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this VM.",
        )

    if job.get("os_choice") != "windows-11":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="In-browser desktop is only supported for Windows 11 VMs.",
        )

    if job.get("status") != VMStatus.done.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="VM must be fully provisioned (status 'done') before opening a remote desktop session.",
        )

    vm_ip = job.get("vm_ip")
    vm_username = job.get("vm_username")
    vm_password = job.get("vm_password")
    if not vm_ip or not vm_username or not vm_password:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="VM is missing IP or credentials; wait for provisioning to finish.",
        )

    try:
        result = guacamole_client.create_desktop_session(
            job_id=job_id,
            vm_ip=str(vm_ip),
            vm_username=str(vm_username),
            vm_password=str(vm_password),
        )
    except guacamole_client.GuacamoleConfigurationError as exc:
        logger.warning("Guacamole not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except guacamole_client.GuacamoleAPIError as exc:
        logger.error("Guacamole API error: %s", exc)
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return DesktopSessionResponse(
        client_url=result["client_url"],
        connection_name=result["connection_name"],
    )
