"""
email_service.py - Production SMTP Email Dispatch Service for RouteMind AI
Handles delivery of secure, time-bound one-time passwords (OTP) for user authentication and password reset.
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple, Optional, List, Dict, Any
from flask import current_app

logger = logging.getLogger('routemind.email')


class EmailService:
    """Enterprise SMTP Email Service with HTML templating and test outbox support."""

    # In-memory outbox for testing when MAIL_SUPPRESS_SEND is enabled
    outbox: List[Dict[str, Any]] = []

    @classmethod
    def clear_outbox(cls):
        cls.outbox.clear()

    @staticmethod
    def _build_html_template(otp_code: str, recipient_name: Optional[str] = None, purpose: str = "login") -> str:
        """
        Render a professional RouteMind AI branded HTML email template.
        Includes maritime branding, 6-digit OTP, 5-minute expiry notice, and security advisory.
        """
        salutation = f"Hello {recipient_name}," if recipient_name else "Hello,"
        spaced_otp = " ".join(str(otp_code))

        if purpose == "reset_password":
            action_desc = "You recently submitted a request to reset your password for your RouteMind AI Control Tower account. Please enter the following 6-digit single-use verification code to complete your password reset:"
            badge_title = "Password Reset Code"
            security_warning = (
                "<strong>&#x26A0;&#xFE0F; Security Notice:</strong> "
                "If you did not request a password reset, please disregard this email. "
                "Your account remains secure and no password changes have been applied. "
                "If you suspect unauthorized activity, contact your RouteMind AI administrator immediately."
            )
        else:
            action_desc = "You have requested to sign in to your RouteMind AI Control Tower account. Please enter the following 6-digit single-use verification code to complete your authentication:"
            badge_title = "Your Verification Code"
            security_warning = (
                "<strong>&#x26A0;&#xFE0F; Security Notice:</strong> "
                "If you did not request this login code, someone may be attempting to access your account. "
                "Please ignore this message or report this incident immediately to your security administrator."
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RouteMind AI Security Verification</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 0;
      background-color: #F8FAFC;
      color: #0F172A;
    }}
    .email-container {{
      max-width: 560px;
      margin: 30px auto;
      background-color: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
    }}
    .email-header {{
      background: linear-gradient(135deg, #094044 0%, #0E7490 100%);
      padding: 28px 32px;
      text-align: center;
      color: #FFFFFF;
    }}
    .brand-title {{
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.5px;
      margin: 0;
    }}
    .brand-subtitle {{
      font-size: 13px;
      opacity: 0.85;
      margin-top: 4px;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }}
    .email-body {{
      padding: 32px;
    }}
    .otp-card {{
      background-color: #F0FDFA;
      border: 2px dashed #0D9488;
      border-radius: 12px;
      padding: 24px;
      text-align: center;
      margin: 24px 0;
    }}
    .otp-code {{
      font-size: 34px;
      font-weight: 800;
      letter-spacing: 8px;
      color: #094044;
      font-family: 'Courier New', Courier, monospace;
      margin: 8px 0;
    }}
    .expiry-badge {{
      display: inline-block;
      background-color: #FEF3C7;
      color: #92400E;
      font-size: 12px;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 20px;
      margin-top: 8px;
    }}
    .security-callout {{
      background-color: #FEF2F2;
      border-left: 4px solid #DC2626;
      padding: 14px 18px;
      border-radius: 6px;
      margin-top: 24px;
      font-size: 13px;
      color: #7F1D1D;
      line-height: 1.5;
    }}
    .email-footer {{
      padding: 20px 32px;
      background-color: #F8FAFC;
      border-top: 1px solid #E2E8F0;
      font-size: 12px;
      color: #64748B;
      text-align: center;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="email-header">
      <h1 class="brand-title">RouteMind AI</h1>
      <div class="brand-subtitle">Maritime Logistics Control Tower</div>
    </div>
    
    <div class="email-body">
      <p style="font-size: 15px; margin-top: 0;">{salutation}</p>
      <p style="font-size: 14px; color: #334155; line-height: 1.6;">
        {action_desc}
      </p>

      <div class="otp-card">
        <div style="font-size: 12px; text-transform: uppercase; color: #0E7490; font-weight: 600; letter-spacing: 1px;">{badge_title}</div>
        <div class="otp-code">{spaced_otp}</div>
        <div class="expiry-badge">&#x23F1; Valid for 5 minutes only</div>
      </div>

      <div class="security-callout">
        {security_warning}
      </div>
    </div>

    <div class="email-footer">
      This is an automated security notification from RouteMind AI Maritime Control Tower.<br>
      Please do not reply directly to this email.
    </div>
  </div>
</body>
</html>
"""

    @classmethod
    def send_otp_email(
        cls,
        to_email: str,
        otp_code: str,
        recipient_name: Optional[str] = None,
        purpose: str = "login"
    ) -> Tuple[bool, Optional[str]]:
        """
        Send a 6-digit OTP verification email via SMTP.
        Returns (success: bool, error_message: Optional[str]).
        Security rule: Never logs or exposes the OTP value in application logs.
        """
        to_email = to_email.strip()
        logger.info("Initiating OTP verification email dispatch for recipient: %s (purpose: %s)", to_email, purpose)

        # Retrieve configuration
        config = current_app.config if current_app else {}
        server_host = config.get('MAIL_SERVER', os.environ.get('MAIL_SERVER', 'smtp.gmail.com'))
        port = int(config.get('MAIL_PORT', os.environ.get('MAIL_PORT', 587)))
        use_tls = config.get('MAIL_USE_TLS', os.environ.get('MAIL_USE_TLS', 'true'))
        if isinstance(use_tls, str):
            use_tls = use_tls.lower() in ('true', '1', 't', 'yes')
        else:
            use_tls = bool(use_tls)

        use_ssl = config.get('MAIL_USE_SSL', os.environ.get('MAIL_USE_SSL', 'false'))
        if isinstance(use_ssl, str):
            use_ssl = use_ssl.lower() in ('true', '1', 't', 'yes')
        else:
            use_ssl = bool(use_ssl)

        username = config.get('MAIL_USERNAME', os.environ.get('MAIL_USERNAME'))
        password = config.get('MAIL_PASSWORD', os.environ.get('MAIL_PASSWORD'))
        sender = config.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_DEFAULT_SENDER', 'RouteMind AI <no-reply@routemind.ai>'))

        # Check if email sending is suppressed (e.g. testing)
        suppress_send = config.get('MAIL_SUPPRESS_SEND', os.environ.get('MAIL_SUPPRESS_SEND', 'false'))
        if isinstance(suppress_send, str):
            suppress_send = suppress_send.lower() in ('true', '1', 't', 'yes')

        # Subject line
        if purpose == "reset_password":
            subject = f"{otp_code} is your RouteMind AI password reset verification code"
            plain_text = (
                f"RouteMind AI - Password Reset Verification Code\n\n"
                f"Your 6-digit verification code is: {otp_code}\n"
                f"This code will expire in 5 minutes.\n\n"
                f"If you did not request a password reset, please ignore this email.\n"
            )
        else:
            subject = f"{otp_code} is your RouteMind AI verification code"
            plain_text = (
                f"RouteMind AI - Login Verification Code\n\n"
                f"Your 6-digit verification code is: {otp_code}\n"
                f"This code will expire in 5 minutes.\n\n"
                f"If you did not request this login code, please ignore this email.\n"
            )

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to_email

        html_text = cls._build_html_template(otp_code, recipient_name, purpose=purpose)
        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_text, 'html', 'utf-8'))

        # If testing/suppressed mode: record in outbox and return success
        if suppress_send:
            cls.outbox.append({
                'to': to_email,
                'subject': msg['Subject'],
                'otp_code': otp_code,
                'purpose': purpose,
                'msg': msg
            })
            logger.info("MAIL_SUPPRESS_SEND active: Recorded email in test outbox for %s", to_email)
            return True, None

        # Check credentials for production SMTP
        if not username or not password:
            err_msg = "SMTP credentials (MAIL_USERNAME/MAIL_PASSWORD) not configured in server environment."
            logger.error(err_msg)
            return False, err_msg

        # Connect and deliver via SMTP
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(server_host, port, timeout=12)
            else:
                server = smtplib.SMTP(server_host, port, timeout=12)
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()

            server.login(username, password)
            server.send_message(msg)
            server.quit()

            logger.info("Successfully delivered OTP verification email to: %s", to_email)
            return True, None
        except Exception as e:
            error_details = str(e)
            logger.error("Failed to deliver OTP email to %s: %s", to_email, error_details)
            return False, f"Email delivery failed: {error_details}"
