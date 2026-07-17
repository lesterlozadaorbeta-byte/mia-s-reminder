"""Reminder endpoint tests."""

import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient


async def _get_auth_token(client: AsyncClient) -> str:
    """Helper to register and get auth token."""
    response = await client.post("/api/v1/auth/register", json={
        "email": f"reminder_test_{datetime.now().timestamp()}@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
    })
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_create_reminder(client: AsyncClient):
    """Test creating a reminder."""
    token = await _get_auth_token(client)
    remind_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    response = await client.post(
        "/api/v1/reminders",
        json={
            "title": "Test Reminder",
            "description": "Don't forget this",
            "remind_at": remind_at,
            "is_persistent": True,
            "persistence_interval_minutes": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Reminder"
    assert data["is_persistent"] is True
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_reminders(client: AsyncClient):
    """Test listing reminders."""
    token = await _get_auth_token(client)
    remind_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    # Create a reminder
    await client.post(
        "/api/v1/reminders",
        json={"title": "List Test", "remind_at": remind_at},
        headers={"Authorization": f"Bearer {token}"},
    )

    # List
    response = await client.get(
        "/api/v1/reminders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_snooze_reminder(client: AsyncClient):
    """Test snoozing a reminder."""
    token = await _get_auth_token(client)
    remind_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    # Create
    create_response = await client.post(
        "/api/v1/reminders",
        json={"title": "Snooze Test", "remind_at": remind_at},
        headers={"Authorization": f"Bearer {token}"},
    )
    reminder_id = create_response.json()["id"]

    # Snooze
    response = await client.post(
        f"/api/v1/reminders/{reminder_id}/snooze",
        json={"snooze_minutes": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "snoozed"
    assert response.json()["snooze_count"] == 1


@pytest.mark.asyncio
async def test_mark_reminder_done(client: AsyncClient):
    """Test marking a reminder as done."""
    token = await _get_auth_token(client)
    remind_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    # Create
    create_response = await client.post(
        "/api/v1/reminders",
        json={"title": "Done Test", "remind_at": remind_at},
        headers={"Authorization": f"Bearer {token}"},
    )
    reminder_id = create_response.json()["id"]

    # Mark done
    response = await client.post(
        f"/api/v1/reminders/{reminder_id}/done",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
