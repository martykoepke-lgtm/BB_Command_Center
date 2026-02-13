"""
Auth router — registration, login, current user profile.

Routes:
  POST  /api/auth/register   — Create a new account
  POST  /api/auth/login      — Authenticate and get JWT token
  GET   /api/auth/me         — Get current user profile (requires auth)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserProfile
from app.services.auth import authenticate_user, create_access_token, hash_password
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.
    Returns a JWT token immediately so the user is logged in after registering.
    """
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create user
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        title=payload.title,
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Issue token
    token = create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email/password and receive a JWT token."""
    user = await authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )


@router.get("/me", response_model=UserProfile)
async def get_me(
    user: User = Depends(get_current_user),
):
    """Get the current authenticated user's profile."""
    return UserProfile(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        title=user.title,
        role=user.role,
        avatar_url=user.avatar_url,
        skills=user.skills or [],
        capacity_hours=float(user.capacity_hours or 40),
        is_active=user.is_active,
    )
