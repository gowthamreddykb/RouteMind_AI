import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class EmailOTP(db.Model):
    """
    EmailOTP model for secure, single-use, time-bound email verification codes (2FA / Quick Sign In).
    Stores only salted hashes of OTPs in the database.
    """
    __tablename__ = 'email_otps'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    otp_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc).replace(tzinfo=None), nullable=False)

    user = db.relationship('User', backref=db.backref('otps', cascade='all, delete-orphan', lazy='dynamic'))

    @property
    def is_expired(self) -> bool:
        """Check if OTP has expired (5-minute lifetime)."""
        if self.expires_at is None:
            return True
        if self.expires_at.tzinfo is not None:
            return dt.datetime.now(dt.timezone.utc) > self.expires_at
        return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) > self.expires_at

    def check_otp(self, candidate_otp: str) -> bool:
        """Verify candidate 6-digit OTP against the secure stored hash."""
        if not candidate_otp or not self.otp_hash:
            return False
        return check_password_hash(self.otp_hash, str(candidate_otp).strip())

    @classmethod
    def create_otp(cls, email: str, raw_otp: str, user_id=None, ip_address=None, lifetime_minutes=5):
        """Factory method to construct a hashed OTP record with exact expiry."""
        now = dt.datetime.now(dt.timezone.utc)
        expires_at = now + dt.timedelta(minutes=lifetime_minutes)
        
        return cls(
            user_id=user_id,
            email=email.strip().lower(),
            otp_hash=generate_password_hash(str(raw_otp).strip()),
            expires_at=expires_at.replace(tzinfo=None),
            failed_attempts=0,
            is_used=False,
            ip_address=ip_address,
            created_at=now.replace(tzinfo=None)
        )


class PasswordResetOTP(db.Model):
    """
    PasswordResetOTP model for dedicated password reset OTP lifecycle management.
    Stores only salted hashes of OTPs in the MySQL database.
    Tracks user_id, hashed OTP, 5-minute expiry, attempts, verified_at, and used_at.
    """
    __tablename__ = 'password_reset_otps'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    otp_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc).replace(tzinfo=None), nullable=False)

    user = db.relationship('User', backref=db.backref('password_reset_otps', cascade='all, delete-orphan', lazy='dynamic'))

    @property
    def is_expired(self) -> bool:
        """Check if OTP has expired (5-minute lifetime)."""
        if self.expires_at is None:
            return True
        if self.expires_at.tzinfo is not None:
            return dt.datetime.now(dt.timezone.utc) > self.expires_at
        return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) > self.expires_at

    @property
    def is_consumed(self) -> bool:
        """Check if OTP has already been consumed / used."""
        return self.used_at is not None

    def check_otp(self, candidate_otp: str) -> bool:
        """Verify candidate 6-digit OTP against the secure stored hash."""
        if not candidate_otp or not self.otp_hash:
            return False
        return check_password_hash(self.otp_hash, str(candidate_otp).strip())

    @classmethod
    def create_otp(cls, user_id: int, raw_otp: str, lifetime_minutes: int = 5):
        """Factory method to construct a hashed OTP record for password reset."""
        now = dt.datetime.now(dt.timezone.utc)
        expires_at = now + dt.timedelta(minutes=lifetime_minutes)
        return cls(
            user_id=user_id,
            otp_hash=generate_password_hash(str(raw_otp).strip()),
            expires_at=expires_at.replace(tzinfo=None),
            attempts=0,
            verified_at=None,
            used_at=None,
            created_at=now.replace(tzinfo=None)
        )
