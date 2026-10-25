"""Authentication API routes — login, session verification, and test credential endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ragops.core.auth import (
    DEFAULT_USERS,
    LoginRequest,
    LoginResponse,
    UserProfile,
    create_token,
    get_current_user,
)
from ragops.storage.repositories import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


class TestUserItem(BaseModel):
    username: str
    email: str
    role: str
    default_password: str
    description: str


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Authenticate user with username and password using SHA-256 salted hash verification."""
    repo = UserRepository()
    user = repo.verify_credentials(credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password. Use test credentials: admin/admin123, test1/test123, or test2/test223",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue signed session token valid for 7 days
    token = create_token(user.username, user.role)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=user,
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    user: UserProfile = Depends(get_current_user),
):
    """Get the profile and role of the currently authenticated user."""
    return user


@router.get("/test-users", response_model=list[TestUserItem])
async def list_dummy_credentials():
    """List pre-configured dummy test users for easy UI one-click authentication."""
    descriptions = {
        "admin": "Full system administrator with access to all user analytics, risk logs, and telemetry.",
        "test1": "Standard enterprise employee user account (HR & general documentation queries).",
        "test2": "Standard developer user account (infrastructure, security & cluster queries).",
    }
    return [
        TestUserItem(
            username=u["username"],
            email=u["email"],
            role=u["role"],
            default_password=u["password"],
            description=descriptions.get(u["username"], "Test user account"),
        )
        for u in DEFAULT_USERS
    ]
