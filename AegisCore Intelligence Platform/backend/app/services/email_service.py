"""Email service for sending transactional emails including invitations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger("aegiscore.email")


@dataclass
class EmailMessage:
    """Email message data structure."""

    to_email: str
    subject: str
    html_body: str
    text_body: str | None = None
    from_email: str | None = None


class EmailBackend(Protocol):
    """Protocol for email backend implementations."""

    async def send(self, message: EmailMessage) -> bool:
        """Send an email message."""
        ...


class ConsoleEmailBackend:
    """Development backend that logs emails to console instead of sending."""

    async def send(self, message: EmailMessage) -> bool:
        logger.info("=" * 60)
        logger.info("EMAIL WOULD BE SENT:")
        logger.info(f"To: {message.to_email}")
        logger.info(f"Subject: {message.subject}")
        logger.info(f"From: {message.from_email or 'noreply@aegiscore.io'}")
        if message.text_body:
            logger.info(f"Text: {message.text_body[:200]}...")
        if message.html_body:
            logger.info(f"HTML: {message.html_body[:200]}...")
        logger.info("=" * 60)
        return True


class SmtpEmailBackend:
    """Production SMTP email backend."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        from_email: str = "noreply@aegiscore.io",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email

    async def send(self, message: EmailMessage) -> bool:
        """Send email via SMTP."""
        try:
            import aiosmtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = message.from_email or self.from_email
            msg["To"] = message.to_email

            if message.text_body:
                msg.attach(MIMEText(message.text_body, "plain"))
            if message.html_body:
                msg.attach(MIMEText(message.html_body, "html"))

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                start_tls=self.use_tls,
            )
            logger.info(f"Email sent successfully to {message.to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {message.to_email}: {e}")
            return False


class SESEmailBackend:
    """AWS SES email backend for production."""

    def __init__(
        self,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_region: str = "us-east-1",
        from_email: str = "noreply@aegiscore.io",
    ):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.from_email = from_email

    async def send(self, message: EmailMessage) -> bool:
        """Send email via AWS SES."""
        try:
            import aioboto3

            session = aioboto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region,
            )

            async with session.client("ses") as client:
                response = await client.send_email(
                    Source=message.from_email or self.from_email,
                    Destination={"ToAddresses": [message.to_email]},
                    Message={
                        "Subject": {"Data": message.subject},
                        "Body": {
                            "Text": {"Data": message.text_body or ""},
                            "Html": {"Data": message.html_body},
                        },
                    },
                )
                logger.info(f"Email sent via SES to {message.to_email}, MessageId: {response['MessageId']}")
                return True
        except Exception as e:
            logger.error(f"Failed to send SES email to {message.to_email}: {e}")
            return False


