from email.message import EmailMessage
import logging
import smtplib
from datetime import datetime, timedelta, timezone

import jwt
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

REVIEW_TOKEN_EXPIRE_HOURS = 72


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

    try:
        await run_in_threadpool(_send)
    except Exception:
        logger.exception("Failed to send email notification to %s", to_email)


def generate_review_token(submission_id, manager_id) -> str:
    settings = get_settings()
    payload = {
        "submission_id": str(submission_id),
        "manager_id": str(manager_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=REVIEW_TOKEN_EXPIRE_HOURS),
        "purpose": "review_link",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_review_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        if payload.get("purpose") != "review_link":
            raise ValueError("Invalid token purpose")
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("This review link has expired. Please ask the employee to re-submit or contact your admin.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid review link.")


def manager_submission_link(submission_id, manager_id) -> str:
    settings = get_settings()
    token = generate_review_token(submission_id, manager_id)
    return f"{settings.frontend_base_url.rstrip('/')}/manager?token={token}"