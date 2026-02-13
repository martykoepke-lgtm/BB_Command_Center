"""Auth router tests — register, login, /me."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(anon_client: AsyncClient):
    email = f"new-{uuid.uuid4().hex[:8]}@test.com"
    resp = await anon_client.post("/api/auth/register", json={
        "email": email,
        "password": "securepass123",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_duplicate_email(anon_client: AsyncClient):
    email = f"dup-{uuid.uuid4().hex[:8]}@test.com"
    # First registration
    resp1 = await anon_client.post("/api/auth/register", json={
        "email": email,
        "password": "securepass123",
        "full_name": "User One",
    })
    assert resp1.status_code == 201

    # Duplicate
    resp2 = await anon_client.post("/api/auth/register", json={
        "email": email,
        "password": "securepass123",
        "full_name": "User Two",
    })
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(anon_client: AsyncClient):
    resp = await anon_client.post("/api/auth/register", json={
        "email": "short@test.com",
        "password": "abc",
        "full_name": "User",
    })
    assert resp.status_code == 422  # validation error


@pytest.mark.asyncio
async def test_login_success(anon_client: AsyncClient):
    email = f"login-{uuid.uuid4().hex[:8]}@test.com"
    # Register first
    await anon_client.post("/api/auth/register", json={
        "email": email,
        "password": "securepass123",
        "full_name": "Login User",
    })
    # Login
    resp = await anon_client.post("/api/auth/login", json={
        "email": email,
        "password": "securepass123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(anon_client: AsyncClient):
    email = f"wrongpw-{uuid.uuid4().hex[:8]}@test.com"
    await anon_client.post("/api/auth/register", json={
        "email": email,
        "password": "securepass123",
        "full_name": "Wrong PW User",
    })
    resp = await anon_client.post("/api/auth/login", json={
        "email": email,
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(anon_client: AsyncClient):
    resp = await anon_client.post("/api/auth/login", json={
        "email": "nobody@test.com",
        "password": "securepass123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(anon_client: AsyncClient):
    email = f"me-{uuid.uuid4().hex[:8]}@test.com"
    reg_resp = await anon_client.post("/api/auth/register", json={
        "email": email,
        "password": "securepass123",
        "full_name": "Me User",
    })
    token = reg_resp.json()["access_token"]

    resp = await anon_client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email
    assert data["full_name"] == "Me User"


@pytest.mark.asyncio
async def test_me_no_token(anon_client: AsyncClient):
    resp = await anon_client.get("/api/auth/me")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no token
