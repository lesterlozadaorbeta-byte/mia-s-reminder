"""Authentication endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with duplicate email."""
    user_data = {
        "email": "duplicate@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
    }
    # First registration
    await client.post("/api/v1/auth/register", json=user_data)
    # Duplicate
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login."""
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "testpassword123",
        "full_name": "Login User",
    })

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "testpassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with wrong password."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "noone@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    """Test accessing profile without auth."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No bearer token


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient):
    """Test accessing profile with valid token."""
    # Register and get token
    reg_response = await client.post("/api/v1/auth/register", json={
        "email": "me@example.com",
        "password": "testpassword123",
        "full_name": "Me User",
    })
    token = reg_response.json()["access_token"]

    # Access profile
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["full_name"] == "Me User"
