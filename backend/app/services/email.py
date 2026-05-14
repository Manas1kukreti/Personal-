from email.message import EmailMessage
import smtplib

from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings


async def send_email(to_email: str | None, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.emails_enabled or not settings.smtp_host or not to_email:
        return

    def _send() -> None:
        message = EmailMessage()
        message["From"] = settings.smtp_from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)

    await run_in_threadpool(_send)


def manager_submission_link(submission_id) -> str:
    settings = get_settings()
    return f"{settings.frontend_base_url.rstrip('/')}/manager?submission_id={submission_id}"
