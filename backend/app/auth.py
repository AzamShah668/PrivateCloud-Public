# =============================================================================
# auth.py
# =============================================================================
# This file handles ALL authentication logic in one place:
#
#   1. Password hashing  — bcrypt via passlib
#   2. JWT creation      — encode a signed token with the user's identity
#   3. JWT verification  — decode & validate an incoming token
#   4. FastAPI dependency — get_current_user() that routes can use with Depends()
#   5. Admin guard       — require_admin() that restricts admin-only routes
#
# Why JWT?
#   JSON Web Tokens are self-contained: the server doesn't need to store
#   sessions in a database. The token is signed with a secret key, so the
#   server can verify it hasn't been tampered with. The token carries the
#   user's identity (username, role) inside it — no DB lookup needed just
#   to identify who is making a request.
#
# Token structure (base64-encoded JSON):
#   Header:  { "alg": "HS256", "typ": "JWT" }
#   Payload: { "sub": "azam", "role": "user", "exp": 1711000000 }
#   Signature: HMAC-SHA256(header + "." + payload, SECRET_KEY)
# =============================================================================

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from db.database import get_user_by_username
from app.models.user import UserInDB

load_dotenv()

# =============================================================================
# ── Configuration ─────────────────────────────────────────────────────────────
# =============================================================================

# SECRET_KEY is used to sign the JWT. If someone gets this key they can forge
# tokens. ALWAYS set a long, random value in production via environment variable.
# Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
_INSECURE_DEFAULT = "CHANGE_ME_IN_PRODUCTION_use_a_long_random_string"
SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", _INSECURE_DEFAULT)

if SECRET_KEY == _INSECURE_DEFAULT:
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY is not set — using insecure default. "
        "Set JWT_SECRET_KEY in .env or environment. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"",
        stacklevel=1,
    )
    # In production, fail hard instead of warning:
    # raise RuntimeError("JWT_SECRET_KEY must be set in production")

# The signing algorithm. HS256 (HMAC + SHA-256) is the most common choice.
ALGORITHM: str = "HS256"

# How long a token stays valid after it's issued (in minutes).
# After this, the user must log in again to get a fresh token.
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


# =============================================================================
# ── Password Hashing ──────────────────────────────────────────────────────────
# =============================================================================

# CryptContext is a passlib helper that wraps the hashing algorithm.
# bcrypt is the industry standard for password hashing — it's deliberately
# slow (has a work factor) so brute-force attacks are impractical.
# deprecated="auto" means old-format hashes get upgraded automatically.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    Call this when registering a user — store the result, never the plain text.

    Example:
        hash_password("mypassword123")
        → "$2b$12$KIXl1..."  (60-char bcrypt hash)
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check whether a plain-text password matches a stored bcrypt hash.
    Returns True if they match, False otherwise.

    Used during login: fetch user from DB, then call this to check the password.
    Never compare hashes manually — always use this function.
    """
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# ── Pydantic schemas used only for auth responses ────────────────────────────
# =============================================================================

class TokenResponse(BaseModel):
    """What /auth/login returns to the client."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data we decode OUT of a JWT payload."""
    username: Optional[str] = None
    role: Optional[str] = None


# =============================================================================
# ── JWT Creation ──────────────────────────────────────────────────────────────
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT token.

    `data` should contain at least {"sub": username, "role": role}.
    "sub" is the JWT standard claim for "subject" (who the token is about).

    The `exp` (expiry) claim is added here. jose will automatically reject
    tokens where exp is in the past.

    Example usage:
        token = create_access_token({"sub": "azam", "role": "user"})
    """
    to_encode = data.copy()

    # Calculate expiry time in UTC
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    # Encode and sign the payload. The result is a string like:
    # "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhemFtIn0.xxxxx"
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# =============================================================================
# ── JWT Verification ──────────────────────────────────────────────────────────
# =============================================================================

def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.

    Raises HTTP 401 if:
      - The token is malformed
      - The signature doesn't match (tampered token)
      - The token has expired
      - The 'sub' claim is missing

    Returns a TokenData object with username and role on success.
    """
    # This is the exception we'll raise for any auth failure.
    # 401 = Unauthorized. The WWW-Authenticate header tells the client
    # it should provide a Bearer token.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # jose.jwt.decode() verifies the signature AND the expiry claim.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username: str = payload.get("sub")
        role: str     = payload.get("role", "user")

        if username is None:
            raise credentials_exception

        return TokenData(username=username, role=role)

    except JWTError:
        # JWTError covers: expired token, bad signature, malformed token.
        raise credentials_exception


# =============================================================================
# ── OAuth2 Scheme ─────────────────────────────────────────────────────────────
# =============================================================================

# OAuth2PasswordBearer tells FastAPI:
# "The client should send tokens in the Authorization header as:
#  Authorization: Bearer <token>"
#
# tokenUrl="/auth/login" is used by the auto-generated Swagger UI (/docs)
# to show a login form and fill the token automatically — very handy for testing.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =============================================================================
# ── FastAPI Dependencies ──────────────────────────────────────────────────────
# =============================================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> UserInDB:
    """
    FastAPI dependency — inject this into any route that requires authentication.

    How to use it in a route:
        @router.get("/protected")
        def protected_route(current_user: UserInDB = Depends(get_current_user)):
            return {"message": f"Hello, {current_user.username}!"}

    FastAPI calls this function automatically before the route handler runs.
    If it raises an HTTPException, the route is never called.

    Flow:
        1. Extract the Bearer token from the Authorization header.
        2. Decode and verify the JWT (raises 401 if invalid/expired).
        3. Look up the user in the database by username.
        4. Return the User object so the route can use it.
    """
    # Step 1 & 2: validate the token, extract username
    token_data = decode_access_token(token)

    # Step 3: look up the user in the DB
    user_dict = get_user_by_username(token_data.username)

    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User belonging to this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserInDB(**user_dict)


def require_admin(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """
    FastAPI dependency — use this for admin-only routes.
    Raises HTTP 403 Forbidden if the user's role is not 'admin'.

    How to use it in a route:
        @router.delete("/users/{user_id}")
        def delete_user(
            user_id: int,
            admin: UserInDB = Depends(require_admin),
        ):
            ...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires admin privileges.",
        )
    return current_user
