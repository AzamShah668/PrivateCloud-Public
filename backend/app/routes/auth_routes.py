# =============================================================================
# routes/auth_routes.py
# =============================================================================
# All authentication-related API endpoints live here.
#
# Endpoints:
#   POST /auth/register  → create a new account
#   POST /auth/login     → verify credentials, return JWT token
#   GET  /auth/me        → return the currently logged-in user's profile
#
# How FastAPI routing works:
#   We create an APIRouter (not the full app), then in main.py we do:
#       app.include_router(auth_router)
#   This keeps each file focused on its own concern.
#
# Every route is a plain Python function decorated with @router.post / @router.get.
# FastAPI reads the function's type hints and automatically:
#   - Parses and validates the request body (via Pydantic)
#   - Generates OpenAPI docs at /docs
#   - Returns appropriate 422 errors for bad input
# =============================================================================

import logging

import psycopg2
import psycopg2.errors          # must be imported explicitly — not loaded by `import psycopg2` alone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    TokenResponse,
)
from db import database
from app.models.user import UserCreate, UserResponse, UserInDB, UserUpdateRequest

logger = logging.getLogger(__name__)

# prefix="/auth" means all routes here are accessible at /auth/<path>
# tags=["Authentication"] groups them in the /docs UI
router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    Called after every significant action (login, register, etc.).

    We wrap this in a try/except so a logging failure NEVER crashes
    the main request — audit logs are important but not worth failing
    a user's login over.
    """
    try:
        database.add_audit_log(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            details=details,
        )
    except Exception as exc:
        logger.error(f"Failed to write audit log [{action}]: {exc}")


# =============================================================================
# POST /auth/register
# =============================================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(user_data: UserCreate):
    """
    Create a new user account.

    Request body:
        {
            "username": "azam",
            "password": "securepassword123",
            "role": "user",          # optional, defaults to "user"
            "daily_quota": 3         # optional; if omitted uses the
                                     # 'quota.default_daily' platform setting
        }

    Returns the created user (without the password hash).

    Errors:
        409 Conflict — if the username is already taken.
    """
    # ── Step 1: check that the username is not already taken ──────────────
    existing = database.get_user_by_username(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_data.username}' is already taken. Choose another.",
        )

    # ── Step 2: hash the password (NEVER store plain text) ────────────────
    hashed = hash_password(user_data.password)

    # ── Step 3: resolve daily_quota from the platform-wide setting ────────
    # If the caller did not pass daily_quota explicitly, we fall back to the
    # 'quota.default_daily' system setting. This lets an admin change the
    # default for future signups from the Admin → Settings page without a
    # redeploy. The final safety net (3) covers the case where the setting
    # row is missing or unreadable.
    if user_data.daily_quota is not None:
        effective_quota = user_data.daily_quota
    else:
        effective_quota = database.get_setting("quota.default_daily") or 3

    # ── Step 4: create the database object ──────────────────────
    try:
        new_user_id = database.create_user(
            username=user_data.username,
            password_hash=hashed,
            role=user_data.role,
            daily_quota=effective_quota,
        )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_data.username}' is already taken. Choose another.",
        )

    new_user = database.get_user_by_id(new_user_id)

    # ── Step 4: write audit log ───────────────────────────────────────────
    log_event(
        user_id=new_user["id"],
        action="user.register",
        target_type="user",
        target_id=str(new_user["id"]),
        details={"username": new_user["username"], "role": new_user["role"]},
    )

    logger.info(f"New user registered: '{new_user['username']}' (id={new_user['id']})")

    # ── Step 5: return the user (Pydantic validates/filters the output) ───
    # UserResponse.model_validate() works with plain dictionaries
    return UserResponse.model_validate(new_user)


# =============================================================================
# POST /auth/login
# =============================================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT access token",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Authenticate with username + password and receive a JWT token.

    Uses OAuth2PasswordRequestForm which expects form-encoded data:
        username=azam&password=secret

    This is the standard OAuth2 format, and it's what the Swagger /docs
    page uses when you click "Authorize". It means you can test the
    whole API from the browser without any extra tools.

    Returns:
        { "access_token": "eyJ...", "token_type": "bearer" }

    Errors:
        401 Unauthorized — wrong username or password.
    """
    # ── Step 1: find the user ─────────────────────────────────────────────
    # Normalise to lowercase — registration lowercases via the UserCreate
    # validator, so we must do the same here to match.
    username = form_data.username.strip().lower()
    user_dict = database.get_user_by_username(username)

    # ── Step 2: maintenance-mode gate ─────────────────────────────────────
    # If an admin has flipped 'platform.maintenance' to true, block any
    # non-admin login attempt with 503 so the user sees the real reason
    # (and doesn't get a misleading "wrong password" message). Admins can
    # still log in to flip the setting back.
    if database.get_setting("platform.maintenance"):
        is_admin = bool(user_dict) and user_dict.get("role") == "admin"
        if not is_admin:
            logger.info(
                "Blocking login for '%s' — platform.maintenance is enabled.",
                username,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "The platform is currently in maintenance mode. "
                    "Please try again later."
                ),
            )

    # ── Step 3: verify password ───────────────────────────────────────────
    # IMPORTANT: we check both user existence AND password in one condition.
    # This prevents "username enumeration" attacks where an attacker can
    # tell from the error message whether a username exists or not.
    if not user_dict or not verify_password(form_data.password, user_dict["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = UserInDB(**user_dict)

    # ── Step 3: create the JWT ────────────────────────────────────────────
    # "sub" (subject) is the standard JWT claim for who the token identifies.
    # We also put "role" in the token so routes can check it WITHOUT a DB query.
    token = create_access_token(data={
        "sub":  user.username,
        "role": user.role,
    })

    # ── Step 4: write audit log ───────────────────────────────────────────
    log_event(
        user_id=user.id,
        action="user.login",
        target_type="user",
        target_id=str(user.id),
        details={"username": user.username},
    )

    logger.info(f"User '{user.username}' logged in.")

    return TokenResponse(access_token=token)


# =============================================================================
# GET /auth/me
# =============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user's profile",
)
def get_me(current_user: UserInDB = Depends(get_current_user)):
    """
    Returns the profile of the user who owns the current JWT token.

    The token is read from the Authorization header automatically by the
    get_current_user dependency — you don't need to pass it explicitly.

    Useful for: "who am I?" checks in the frontend after login.

    Errors:
        401 Unauthorized — missing or invalid token.
    """
    return UserResponse.model_validate(current_user.model_dump())


# =============================================================================
# PATCH /auth/me
# =============================================================================

@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the current user's credentials",
)
def update_me(
    update_data: UserUpdateRequest,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Update the authenticated user's credentials.

    You can change any combination of:
      - **username** — must be unique and at least 3 characters, no spaces.
      - **password** — supply `current_password` (proof of identity) and
        `new_password` (min 8 chars).
      - **daily_quota** — regular users can only *lower* their own quota;
        admins can set it to any positive value.

    At least one changeable field must be provided, otherwise a 400 is returned.

    Returns the updated user profile (without the password hash).

    Errors:
        400 Bad Request  — nothing to update, or `current_password` missing
                           when changing password.
        401 Unauthorized — `current_password` is wrong.
        409 Conflict     — chosen username is already taken.
    """
    # ── Guard: at least one field must be changing ────────────────────────
    if (
        update_data.username     is None
        and update_data.new_password is None
        and update_data.daily_quota  is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Nothing to update. Supply at least one of: "
                "username, new_password, daily_quota."
            ),
        )

    # ── Password change validation ────────────────────────────────────────
    new_password_hash: str | None = None

    if update_data.new_password is not None:
        # Require current_password as proof of identity before allowing a
        # password change — prevents someone with a stolen session token from
        # locking out the real owner.
        if not update_data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="current_password is required when setting a new password.",
            )

        if not verify_password(update_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="current_password is incorrect.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        new_password_hash = hash_password(update_data.new_password)

    # ── Username uniqueness check ─────────────────────────────────────────
    if update_data.username is not None and update_data.username != current_user.username:
        if database.get_user_by_username(update_data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{update_data.username}' is already taken.",
            )

    # ── daily_quota guard for non-admins ──────────────────────────────────
    final_quota: int | None = update_data.daily_quota
    if final_quota is not None and current_user.role != "admin":
        # Regular users cannot raise their own quota
        if final_quota > current_user.daily_quota:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You cannot increase your own daily_quota. "
                    "Contact an admin to raise your limit."
                ),
            )

    # ── Apply the update ──────────────────────────────────────────────────
    try:
        database.update_user_credentials(
            current_user.id,
            username=update_data.username,
            password_hash=new_password_hash,
            daily_quota=final_quota,
        )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{update_data.username}' is already taken.",
        )

    # ── Audit log ─────────────────────────────────────────────────────────
    changed_fields = []
    if update_data.username     is not None: changed_fields.append("username")
    if update_data.new_password is not None: changed_fields.append("password")
    if update_data.daily_quota  is not None: changed_fields.append("daily_quota")

    log_event(
        user_id=current_user.id,
        action="user.update_credentials",
        target_type="user",
        target_id=str(current_user.id),
        details={"changed_fields": changed_fields},
    )

    logger.info(
        f"User '{current_user.username}' (id={current_user.id}) "
        f"updated: {changed_fields}"
    )

    # ── Return the fresh user record ──────────────────────────────────────
    updated_user = database.get_user_by_id(current_user.id)
    return UserResponse.model_validate(updated_user)
