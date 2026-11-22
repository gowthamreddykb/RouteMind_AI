"""
tests/test_flow_buttons.py - Full Verification of All Interactive Buttons & Flow Navigation
Verifies every button, link, form submission, and route transition across the entire
Forgot Password -> OTP Verification -> Reset Password -> Login -> Dashboard flow.
"""
import requests
import datetime as dt
from werkzeug.security import generate_password_hash
from app import create_app
from extensions import db
from src.models.user_model import User
from src.models.otp_model import PasswordResetOTP

app = create_app()
app.config['MAIL_SUPPRESS_SEND'] = True
app.config['WTF_CSRF_ENABLED'] = False
base_url = 'http://127.0.0.1:5000'


def test_complete_button_and_link_flow():
    # 1. Reset user state in DB
    with app.app_context():
        u = User.query.filter_by(username='gowtham_k').first()
        assert u is not None
        user_id = u.id
        user_email = u.email
        PasswordResetOTP.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    client = app.test_client()

    # BUTTON 1: 'Forgot Password?' link on /auth/login
    r_login = client.get('/auth/login')
    assert r_login.status_code == 200
    assert '/auth/forgot-password' in r_login.get_data(as_text=True)
    print('Button 1: Forgot Password? link verified.')

    # BUTTON 2: 'Send Verification Code' button on /auth/forgot-password
    r_forgot = client.get('/auth/forgot-password')
    assert r_forgot.status_code == 200
    assert 'Send Verification Code' in r_forgot.get_data(as_text=True)
    print('Button 2: Send Verification Code button verified.')

    # BUTTON 3: 'Back to Sign In' link on /auth/forgot-password
    assert '/auth/login' in r_forgot.get_data(as_text=True)
    print('Button 3: Back to Sign In link verified.')

    # Set up test OTP in DB with created_at in the past so cooldown is satisfied
    known_otp = '456789'
    with app.app_context():
        otp = PasswordResetOTP.create_otp(user_id=user_id, raw_otp=known_otp, lifetime_minutes=5)
        otp.created_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(seconds=65)
        db.session.add(otp)
        db.session.commit()

    # Submit forgot password form
    r_post_forgot = client.post(
        '/auth/forgot-password',
        data={'email': user_email},
        follow_redirects=False
    )
    assert r_post_forgot.status_code in (200, 302)
    print('Form submit: Forgot password request dispatched.')

    # Update OTP hash to ensure exact match with known_otp
    with app.app_context():
        latest = PasswordResetOTP.query.filter_by(user_id=user_id, used_at=None).order_by(PasswordResetOTP.id.desc()).first()
        latest.otp_hash = generate_password_hash(known_otp)
        latest.attempts = 0
        db.session.commit()

    # BUTTON 4 & 5: 'Verify Code' & 'Resend Code' on /auth/verify-otp
    r_verify = client.get(f'/auth/verify-otp?email={user_email}&purpose=reset_password')
    assert r_verify.status_code == 200
    assert 'Verify Code' in r_verify.get_data(as_text=True)
    assert 'Resend Code' in r_verify.get_data(as_text=True)
    assert '/auth/login' in r_verify.get_data(as_text=True)
    print('Buttons 4 & 5: Verify Code & Resend Code verified on verification page.')

    # Verify candidate OTP
    r_post_verify = client.post(
        f'/auth/verify-otp?email={user_email}&purpose=reset_password',
        data={'email': user_email, 'otp': known_otp, 'purpose': 'reset_password'},
        follow_redirects=False
    )
    assert r_post_verify.status_code == 302
    assert '/auth/reset-password' in r_post_verify.headers.get('Location')
    print('Flow transition: /auth/verify-otp -> /auth/reset-password succeeded.')

    # BUTTON 6, 7, 8, 9, 10: Reset Password Page Controls
    r_reset = client.get('/auth/reset-password')
    assert r_reset.status_code == 200
    assert 'Create New Password' in r_reset.get_data(as_text=True)
    assert 'Update Password' in r_reset.get_data(as_text=True)
    assert 'togglePasswordVisibility' in r_reset.get_data(as_text=True)
    assert '/auth/login' in r_reset.get_data(as_text=True)
    print('Buttons 6-10: Reset password form, show/hide eye toggles, submit & cancel buttons verified.')

    # Submit valid new password
    new_password = 'RouteMind#Titan2026!'
    r_post_reset = client.post(
        '/auth/reset-password',
        data={'new_password': new_password, 'confirm_password': new_password},
        follow_redirects=False
    )
    assert r_post_reset.status_code == 302
    assert '/auth/login' in r_post_reset.headers.get('Location')
    print('Password update: Password hash committed to MySQL, redirected to /auth/login.')

    # BUTTON 11: Sign In on /auth/login with new credentials
    r_post_login = client.post(
        '/auth/login',
        data={'email': 'gowtham_k', 'password': new_password},
        follow_redirects=False
    )
    assert r_post_login.status_code == 302
    assert '/dashboard' in r_post_login.headers.get('Location')
    print('Button 11: Sign In succeeds with new credentials -> /dashboard.')


if __name__ == '__main__':
    test_complete_button_and_link_flow()
    print('ALL BUTTONS AND FLOW STEPS PASSED SUCCESSFULLY!')
