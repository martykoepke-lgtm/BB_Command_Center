"""
Email notification service — async SMTP dispatch with HTML templates.

Nexus Phase 5: Sends workflow notifications for phase advances,
action assignments, and initiative completions.

Graceful degradation: if email is disabled or SMTP fails, warnings
are logged but the calling operation is never blocked.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTML email template base
# ---------------------------------------------------------------------------

_EMAIL_STYLE = """
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
  .container { max-width: 600px; margin: 20px auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  .header { background: #16213e; color: white; padding: 20px 30px; }
  .header h1 { margin: 0; font-size: 20px; font-weight: 600; }
  .content { padding: 30px; color: #333; line-height: 1.6; }
  .content h2 { color: #0f3460; margin-top: 0; }
  .badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 600; }
  .badge-phase { background: #cce5ff; color: #004085; }
  .badge-action { background: #fff3cd; color: #856404; }
  .badge-complete { background: #d4edda; color: #155724; }
  .btn { display: inline-block; padding: 10px 24px; background: #0f3460; color: white; text-decoration: none; border-radius: 6px; margin-top: 16px; }
  .footer { padding: 16px 30px; background: #f8f9fa; color: #999; font-size: 12px; border-top: 1px solid #eee; }
</style>
"""


def _wrap_email(subject: str, body_html: str) -> str:
    """Wrap email body in the standard template."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{_EMAIL_STYLE}</head>
<body>
<div class="container">
  <div class="header"><h1>BB Enabled Command</h1></div>
  <div class="content">{body_html}</div>
  <div class="footer">
    This is an automated notification from BB Enabled Command.<br>
    Do not reply to this email.
  </div>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Email Service
# ---------------------------------------------------------------------------

class EmailService:
    """Async email dispatch with HTML templates."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_address: str,
        from_name: str,
        app_base_url: str,
        enabled: bool = False,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from_address = from_address
        self._from_name = from_name
        self._app_base_url = app_base_url.rstrip("/")
        self._enabled = enabled

    async def _send(self, to: str, subject: str, html_body: str) -> None:
        """Send an email via SMTP in a background thread."""
        if not self._enabled:
            logger.debug("Email disabled — skipping: %s to %s", subject, to)
            return

        def _smtp_send():
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self._from_name} <{self._from_address}>"
            msg["To"] = to
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self._host, self._port) as server:
                server.ehlo()
                if self._port != 25:
                    server.starttls()
                    server.ehlo()
                if self._user and self._password:
                    server.login(self._user, self._password)
                server.sendmail(self._from_address, [to], msg.as_string())

        try:
            await asyncio.to_thread(_smtp_send)
            logger.info("Email sent: '%s' to %s", subject, to)
        except Exception:
            logger.exception("Failed to send email: '%s' to %s", subject, to)

    # -------------------------------------------------------------------
    # Template methods
    # -------------------------------------------------------------------

    async def send_phase_advance(
        self,
        recipient_email: str,
        initiative_title: str,
        initiative_id: str,
        completed_phase: str,
        next_phase: str,
    ) -> None:
        """Notify about a phase advancing to the next stage."""
        link = f"{self._app_base_url}/initiatives/{initiative_id}"
        body = f"""
        <h2>Phase Advanced</h2>
        <p>The <span class="badge badge-phase">{completed_phase.title()}</span> phase
        of <strong>{initiative_title}</strong> has been completed.</p>
        <p>The project is now in the <strong>{next_phase.title()}</strong> phase.</p>
        <a href="{link}" class="btn">View Initiative</a>
        """
        await self._send(
            recipient_email,
            f"Phase Advanced: {initiative_title} → {next_phase.title()}",
            _wrap_email("Phase Advanced", body),
        )

    async def send_action_assigned(
        self,
        recipient_email: str,
        action_title: str,
        due_date: date | None,
        initiative_title: str,
        initiative_id: str | None = None,
    ) -> None:
        """Notify about a new action item assignment."""
        due_str = due_date.strftime("%B %d, %Y") if due_date else "No due date"
        link = f"{self._app_base_url}/initiatives/{initiative_id}" if initiative_id else self._app_base_url
        body = f"""
        <h2>New Action Item Assigned</h2>
        <p>You've been assigned a new action item:</p>
        <p><span class="badge badge-action">{action_title}</span></p>
        <p><strong>Initiative:</strong> {initiative_title}<br>
        <strong>Due:</strong> {due_str}</p>
        <a href="{link}" class="btn">View Details</a>
        """
        await self._send(
            recipient_email,
            f"Action Assigned: {action_title}",
            _wrap_email("Action Assigned", body),
        )

    async def send_initiative_completed(
        self,
        recipient_email: str,
        initiative_title: str,
        initiative_id: str,
        actual_savings: float | None = None,
    ) -> None:
        """Notify about initiative completion."""
        link = f"{self._app_base_url}/initiatives/{initiative_id}"
        savings_html = ""
        if actual_savings is not None:
            savings_html = f"<p><strong>Actual Savings:</strong> ${actual_savings:,.0f}</p>"
        body = f"""
        <h2>Initiative Completed</h2>
        <p><span class="badge badge-complete">{initiative_title}</span> has been
        successfully completed!</p>
        {savings_html}
        <p>A closeout report has been automatically generated.</p>
        <a href="{link}" class="btn">View Initiative</a>
        """
        await self._send(
            recipient_email,
            f"Completed: {initiative_title}",
            _wrap_email("Initiative Completed", body),
        )


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_email_service: EmailService | None = None


def init_email_service(settings) -> EmailService:
    """Create and store the global email service singleton."""
    global _email_service
    _email_service = EmailService(
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.smtp_user,
        password=settings.smtp_password,
        from_address=settings.smtp_from_address,
        from_name=settings.smtp_from_name,
        app_base_url=settings.app_base_url,
        enabled=settings.email_enabled,
    )
    return _email_service


def get_email_service() -> EmailService:
    """FastAPI dependency: returns the global email service."""
    if _email_service is None:
        raise RuntimeError("EmailService not initialized — app not started")
    return _email_service