class EmailService:
    """Service for sending transactional emails."""

    def __init__(self, backend: EmailBackend | None = None):
        self.backend = backend or self._create_default_backend()

    def _create_default_backend(self) -> EmailBackend:
        """Create default email backend based on settings."""
        settings = get_settings()
        email_provider = getattr(settings, "email_provider", "console")

        if email_provider == "smtp":
            return SmtpEmailBackend(
                host=getattr(settings, "smtp_host", "localhost"),
                port=getattr(settings, "smtp_port", 587),
                username=getattr(settings, "smtp_username", None),
                password=getattr(settings, "smtp_password", None),
                use_tls=getattr(settings, "smtp_use_tls", True),
                from_email=getattr(settings, "from_email", "noreply@aegiscore.io"),
            )
        elif email_provider == "ses":
            return SESEmailBackend(
                aws_access_key_id=getattr(settings, "aws_access_key_id", None),
                aws_secret_access_key=getattr(settings, "aws_secret_access_key", None),
                aws_region=getattr(settings, "aws_region", "us-east-1"),
                from_email=getattr(settings, "from_email", "noreply@aegiscore.io"),
            )
        else:
            return ConsoleEmailBackend()

    async def send_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        company_name: str,
        invitation_token: str,
        accept_url: str,
        expires_in_hours: int = 72,
    ) -> bool:
        """Send user invitation email."""
        subject = f"You've been invited to join {company_name} on AegisCore"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1a365d; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f7fafc; padding: 30px; margin: 20px 0; }}
                .button {{ display: inline-block; background: #3182ce; color: white; padding: 12px 30px;
                         text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #718096; font-size: 12px; margin-top: 30px; }}
                .expiry {{ color: #e53e3e; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>AegisCore Invitation</h1>
                </div>
                <div class="content">
                    <h2>Hello,</h2>
                    <p><strong>{inviter_name}</strong> has invited you to join <strong>{company_name}</strong> on AegisCore.</p>
                    <p>AegisCore is a comprehensive cyber risk intelligence platform that helps organizations
                       identify, prioritize, and remediate security vulnerabilities.</p>
                    <p style="text-align: center;">
                        <a href="{accept_url}?token={invitation_token}" class="button">Accept Invitation</a>
                    </p>
                    <p class="expiry">This invitation expires in {expires_in_hours} hours.</p>
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <code>{accept_url}?token={invitation_token}</code>
                </div>
                <div class="footer">
                    <p>If you did not expect this invitation, you can safely ignore this email.</p>
                    <p>&copy; 2024 AegisCore. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        You've been invited to join {company_name} on AegisCore

        {inviter_name} has invited you to join their organization on AegisCore.

        To accept this invitation, please visit:
        {accept_url}?token={invitation_token}

        This invitation expires in {expires_in_hours} hours.

        If you did not expect this invitation, you can safely ignore this email.
        """

        message = EmailMessage(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

        return await self.backend.send(message)

    async def send_welcome_email(
        self,
        to_email: str,
        full_name: str,
        company_name: str,
        login_url: str,
    ) -> bool:
        """Send welcome email to newly registered users."""
        subject = f"Welcome to AegisCore - {company_name}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1a365d; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f7fafc; padding: 30px; margin: 20px 0; }}
                .button {{ display: inline-block; background: #3182ce; color: white; padding: 12px 30px;
                         text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #718096; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to AegisCore!</h1>
                </div>
                <div class="content">
                    <h2>Hello {full_name},</h2>
                    <p>Your account for <strong>{company_name}</strong> has been successfully created on AegisCore.</p>
                    <p>You can now access your security dashboard and start managing your organization's
                       cyber risk posture.</p>
                    <p style="text-align: center;">
                        <a href="{login_url}" class="button">Log In to AegisCore</a>
                    </p>
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <code>{login_url}</code>
                </div>
                <div class="footer">
                    <p>&copy; 2024 AegisCore. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Welcome to AegisCore!

        Hello {full_name},

        Your account for {company_name} has been successfully created on AegisCore.

        You can now log in at: {login_url}

        Thank you for choosing AegisCore for your security needs.
        """

        message = EmailMessage(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

        return await self.backend.send(message)

    async def send_otp_verification_email(
        self,
        to_email: str,
        otp_code: str,
        expires_in_minutes: int = 10,
    ) -> bool:
        """Send email verification OTP code.
        
        This is the critical missing piece - actually delivering the OTP
        to the user's email address.
        
        Args:
            to_email: Recipient email address
            otp_code: 6-digit OTP code
            expires_in_minutes: How long the code is valid
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        subject = "Your AegisCore Verification Code"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1a365d; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f7fafc; padding: 30px; margin: 20px 0; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #1a365d; 
                           letter-spacing: 8px; text-align: center; padding: 20px;
                           background: white; border-radius: 8px; margin: 20px 0; }}
                .warning {{ color: #e53e3e; font-weight: bold; text-align: center; }}
                .footer {{ text-align: center; color: #718096; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>AegisCore Email Verification</h1>
                </div>
                <div class="content">
                    <h2>Verify Your Email Address</h2>
                    <p>Your verification code is:</p>
                    <div class="otp-code">{otp_code}</div>
                    <p class="warning">This code expires in {expires_in_minutes} minutes.</p>
                    <p>Enter this code in the verification screen to complete your registration.</p>
                    <p>If you did not request this code, please ignore this email or contact support.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 AegisCore. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        AegisCore Email Verification

        Your verification code is: {otp_code}

        This code expires in {expires_in_minutes} minutes.

        Enter this code in the verification screen to complete your registration.

        If you did not request this code, please ignore this email or contact support.
        """

        message = EmailMessage(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

        result = await self.backend.send(message)
        if result:
            logger.info(f"OTP email sent successfully to {to_email}")
        else:
            logger.error(f"Failed to send OTP email to {to_email}")
        return result


# Global instance
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
