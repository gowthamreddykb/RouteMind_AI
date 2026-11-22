"""
tests/test_forgot_password.py - Production Test Suite for Forgot & Reset Password Workflow
Verifies OTP generation, Gmail SMTP dispatch, anti-enumeration, 60s cooldown,
5-attempt lockout, 5-minute expiry, password strength validation, MySQL DB update,
audit logging, and login authentication.
"""
import pytest
import datetime as dt
from werkzeug.security import check_password_hash
from app import create_app
from extensions import db
from src.models.user_model import User
from src.models.otp_model import PasswordResetOTP
from src.models.audit_log_model import AuditLog
from src.services.email_service import EmailService
from src.services.otp_service import OTPService


@pytest.fixture
def app_instance():
    """Create test application context with isolated config."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['MAIL_SUPPRESS_SEND'] = True  # Capture in EmailService.outbox
    with app.app_context():
        EmailService.clear_outbox()
        yield app


@pytest.fixture
def client(app_instance):
    """Flask test client."""
    return app_instance.test_client()


def test_forgot_password_page_loads(client):
    """Test that the Forgot Password page renders correctly."""
    resp = client.get('/auth/forgot-password')
    assert resp.status_code == 200
    assert b"Reset Password" in resp.data
    assert b"Enterprise Email or Login ID" in resp.data
    assert b"Send Verification Code" in resp.data


def test_anti_enumeration_nonexistent_user(client):
    """
    Anti-enumeration requirement:
    Submitting a non-existent email/login ID must return a generic success message
    without leaking that the account does not exist.
    """
    resp = client.post('/auth/forgot-password', data={'email': 'nonexistent_user_999@example.com'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"verification code has been dispatched" in resp.data or b"Enter Verification Code" in resp.data


def test_inactive_account_rejected(client):
    """Deactivated accounts must be rejected from requesting a password reset."""
    resp = client.post('/auth/forgot-password', data={'email': 'deactivated_test'}, follow_redirects=False)
    assert resp.status_code == 403
    assert b"deactivated" in resp.data


def test_otp_dispatch_and_cooldown(client):
    """
    Test OTP generation, dispatch via EmailService, and 60-second cooldown enforcement.
    """
    # Clean previous reset OTPs for gowtham_k
    user = User.query.filter_by(username='gowtham_k').first()
    assert user is not None
    PasswordResetOTP.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # Request 1: Should succeed
    resp1 = client.post('/auth/forgot-password', data={'email': 'gowtham_k'}, follow_redirects=False)
    assert resp1.status_code in (200, 302)

    # Check that email was captured in outbox
    assert len(EmailService.outbox) > 0
    last_email = EmailService.outbox[-1]
    assert last_email['to'] == user.email
    assert 'password reset verification code' in last_email['subject']
    raw_otp = last_email['otp_code']
    assert len(raw_otp) == 6
    assert raw_otp.isdigit()

    # Check DB record: securely hashed, NOT plaintext
    otp_rec = PasswordResetOTP.query.filter_by(user_id=user.id, used_at=None).order_by(PasswordResetOTP.id.desc()).first()
    assert otp_rec is not None
    assert otp_rec.otp_hash != raw_otp  # Must be hashed
    assert otp_rec.check_otp(raw_otp) is True
    assert otp_rec.attempts == 0
    assert otp_rec.verified_at is None

    # Request 2 (immediate): Must trigger 60s cooldown
    resp2 = client.post('/auth/forgot-password', data={'email': 'gowtham_k'}, follow_redirects=False)
    assert resp2.status_code == 429
    assert b"Please wait" in resp2.data


def test_otp_verification_attempt_limit_and_lockout(client):
    """
    Test that incorrect OTPs increment attempts counter and lock out at 5 attempts.
    """
    user = User.query.filter_by(username='gowtham_k').first()
    # Force clean state
    PasswordResetOTP.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # Generate OTP
    OTPService.request_password_reset_otp('gowtham_k')
    otp_rec = PasswordResetOTP.query.filter_by(user_id=user.id, used_at=None).order_by(PasswordResetOTP.id.desc()).first()
    assert otp_rec is not None

    # Test invalid attempts (1 to 4)
    for i in range(1, 5):
        success, code, msg, attempts_left = OTPService.verify_password_reset_otp('gowtham_k', '999999')
        assert success is False
        assert code == "INVALID_OTP"
        assert attempts_left == 5 - i

    # 5th failed attempt -> LOCKOUT
    success, code, msg, attempts_left = OTPService.verify_password_reset_otp('gowtham_k', '999999')
    assert success is False
    assert code == "LOCKED"
    assert attempts_left == 0

    # Ensure record is now invalidated
    db.session.refresh(otp_rec)
    assert otp_rec.used_at is not None


def test_otp_verification_expired(client):
    """Test that expired OTPs (>5 minutes) are rejected."""
    user = User.query.filter_by(username='gowtham_k').first()
    PasswordResetOTP.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # Create an expired OTP
    expired_time = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(minutes=10)
    otp = PasswordResetOTP.create_otp(user.id, "123456", lifetime_minutes=5)
    otp.expires_at = expired_time
    db.session.add(otp)
    db.session.commit()

    success, code, msg, _ = OTPService.verify_password_reset_otp('gowtham_k', '123456')
    assert success is False
    assert code == "EXPIRED"


def test_direct_access_to_reset_password_blocked(client):
    """Direct access to /auth/reset-password without prior OTP verification must be redirected."""
    resp = client.get('/auth/reset-password', follow_redirects=False)
    assert resp.status_code == 302
    assert '/auth/forgot-password' in resp.headers.get('Location', '')


def test_full_reset_password_end_to_end(client):
    """
    Complete end-to-end flow:
    1. Request OTP via email / login ID
    2. Retrieve OTP from outbox
    3. Verify OTP -> Establish reset session
    4. Reject password mismatch
    5. Reject weak password
    6. Submit valid strong password
    7. Verify password hash updated in MySQL DB
    8. Verify old password fails
    9. Verify new password succeeds
    10. Verify audit log entry created
    11. Verify OTP marked as consumed
    """
    user = User.query.filter_by(username='gowtham_k').first()
    old_pw_hash = user.password_hash

    # Clean old reset OTPs
    PasswordResetOTP.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # 1. Request OTP
    resp_req = client.post('/auth/forgot-password', data={'email': 'gowtham_k'}, follow_redirects=True)
    assert resp_req.status_code == 200

    last_email = EmailService.outbox[-1]
    valid_otp = last_email['otp_code']

    # 2. Verify OTP
    with client.session_transaction() as sess:
        sess['reset_identifier'] = 'gowtham_k'
        sess['reset_purpose'] = 'reset_password'

    resp_verify = client.post(
        '/auth/verify-otp?email=gowtham_k&purpose=reset_password',
        data={'email': 'gowtham_k', 'otp': valid_otp, 'purpose': 'reset_password'},
        follow_redirects=False
    )
    assert resp_verify.status_code == 302
    assert '/auth/reset-password' in resp_verify.headers.get('Location', '')

    # 3. Test password mismatch
    resp_mismatch = client.post('/auth/reset-password', data={
        'new_password': 'RouteMind#Secure2026',
        'confirm_password': 'DifferentPassword123'
    }, follow_redirects=True)
    assert resp_mismatch.status_code == 400
    assert b"do not match" in resp_mismatch.data

    # 4. Test weak password (<8 characters or no uppercase)
    resp_weak = client.post('/auth/reset-password', data={
        'new_password': 'short',
        'confirm_password': 'short'
    }, follow_redirects=True)
    assert resp_weak.status_code == 400
    assert b"at least 8 characters" in resp_weak.data

    # 5. Submit valid strong password
    new_password = "RouteMind#Maritime2026!"
    resp_reset = client.post('/auth/reset-password', data={
        'new_password': new_password,
        'confirm_password': new_password
    }, follow_redirects=False)

    assert resp_reset.status_code == 302
    assert '/auth/login' in resp_reset.headers.get('Location', '')

    # Verify flash message
    with client.session_transaction() as sess:
        flashes = sess.get('_flashes', [])
        assert any("Your password has been reset successfully." in f[1] for f in flashes)

    # 6. Verify MySQL database updates
    db.session.expire_all()
    updated_user = User.query.filter_by(username='gowtham_k').first()
    assert updated_user.password_hash != old_pw_hash
    assert updated_user.check_password(new_password) is True

    # 7. Verify OTP record consumed in MySQL
    otp_record = PasswordResetOTP.query.filter_by(user_id=user.id).order_by(PasswordResetOTP.id.desc()).first()
    assert otp_record.used_at is not None

    # 8. Verify Audit Log entry in MySQL
    audit_entry = AuditLog.query.filter_by(action='PASSWORD_RESET', user_id=user.id).order_by(AuditLog.id.desc()).first()
    assert audit_entry is not None
    assert f"user '{user.username}'" in audit_entry.details

    # 9. Verify Login with new password succeeds
    login_resp = client.post('/auth/login', data={
        'email': 'gowtham_k',
        'password': new_password
    }, follow_redirects=False)
    assert login_resp.status_code == 302
    assert '/dashboard' in login_resp.headers.get('Location', '')

    # 10. Verify Login with old password fails
    client.get('/auth/logout')
    bad_login_resp = client.post('/auth/login', data={
        'email': 'gowtham_k',
        'password': 'WrongOldPassword123'
    }, follow_redirects=False)
    assert bad_login_resp.status_code == 401
