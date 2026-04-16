# =============================================================================
# models/user.py
# =============================================================================
# This file contains TWO kinds of model for the User concept:
#
#   1. SQLAlchemy ORM model  (class User)
#      → Maps directly to the `users` table in PostgreSQL.
#      → Used when reading/writing to the database.
#
#   2. Pydantic schemas  (UserCreate, UserResponse, …)
#      → Used for request validation (what the API accepts)
#        and response serialisation (what the API returns).
#      → Pydantic validates data types, required fields, and
#        constraints automatically — you get a 422 error for free
#        if the client sends bad data.
#
# Why keep both in one file?
#   They describe the same entity (a User), so keeping them together
#   makes it easier to see at a glance what the table looks like AND
#   what the API exposes, without having to jump between files.
# =============================================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# =============================================================================
# ── Pydantic Schemas ──────────────────────────────────────────────────────────
#
# Naming convention used here:
#   UserCreate   → body of POST /auth/register
#   UserResponse → what the API returns (never exposes password_hash)
#   UserInDB     → internal shape that includes password_hash (used by auth.py)
# =============================================================================

class UserCreate(BaseModel):
    """
    Schema for registering a new user.
    The client sends { "username": "...", "password": "..." }.
    The route handler will hash the password before saving.
    """
    username: str
    password: str
    # role is optional — clients can't set themselves to 'admin'.
    # Only an existing admin can upgrade a user (future sprint).
    role: str = "user"
    daily_quota: int = 3

    # ── Validators ────────────────────────────────────────────────────────
    # @field_validator runs after Pydantic's type check.
    # mode='before' means it runs on the raw input value (before coercion).

    @field_validator("username")
    @classmethod
    def username_no_spaces(cls, v: str) -> str:
        """Usernames must not contain spaces."""
        if " " in v:
            raise ValueError("Username must not contain spaces.")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters.")
        return v.lower()  # normalise to lowercase for consistency

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        """Enforce a minimum password length of 8 characters."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        allowed = {"user", "admin"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


class UserResponse(BaseModel):
    """
    What the API returns when talking about a user.
    Note: password_hash is intentionally ABSENT — never send it to clients.
    """
    id: int
    username: str
    role: str
    daily_quota: int
    created_at: datetime

    # model_config with from_attributes=True tells Pydantic it's allowed
    # to read values from ORM object attributes (not just dicts).
    # This is what lets you do UserResponse.model_validate(user_orm_object).
    model_config = {"from_attributes": True}


class UserInDB(UserResponse):
    """
    Internal schema that extends UserResponse with the password hash.
    Used inside auth.py for the password verification step.
    We keep it separate so there's no risk of accidentally including
    password_hash in a normal API response.
    """
    password_hash: str


class UserUpdateRequest(BaseModel):
    """
    Schema for PATCH /auth/me — update the current user's credentials.

    All fields are optional so the client can send only what it wants to change.

    Rules:
      - `username`:         new desired username (same validation as registration).
      - `current_password`: REQUIRED when changing password (proves ownership).
      - `new_password`:     the replacement password (min 8 chars).
      - `daily_quota`:      self-service quota change (admin can set any value;
                            regular users are capped at their current quota in
                            the route handler).

    At least one field must be present (enforced in the route handler).
    """
    username:         Optional[str] = None
    current_password: Optional[str] = None   # proof of identity for pw change
    new_password:     Optional[str] = None
    daily_quota:      Optional[int] = None

    @field_validator("username")
    @classmethod
    def username_no_spaces(cls, v: str) -> str:
        if v is None:
            return v
        if " " in v:
            raise ValueError("Username must not contain spaces.")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters.")
        return v.lower()

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters.")
        return v

    @field_validator("daily_quota")
    @classmethod
    def quota_positive(cls, v: int) -> int:
        if v is not None and v < 1:
            raise ValueError("daily_quota must be at least 1.")
        return v
