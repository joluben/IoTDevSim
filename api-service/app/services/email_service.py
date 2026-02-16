"""
SMTP email service for onboarding and password reset flows.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

import structlog

from app.core.simple_config import settings

logger = structlog.get_logger()


class EmailService:
    def __init__(self) -> None:
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from = settings.SMTP_FROM
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.smtp_use_ssl = settings.SMTP_USE_SSL
        self.smtp_timeout = settings.SMTP_TIMEOUT_SECONDS
        self.max_retries = settings.SMTP_MAX_RETRIES

    def _is_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_port and self.smtp_from)

    def _build_connection(self):
        if self.smtp_use_ssl:
            context = ssl.create_default_context()
            return smtplib.SMTP_SSL(
                host=self.smtp_host,
                port=self.smtp_port,
                timeout=self.smtp_timeout,
                context=context,
            )

        smtp = smtplib.SMTP(
            host=self.smtp_host,
            port=self.smtp_port,
            timeout=self.smtp_timeout,
        )
        if self.smtp_use_tls:
            context = ssl.create_default_context()
            smtp.starttls(context=context)
        return smtp

    def send_email(self, *, to_email: str, subject: str, text_body: str, html_body: Optional[str] = None) -> None:
        if not self._is_configured():
            raise RuntimeError("SMTP is not configured. Set SMTP_* environment variables.")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.smtp_from
        message["To"] = to_email
        message.set_content(text_body)

        if html_body:
            message.add_alternative(html_body, subtype="html")

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                with self._build_connection() as smtp:
                    if self.smtp_user and self.smtp_password:
                        smtp.login(self.smtp_user, self.smtp_password)
                    smtp.send_message(message)

                logger.info("Email sent", to=to_email, subject=subject, attempt=attempt)
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "Email send attempt failed",
                    to=to_email,
                    subject=subject,
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=str(exc),
                )

        raise RuntimeError(f"Failed to send email after {self.max_retries} attempts: {last_error}")

    def send_welcome_email(self, *, to_email: str, full_name: str, temporary_password: str) -> None:
        subject = "Bienvenido a IoTDevSim"
        text_body = (
            f"Hola {full_name},\n\n"
            "Tu cuenta en IoTDevSim ha sido creada.\n"
            f"Usuario: {to_email}\n"
            f"Contraseña temporal: {temporary_password}\n\n"
            "Te recomendamos cambiar la contraseña en tu perfil después del primer inicio de sesión.\n"
        )

        self.send_email(to_email=to_email, subject=subject, text_body=text_body)

    def send_password_reset_email(self, *, to_email: str, reset_token: str) -> None:
        reset_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={reset_token}"

        subject = "Recuperación de contraseña IoTDevSim"
        text_body = (
            "Se solicitó el restablecimiento de tu contraseña.\n\n"
            f"Usa este enlace para continuar: {reset_url}\n\n"
            "Si no realizaste esta solicitud, ignora este mensaje."
        )

        self.send_email(to_email=to_email, subject=subject, text_body=text_body)


email_service = EmailService()
