"""Auth API schemas — login, register, token responses."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """New user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    title: str | None = None
    role: str = "analyst"  # admin, manager, analyst, viewer, sponsor


class LoginRequest(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token returned on successful auth."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserProfile(BaseModel):
    """Current user profile (returned from /users/me)."""
    id: str
    email: str
    full_name: str
    title: str | None
    role: str
    avatar_url: str | None
    skills: list
    capacity_hours: float
    is_active: bool

    model_config = {"from_attributes": True}
