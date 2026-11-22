"""
test_email_otp_auth.py - Comprehensive Unit & Integration Test Suite for Email OTP Authentication
Validates all 13 test scenarios specified in Section 8 of the requirements.
"""
import pytest
import datetime as dt
from unittest.mock import patch
from flask_login import current_user

from app import create_app
from extensions import db
from src.models.user_model import User
from src.models.otp_model import EmailOTP
from src.services.email_service import EmailService
from src.services.otp_service import OTPService


@pytest.fixture
def app():
    app = create_app('development')
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['MAIL_SUPPRESS_SEND'] = True
    app.config['LOGIN_DISABLED'] = False  # Enable Flask-Login enforcement for auth tests

    with app.app_context():
        # Clean OTP table and outbox before test run
        EmailOTP.query.delete()
        db.session.commit()
        EmailService.clear_outbox()

    yield app

    with app.app_context():
        EmailOTP.query.delete()
        db.session.commit()
        EmailService.clear_outbox()


@pytest.fixture
def client(app):
    return app.test_client()


def test_1_valid_registered_email_requests_otp(client, app):
    """Scenario 1: Valid registered email receives 6-digit OTP in outbox."""
    with app.app_context():
        EmailService.clear_outbox()

    res = client.post('/auth/request-otp', json={'email': 'dispatcher@routemind.ai'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'email' in data and data['email'] == 'dispatcher@routemind.ai'

    with app.app_context():
        assert len(EmailService.outbox) == 1
        msg = EmailService.outbox[0]
        assert msg['to'] == 'dispatcher@routemind.ai'
        assert len(msg['otp_code']) == 6 and msg['otp_code'].isdigit()

        # Verify DB record is hashed (never raw OTP)
        otp_rec = EmailOTP.query.filter_by(email='dispatcher@routemind.ai', is_used=False).first()
        assert otp_rec is not None
        assert otp_rec.otp_hash != msg['otp_code']
        assert otp_rec.check_otp(msg['otp_code']) is True


def test_2_unknown_email_generic_response(client, app):
    """Scenario 2: Unknown email returns generic response without creating DB OTP or leaking account nonexistence."""
    with app.app_context():
        EmailService.clear_outbox()

    res = client.post('/auth/request-otp', json={'email': 'nonexistent_user@outside.com'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'If this email is registered' in data['message']

    with app.app_context():
        # Anti-enumeration: No email dispatched, no DB record
        assert len(EmailService.outbox) == 0
        assert EmailOTP.query.filter_by(email='nonexistent_user@outside.com').count() == 0


def test_3_correct_otp_login_flow(client, app):
    """Scenario 3: Entering correct OTP creates session and redirects to dashboard."""
    with app.app_context():
        EmailService.clear_outbox()

    # Request code
    client.post('/auth/request-otp', json={'email': 'dispatcher@routemind.ai'})
    with app.app_context():
        raw_code = EmailService.outbox[-1]['otp_code']

    # Verify code
    res = client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': raw_code})
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['user']['role'] == 'Dispatcher'

    # Verify authenticated access to protected dashboard
    dash_res = client.get('/dashboard')
    assert dash_res.status_code == 200
    assert b"Control Tower" in dash_res.data


def test_4_incorrect_otp_rejection(client, app):
    """Scenario 4: Incorrect OTP returns 401 with remaining attempt counter."""
    with app.app_context():
        EmailService.clear_outbox()

    client.post('/auth/request-otp', json={'email': 'dispatcher@routemind.ai'})

    res = client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': '000000'})
    assert res.status_code == 401
    data = res.get_json()
    assert data['code'] == 'INVALID_OTP'
    assert data['remaining_attempts'] == 4

    # Direct access still blocked
    dash_res = client.get('/dashboard')
    assert dash_res.status_code == 302


def test_5_expired_otp_rejection(client, app):
    """Scenario 5: Expired OTP is rejected with 400 EXPIRED."""
    with app.app_context():
        EmailService.clear_outbox()
        # Seed an expired OTP directly (using UTC to align with DB timestamp storage)
        past = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(minutes=10)
        u = User.query.filter_by(email='dispatcher@routemind.ai').first()
        expired_otp = EmailOTP.create_otp('dispatcher@routemind.ai', '123456', user_id=u.id)
        expired_otp.expires_at = past
        db.session.add(expired_otp)
        db.session.commit()

    res = client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': '123456'})
    assert res.status_code == 400
    data = res.get_json()
    assert data['code'] == 'EXPIRED'


def test_6_reused_otp_rejection(client, app):
    """Scenario 6: Single-use OTP cannot be reused after verification."""
    with app.app_context():
        EmailService.clear_outbox()

    client.post('/auth/request-otp', json={'email': 'dispatcher@routemind.ai'})
    with app.app_context():
        raw_code = EmailService.outbox[-1]['otp_code']

    # First verification succeeds
    res1 = client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': raw_code})
    assert res1.status_code == 200

    # Logout
    client.get('/auth/logout')

    # Second attempt with same code fails
    res2 = client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': raw_code})
    assert res2.status_code == 400
    assert res2.get_json()['code'] in ('NOT_FOUND', 'EXPIRED')


def test_7_five_failed_attempts_locks_otp(client, app):
    """Scenario 7: Five failed attempts invalidates the OTP."""
    with app.app_context():
        EmailService.clear_outbox()

    client.post('/auth/request-otp', json={'email': 'dispatcher@routemind.ai'})
    with app.app_context():
        correct_code = EmailService.outbox[-1]['otp_code']

    # 4 incorrect attempts
    for i in range(1, 5):
        r = client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': f'11111{i}'})
        assert r.status_code == 401
        assert r.get_json()['remaining_attempts'] == 5 - i

    # 5th incorrect attempt locks the code
    r5 = client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': '999999'})
    assert r5.status_code == 429
    assert r5.get_json()['code'] == 'LOCKED'

    # Now even the correct code must be rejected
    r_corr = client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': correct_code})
    assert r_corr.status_code in (400, 429)


def test_8_resend_cooldown_60_seconds(client, app):
    """Scenario 8: Resend cooldown rejects requests within 60 seconds with remaining seconds."""
    with app.app_context():
        EmailService.clear_outbox()

    r1 = client.post('/auth/request-otp', json={'email': 'dispatcher@routemind.ai'})
    assert r1.status_code == 200

    # Immediate second request
    r2 = client.post('/auth/request-otp', json={'email': 'dispatcher@routemind.ai'})
    assert r2.status_code == 429
    data = r2.get_json()
    assert data['code'] == 'COOLDOWN'
    assert 0 < data['remaining_seconds'] <= 60


def test_9_email_delivery_failure_handling(client, app):
    """Scenario 9: Email delivery failure returns 500 without creating active session or usable OTP."""
    with app.app_context():
        EmailService.clear_outbox()

    with patch.object(EmailService, 'send_otp_email', return_value=(False, "SMTP server unreachable")):
        res = client.post('/auth/request-otp', json={'email': 'dispatcher@routemind.ai'})
        assert res.status_code == 500
        assert 'Failed to deliver' in res.get_json()['message']

    # Attempting to login without valid OTP fails
    v_res = client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': '123456'})
    assert v_res.status_code in (400, 401)


def test_10_inactive_account_blocked(client, app):
    """Scenario 10: Inactive / deactivated accounts receive 403."""
    res = client.post('/auth/request-otp', json={'email': 'deactivated@routemind.internal'})
    assert res.status_code == 403
    assert 'deactivated' in res.get_json()['message'].lower()


def test_11_role_based_dashboard_redirection(client, app):
    """Scenario 11: Users log in with role and are gated by backend permissions."""
    with app.app_context():
        EmailService.clear_outbox()

    # Login as Dispatcher
    client.post('/auth/request-otp', json={'email': 'dispatcher@routemind.ai'})
    with app.app_context():
        code = EmailService.outbox[-1]['otp_code']
    client.post('/auth/verify-otp', json={'email': 'dispatcher@routemind.ai', 'otp': code})

    # Dispatcher can see shipments, cannot access admin settings
    assert client.get('/shipments/').status_code == 200
    assert client.get('/admin/settings').status_code == 403

    client.get('/auth/logout')


def test_12_direct_access_to_protected_routes_before_login(client):
    """Scenario 12: Direct access before login redirects to /auth/login for HTML or 401 for JSON."""
    r_html = client.get('/dashboard')
    assert r_html.status_code == 302
    assert '/auth/login' in r_html.location

    r_api = client.get('/api/models', headers={'Accept': 'application/json'})
    assert r_api.status_code == 401


def test_13_logout_and_session_invalidation(client, app):
    """Scenario 13: Logout invalidates session immediately."""
    with app.app_context():
        EmailService.clear_outbox()

    client.post('/auth/request-otp', json={'email': 'admin@routemind.ai'})
    with app.app_context():
        code = EmailService.outbox[-1]['otp_code']
    client.post('/auth/verify-otp', json={'email': 'admin@routemind.ai', 'otp': code})

    # In session
    assert client.get('/admin/settings').status_code == 200

    # Logout
    logout_res = client.get('/auth/logout')
    assert logout_res.status_code == 302

    # Subsequent access is redirected
    assert client.get('/admin/settings').status_code == 302
