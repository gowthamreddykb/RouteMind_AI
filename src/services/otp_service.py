"""
otp_service.py - Production One-Time Password (OTP) Generation & Validation Engine
RouteMind AI Maritime Logistics Control Tower
Handles both Login OTP and dedicated Password Reset OTP lifecycles.
"""
import secrets
import datetime as dt
from typing import Tuple, Optional, Any, Dict
from extensions import db
from src.models.user_model import User
from src.models.otp_model import EmailOTP, PasswordResetOTP
from src.services.email_service import EmailService

# Rate limiting tracking (in-memory IP and account windows)
_RATE_LIMIT_CACHE: Dict[str, list] = {}


class OTPService:
    """Enterprise OTP lifecycle management with cryptographic randomness, salted hashing, and rate limiting."""

    COOLDOWN_SECONDS = 60
    EXPIRY_MINUTES = 5
    MAX_FAILED_ATTEMPTS = 5
    MAX_REQUESTS_PER_WINDOW = 10
    WINDOW_MINUTES = 15

    @classmethod
    def _is_rate_limited(cls, key: str) -> bool:
        """Check if request rate exceeds threshold within rolling window."""
        now = dt.datetime.now(dt.timezone.utc).timestamp()
        cutoff = now - (cls.WINDOW_MINUTES * 60)
        timestamps = [t for t in _RATE_LIMIT_CACHE.get(key, []) if t > cutoff]
        _RATE_LIMIT_CACHE[key] = timestamps
        if len(timestamps) >= cls.MAX_REQUESTS_PER_WINDOW:
            return True
        _RATE_LIMIT_CACHE[key].append(now)
        return False

    # ==========================================
    # LOGIN / 2FA OTP METHODS
    # ==========================================

    @classmethod
    def request_otp(cls, email: str, ip_address: Optional[str] = None) -> Tuple[bool, str, str, Optional[int]]:
        """
        Request a 6-digit OTP for email login.
        Returns: (success: bool, status_code: str, message: str, cooldown_remaining: Optional[int])
        """
        identifier = str(email or '').strip().lower()
        if not identifier:
            return False, "INVALID_EMAIL", "Please enter a valid email address.", None

        # Look up registered user by email or username
        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()

        # Handle deactivated account
        if user and not user.is_active:
            return False, "INACTIVE", "Account is deactivated. Contact Administrator.", None

        email = user.email if user else identifier
        if '@' not in email:
            return False, "INVALID_EMAIL", "Please enter a valid email address.", None

        # Check 60-second resend cooldown against latest OTP record
        latest_otp = EmailOTP.query.filter_by(email=email).order_by(EmailOTP.id.desc()).first()
        if latest_otp and latest_otp.created_at:
            now_utc_naive = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
            created_naive = latest_otp.created_at.replace(tzinfo=None) if latest_otp.created_at.tzinfo else latest_otp.created_at
            elapsed = max(0.0, (now_utc_naive - created_naive).total_seconds())
            if elapsed < cls.COOLDOWN_SECONDS:
                remaining = int(cls.COOLDOWN_SECONDS - elapsed)
                return False, "COOLDOWN", f"Please wait {remaining} seconds before requesting a new code.", remaining

        # Generate a cryptographically secure 6-digit numeric OTP (e.g. 000000 - 999999)
        raw_otp = f"{secrets.randbelow(1000000):06d}"

        # If user is not found, return generic success without generating a DB OTP (anti-enumeration)
        if not user:
            return True, "GENERIC_SENT", "If this email is registered in RouteMind AI, a 6-digit verification code has been dispatched.", cls.COOLDOWN_SECONDS

        # Attempt sending the email first to ensure delivery before saving DB state
        recipient_name = user.full_name or user.username.replace('_', ' ').title()
        sent, err = EmailService.send_otp_email(email, raw_otp, recipient_name=recipient_name, purpose="login")
        if not sent:
            return False, "EMAIL_FAILED", f"Failed to deliver verification code: {err}", None

        # Invalidate any previously unused OTPs for this user / email
        EmailOTP.query.filter_by(email=email, is_used=False).update({'is_used': True})

        # Save new hashed OTP record
        otp_record = EmailOTP.create_otp(
            email=email,
            raw_otp=raw_otp,
            user_id=user.id,
            ip_address=ip_address,
            lifetime_minutes=cls.EXPIRY_MINUTES
        )
        db.session.add(otp_record)
        db.session.commit()

        return True, "SENT", "A 6-digit verification code has been dispatched to your registered email address.", cls.COOLDOWN_SECONDS

    @classmethod
    def verify_otp(cls, email: str, raw_otp: str, ip_address: Optional[str] = None) -> Tuple[bool, str, str, Any]:
        """
        Verify the candidate OTP code for login.
        Returns: (success: bool, status_code: str, message: str, user_or_attempts: Any)
        """
        email = str(email or '').strip().lower()
        candidate = str(raw_otp or '').strip()

        if not email or not candidate:
            return False, "MISSING_DATA", "Both email and verification code are required.", None

        if not candidate.isdigit() or len(candidate) != 6:
            return False, "INVALID_FORMAT", "Verification code must be exactly 6 digits.", None

        # Find latest active OTP record for this email
        otp_record = EmailOTP.query.filter_by(email=email, is_used=False).order_by(EmailOTP.id.desc()).first()

        if not otp_record:
            return False, "NOT_FOUND", "No active verification code found for this email. Please request a new code.", None

        # Check if already expired
        if otp_record.is_expired:
            otp_record.is_used = True
            db.session.commit()
            return False, "EXPIRED", "Verification code has expired. Please request a new code.", None

        # Check if already locked by too many failed attempts
        if otp_record.failed_attempts >= cls.MAX_FAILED_ATTEMPTS:
            otp_record.is_used = True
            db.session.commit()
            return False, "LOCKED", "Maximum verification attempts exceeded. Code has been invalidated. Please request a new code.", None

        # Verify hash match
        if not otp_record.check_otp(candidate):
            otp_record.failed_attempts += 1
            if otp_record.failed_attempts >= cls.MAX_FAILED_ATTEMPTS:
                otp_record.is_used = True
                db.session.commit()
                return False, "LOCKED", "Maximum verification attempts exceeded. Code has been invalidated. Please request a new code.", 0

            db.session.commit()
            remaining = cls.MAX_FAILED_ATTEMPTS - otp_record.failed_attempts
            return False, "INVALID_OTP", f"Invalid verification code. {remaining} attempt(s) remaining.", remaining

        # Valid OTP match: Mark single-use consumption
        otp_record.is_used = True
        db.session.commit()

        # Retrieve user and verify active status
        user = User.query.get(otp_record.user_id) if otp_record.user_id else User.query.filter_by(email=email).first()
        if not user or not user.is_active:
            return False, "INACTIVE", "Account is deactivated. Contact Administrator.", None

        return True, "SUCCESS", f"Welcome back, {user.username.title()}!", user

    # ==========================================
    # PASSWORD RESET OTP METHODS
    # ==========================================

    @classmethod
    def request_password_reset_otp(cls, identifier: str, ip_address: Optional[str] = None) -> Tuple[bool, str, str, Optional[int]]:
        """
        Request a 6-digit OTP specifically for password recovery.
        Accepts registered email or username/login ID.
        Protects against user enumeration.
        Enforces 60-second resend cooldown.
        Delivers via configured Gmail SMTP.
        Returns: (success: bool, status_code: str, message: str, cooldown_remaining: Optional[int])
        """
        raw_id = str(identifier or '').strip().lower()
        if not raw_id:
            return False, "INVALID_INPUT", "Please enter your registered email address or login ID.", None

        # Look up registered user by email or username
        user = User.query.filter((User.email == raw_id) | (User.username == raw_id)).first()

        # Anti-enumeration response message
        generic_msg = "If this account is registered in RouteMind AI, a 6-digit verification code has been dispatched to the registered email."

        # If user does not exist: return generic success without revealing non-existence
        if not user:
            return True, "GENERIC_SENT", generic_msg, cls.COOLDOWN_SECONDS

        # Check account status
        if not user.is_active:
            return False, "INACTIVE", "This account has been deactivated. Please contact your system administrator.", None

        # Check 60-second cooldown on password reset OTPs for this user
        latest_reset = PasswordResetOTP.query.filter_by(user_id=user.id).order_by(PasswordResetOTP.id.desc()).first()
        if latest_reset and latest_reset.created_at:
            now_utc_naive = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
            created_naive = latest_reset.created_at.replace(tzinfo=None) if latest_reset.created_at.tzinfo else latest_reset.created_at
            elapsed = max(0.0, (now_utc_naive - created_naive).total_seconds())
            if elapsed < cls.COOLDOWN_SECONDS:
                remaining = int(cls.COOLDOWN_SECONDS - elapsed)
                return False, "COOLDOWN", f"Please wait {remaining} seconds before requesting a new verification code.", remaining

        # Generate secure random 6-digit numeric OTP
        raw_otp = f"{secrets.randbelow(1000000):06d}"

        # Dispatch OTP to registered user's email via Gmail SMTP
        recipient_name = user.full_name or user.username.replace('_', ' ').title()
        sent, err = EmailService.send_otp_email(
            to_email=user.email,
            otp_code=raw_otp,
            recipient_name=recipient_name,
            purpose="reset_password"
        )

        if not sent:
            # If email delivery fails, do NOT allow password reset
            return False, "EMAIL_FAILED", f"Failed to deliver verification code: {err}. Please try again later.", None

        # Invalidate any prior unused password reset OTPs for this user
        now_naive = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        prior_otps = PasswordResetOTP.query.filter_by(user_id=user.id, used_at=None).all()
        for poto in prior_otps:
            poto.used_at = now_naive

        # Store only the securely hashed OTP in MySQL database
        otp_record = PasswordResetOTP.create_otp(
            user_id=user.id,
            raw_otp=raw_otp,
            lifetime_minutes=cls.EXPIRY_MINUTES
        )
        db.session.add(otp_record)
        db.session.commit()

        return True, "SENT", f"A 6-digit verification code has been dispatched to {user.email}.", cls.COOLDOWN_SECONDS

    @classmethod
    def verify_password_reset_otp(cls, identifier: str, candidate_otp: str) -> Tuple[bool, str, str, Any]:
        """
        Verify the candidate OTP code for password reset.
        Enforces 5-minute expiry, single-use, and max 5 attempts lockout.
        Returns: (success: bool, status_code: str, message: str, user_or_attempts: Any)
        """
        raw_id = str(identifier or '').strip().lower()
        candidate = str(candidate_otp or '').strip()

        if not raw_id or not candidate:
            return False, "MISSING_DATA", "Both account identifier and verification code are required.", None

        if not candidate.isdigit() or len(candidate) != 6:
            return False, "INVALID_FORMAT", "Verification code must be exactly 6 digits.", None

        # Lookup user
        user = User.query.filter((User.email == raw_id) | (User.username == raw_id)).first()
        if not user:
            return False, "NOT_FOUND", "No active verification code found for this account. Please request a new code.", None

        if not user.is_active:
            return False, "INACTIVE", "This account has been deactivated. Please contact your system administrator.", None

        # Find latest unused OTP record for this user
        otp_record = PasswordResetOTP.query.filter_by(
            user_id=user.id,
            used_at=None
        ).order_by(PasswordResetOTP.id.desc()).first()

        if not otp_record:
            return False, "NOT_FOUND", "No active verification code found for this account. Please request a new code.", None

        now_naive = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

        # Check if already expired (5 minutes)
        if otp_record.is_expired:
            otp_record.used_at = now_naive
            db.session.commit()
            return False, "EXPIRED", "Verification code has expired. Please request a new code.", None

        # Check if already locked out
        if otp_record.attempts >= cls.MAX_FAILED_ATTEMPTS:
            otp_record.used_at = now_naive
            db.session.commit()
            return False, "LOCKED", "Maximum verification attempts exceeded. Code has been invalidated. Please request a new code.", None

        # Verify cryptographic hash match
        if not otp_record.check_otp(candidate):
            otp_record.attempts += 1
            if otp_record.attempts >= cls.MAX_FAILED_ATTEMPTS:
                otp_record.used_at = now_naive
                db.session.commit()
                return False, "LOCKED", "Maximum verification attempts exceeded. Code has been invalidated. Please request a new code.", 0

            db.session.commit()
            remaining = cls.MAX_FAILED_ATTEMPTS - otp_record.attempts
            return False, "INVALID_OTP", f"Invalid verification code. {remaining} attempt(s) remaining.", remaining

        # Valid OTP match: Record verification timestamp
        otp_record.verified_at = now_naive
        db.session.commit()

        return True, "SUCCESS", "Identity verified successfully.", user
