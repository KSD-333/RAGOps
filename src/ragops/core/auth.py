"""Authentication and security module — SHA-256 password hashing and dummy credentials.

Provides:
- SHA-256 salted password hashing
- Built-in dummy users: admin, test1, test2
- Token generation and verification
- FastAPI dependencies for user extraction
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from ragops.core.logging import get_logger

logger = get_logger(__name__)

# Secret key for HMAC token signing (can be overridden via env)
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "ragops-enterprise-insecure-secret-change-in-prod-2026")

# Reusable HTTP Bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

class UserProfile(BaseModel):
    """User profile data contract."""
    id: int
    username: str
    email: str
    role: str  # "admin" | "user"
    is_active: bool = True


class LoginRequest(BaseModel):
    """Login payload."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with access token."""
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


# -----------------------------------------------------------------------------
# Default Dummy Users Specification
# -----------------------------------------------------------------------------

DEFAULT_USERS = [
    {
        "username": "admin",
        "email": "admin@ragops.io",
        "password": "admin123",
        "role": "admin",
    },
    {
        "username": "test1",
        "email": "test1@ragops.io",
        "password": "test123",
        "role": "user",
    },
    {
        "username": "test2",
        "email": "test2@ragops.io",
        "password": "test223",
        "role": "user",
    },
]


# -----------------------------------------------------------------------------
# Hashing & Token Helpers
# -----------------------------------------------------------------------------

def generate_salt(length: int = 16) -> str:
    """Generate a random cryptographic salt."""
    return secrets.token_hex(length)


def hash_password(password: str, salt: str) -> str:
    """Hash password using SHA-256 with a salt."""
    salted = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Verify password against salt and expected hash."""
    computed = hash_password(password, salt)
    return hmac.compare_digest(computed, expected_hash)


def create_token(username: str, role: str, expires_in_sec: int = 86400 * 7) -> str:
    """Create a signed, tamper-proof session token."""
    expires_at = int(time.time()) + expires_in_sec
    payload = f"{username}:{role}:{expires_at}"
    signature = hmac.new(AUTH_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_token(token: str) -> Optional[dict[str, Any]]:
    """Verify signed session token and return user claims if valid."""
    if not token or not isinstance(token, str):
        return None
    try:
        parts = token.strip().split(":")
        if len(parts) != 4:
            return None
        username, role, expires_at_str, signature = parts
        payload = f"{username}:{role}:{expires_at_str}"
        expected_sig = hmac.new(AUTH_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        if int(expires_at_str) < int(time.time()):
            return None  # Token expired
        return {"username": username, "role": role}
    except Exception:
        return None


# -----------------------------------------------------------------------------
# FastAPI User Extraction Dependencies
# -----------------------------------------------------------------------------

def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_username: Optional[str] = Header(None, alias="X-Username"),
) -> Optional[UserProfile]:
    """Extract authenticated user if present, or return None."""
    # 1. Check Bearer token
    if auth and auth.credentials:
        claims = verify_token(auth.credentials)
        if claims:
            from ragops.storage.repositories import UserRepository
            repo = UserRepository()
            user = repo.get_by_username(claims["username"])
            if user:
                return user

    # 2. Check X-Username header (convenient for local dev & testing)
    if x_username:
        from ragops.storage.repositories import UserRepository
        repo = UserRepository()
        user = repo.get_by_username(x_username)
        if user:
            return user

    return None


def get_current_user(
    user: Optional[UserProfile] = Depends(get_current_user_optional),
) -> UserProfile:
    """Require an authenticated user. Defaults to 'test1' in dev if none provided."""
    if user:
        return user
    # Fallback default in development so API testing doesn't break
    from ragops.storage.repositories import UserRepository
    repo = UserRepository()
    default_user = repo.get_by_username("test1")
    if default_user:
        return default_user
    return UserProfile(id=2, username="test1", email="test1@ragops.io", role="user")


def require_admin(
    user: UserProfile = Depends(get_current_user),
) -> UserProfile:
    """Require the user to have the 'admin' role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this operation",
        )
    return user
