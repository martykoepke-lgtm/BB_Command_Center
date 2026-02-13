"""Tests for the email notification service."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email_service import EmailService


@pytest.fixture
def email_service() -> EmailService:
    """Email service with email enabled."""
    return EmailService(
        host="smtp.test.com",
        port=587,
        user="user@test.com",
        password="secret",
        from_address="noreply@test.com",
        from_name="Test App",
        app_base_url="http://localhost:5173",
        enabled=True,
    )


@pytest.fixture
def disabled_service() -> EmailService:
    """Email service with email disabled."""
    return EmailService(
        host="",
        port=587,
        user="",
        password="",
        from_address="noreply@test.com",
        from_name="Test App",
        app_base_url="http://localhost:5173",
        enabled=False,
    )


# -------------------------------------------------------------------
# Template methods
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_phase_advance(email_service: EmailService):
    """Phase advance email has correct subject and recipient."""
    with patch.object(email_service, "_send", new_callable=AsyncMock) as mock_send:
        await email_service.send_phase_advance(
            recipient_email="analyst@test.com",
            initiative_title="Reduce Wait Times",
            initiative_id="abc-123",
            completed_phase="define",
            next_phase="measure",
        )

        mock_send.assert_called_once()
        args = mock_send.call_args
        assert args[0][0] == "analyst@test.com"
        assert "Reduce Wait Times" in args[0][1]
        assert "Measure" in args[0][1]


@pytest.mark.asyncio
async def test_send_action_assigned(email_service: EmailService):
    """Action assigned email includes due date and initiative link."""
    with patch.object(email_service, "_send", new_callable=AsyncMock) as mock_send:
        await email_service.send_action_assigned(
            recipient_email="user@test.com",
            action_title="Update process map",
            due_date=date(2026, 3, 15),
            initiative_title="Lean Project",
            initiative_id="init-456",
        )

        mock_send.assert_called_once()
        args = mock_send.call_args
        assert args[0][0] == "user@test.com"
        assert "Update process map" in args[0][1]
        # HTML body should contain due date and initiative link
        html = args[0][2]
        assert "March 15, 2026" in html
        assert "init-456" in html


@pytest.mark.asyncio
async def test_send_initiative_completed(email_service: EmailService):
    """Initiative completion email includes savings if provided."""
    with patch.object(email_service, "_send", new_callable=AsyncMock) as mock_send:
        await email_service.send_initiative_completed(
            recipient_email="lead@test.com",
            initiative_title="Cost Reduction",
            initiative_id="init-789",
            actual_savings=50000.0,
        )

        mock_send.assert_called_once()
        html = mock_send.call_args[0][2]
        assert "$50,000" in html
        assert "Cost Reduction" in html


# -------------------------------------------------------------------
# Disabled / graceful degradation
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_disabled(disabled_service: EmailService):
    """No SMTP call when email_enabled=False."""
    with patch("smtplib.SMTP") as mock_smtp:
        await disabled_service.send_phase_advance(
            recipient_email="test@test.com",
            initiative_title="Test",
            initiative_id="id",
            completed_phase="define",
            next_phase="measure",
        )

        mock_smtp.assert_not_called()


@pytest.mark.asyncio
async def test_smtp_failure_graceful(email_service: EmailService):
    """SMTP connection error is logged but does not raise."""
    with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("Connection refused")):
        # Should NOT raise
        await email_service._send(
            to="test@test.com",
            subject="Test Subject",
            html_body="<p>Test</p>",
        )


# -------------------------------------------------------------------
# HTML content
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_html_content(email_service: EmailService):
    """Templates contain expected HTML elements."""
    with patch.object(email_service, "_send", new_callable=AsyncMock) as mock_send:
        await email_service.send_phase_advance(
            recipient_email="analyst@test.com",
            initiative_title="Test Initiative",
            initiative_id="abc",
            completed_phase="define",
            next_phase="measure",
        )

        html = mock_send.call_args[0][2]
        assert "BB Enabled Command" in html
        assert "Phase Advanced" in html
        assert "View Initiative" in html
        assert "http://localhost:5173/initiatives/abc" in html
