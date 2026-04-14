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
from app.models.user import UserCreate, UserResponse, UserInDB

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
            "daily_quota": 3         # optional, defaults to 3
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

    # ── Step 3: create the database object ──────────────────────
    try:
        new_user_id = database.create_user(
            username=user_data.username,
            password_hash=hashed,
            role=user_data.role,
            daily_quota=user_data.daily_quota,
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

    # ── Step 2: verify password ───────────────────────────────────────────
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
