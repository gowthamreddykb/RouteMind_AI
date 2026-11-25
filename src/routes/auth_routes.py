"""
auth_routes.py - RouteMind AI Authentication Blueprint
Implements Email OTP-Based Authentication, Forgot Password, Reset Password, and Session Management.
"""
import secrets
import datetime as dt
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, current_user
from extensions import db
from src.models.user_model import User
from src.models.otp_model import PasswordResetOTP
from src.services.otp_service import OTPService
from src.services.audit_service import AuditService
from src.security.permissions import normalize_role
from typing import Tuple

auth_bp = Blueprint('auth_bp', __name__)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate enterprise password complexity requirements."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not any(c.isdigit() or not c.isalnum() for c in password):
        return False, "Password must contain at least one number (0-9) or special symbol."
    return True, ""


# Import Tuple type annotation
from typing import Tuple


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login view:
    - GET: Renders login screen with Email & Password.
    - POST:
        * If 'password' is provided: Authenticates using registered email/username and password.
        * If 'password' is not provided: Dispatches a 6-digit OTP to the registered email address.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        email = (data.get('email') or data.get('username') or '').strip().lower()
        password = data.get('password')
        ip = request.remote_addr

        # 1. Direct Email & Password Authentication
        if password is not None and str(password).strip():
            user = User.query.filter((User.email == email) | (User.username == email)).first()
            if not user or not user.check_password(str(password).strip()):
                msg = "Invalid email or password. Please verify your credentials."
                if request.is_json:
                    return jsonify({'status': 'error', 'code': 'INVALID_CREDENTIALS', 'message': msg}), 401
                flash(msg, 'danger')
                return render_template('login.html', hide_nav=True, email=email), 401

            if not user.is_active:
                msg = "This account has been deactivated. Please contact an administrator."
                if request.is_json:
                    return jsonify({'status': 'error', 'code': 'INACTIVE', 'message': msg}), 403
                flash(msg, 'danger')
                return render_template('login.html', hide_nav=True, email=email), 403

            remember = bool(data.get('remember', False))
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.full_name or user.username}!", "success")
            next_page = request.args.get('next', '')
            if request.is_json:
                return jsonify({
                    'status': 'success',
                    'message': 'Login successful',
                    'redirect': next_page or url_for('dashboard')
                }), 200
            return redirect(next_page or url_for('dashboard'))

        # 2. Fallback: Request OTP generation and email dispatch (if password omitted)
        success, code, msg, cooldown = OTPService.request_otp(email, ip_address=ip)

        if not success:
            status_code = 403 if code == "INACTIVE" else (429 if code in ("COOLDOWN", "RATE_LIMITED") else (500 if code == "EMAIL_FAILED" else 400))
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'code': code,
                    'message': msg,
                    'remaining_seconds': cooldown
                }), status_code

            flash(msg, 'danger' if status_code >= 500 else 'warning')
            return render_template('login.html', hide_nav=True, email=email), status_code

        # OTP successfully generated and dispatched (or generic anti-enumeration success)
        next_page = request.args.get('next', '')
        verify_url = url_for('auth_bp.verify_otp', email=email, next=next_page)

        if request.is_json:
            return jsonify({
                'status': 'success',
                'code': code,
                'message': msg,
                'email': email,
                'cooldown_seconds': cooldown or 60,
                'redirect': verify_url
            }), 200

        flash(msg, 'info')
        return redirect(verify_url)

    return render_template('login.html', hide_nav=True)


@auth_bp.route('/request-otp', methods=['POST'])
def request_otp():
    """Explicit API endpoint for requesting an OTP code."""
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip().lower()
    ip = request.remote_addr

    success, code, msg, cooldown = OTPService.request_otp(email, ip_address=ip)
    if not success:
        status_code = 403 if code == "INACTIVE" else (429 if code in ("COOLDOWN", "RATE_LIMITED") else (500 if code == "EMAIL_FAILED" else 400))
        return jsonify({
            'status': 'error',
            'code': code,
            'message': msg,
            'remaining_seconds': cooldown
        }), status_code

    verify_url = url_for('auth_bp.verify_otp', email=email)
    return jsonify({
        'status': 'success',
        'code': code,
        'message': msg,
        'email': email,
        'cooldown_seconds': cooldown or 60,
        'redirect': verify_url
    }), 200


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """
    OTP Verification view:
    - GET: Renders the 6-digit OTP entry screen with countdown timer.
    - POST: Validates the OTP.
        * If purpose is reset_password: validates via PasswordResetOTP and redirects to /auth/reset-password.
        * If purpose is login: establishes an authenticated Flask-Login session.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    email = request.args.get('email') or request.args.get('identifier') or session.get('reset_identifier', '')
    email = str(email or '').strip().lower()
    purpose = request.args.get('purpose') or session.get('reset_purpose', '')

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        ident = (data.get('email') or data.get('identifier') or email).strip().lower()
        otp = (data.get('otp') or '').strip()
        purpose = (data.get('purpose') or purpose or session.get('reset_purpose', '')).strip()
        ip = request.remote_addr

        # Handle Password Reset OTP Verification
        if purpose == 'reset_password':
            success, code, msg, result = OTPService.verify_password_reset_otp(ident, otp)

            if not success:
                status_code = 403 if code == "INACTIVE" else (429 if code == "LOCKED" else (401 if code == "INVALID_OTP" else 400))
                if request.is_json:
                    return jsonify({
                        'status': 'error',
                        'code': code,
                        'message': msg,
                        'remaining_attempts': result if isinstance(result, int) else None
                    }), status_code

                flash(msg, 'danger')
                return render_template('verify_otp.html', hide_nav=True, email=ident, purpose=purpose), status_code

            user = result
            # Generate one-time cryptographic reset token
            reset_token = secrets.token_urlsafe(32)
            session['reset_token'] = reset_token
            session['reset_user_id'] = user.id
            session['reset_email'] = user.email
            session['reset_purpose'] = 'reset_password'

            flash('Identity verified successfully! Please enter your new password.', 'success')
            reset_url = url_for('auth_bp.reset_password')
            if request.is_json:
                return jsonify({
                    'status': 'success',
                    'message': 'Code verified. Proceed to reset password.',
                    'redirect': reset_url
                }), 200
            return redirect(reset_url)

        # Handle Login / 2FA Verification
        success, code, msg, result = OTPService.verify_otp(ident, otp, ip_address=ip)

        if not success:
            status_code = 403 if code == "INACTIVE" else (429 if code == "LOCKED" else (401 if code == "INVALID_OTP" else 400))
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'code': code,
                    'message': msg,
                    'remaining_attempts': result if isinstance(result, int) else None
                }), status_code

            flash(msg, 'danger')
            return render_template('verify_otp.html', hide_nav=True, email=ident, purpose=purpose), status_code

        user = result
        login_user(user, remember=True)

        next_page = request.args.get('next') or data.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard')

        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': msg,
                'user': user.to_dict(),
                'redirect': next_page
            }), 200

        flash(f'Welcome back, {user.username.title()}! Successfully authenticated.', 'success')
        return redirect(next_page)

    if not email:
        flash('Please enter your email or Login ID to request a verification code.', 'warning')
        return redirect(url_for('auth_bp.login'))

    return render_template('verify_otp.html', hide_nav=True, email=email, purpose=purpose)


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """API endpoint to resend OTP code honoring the 60-second cooldown."""
    data = request.get_json(silent=True) or request.form
    ident = (data.get('email') or data.get('identifier') or session.get('reset_identifier', '')).strip().lower()
    purpose = (data.get('purpose') or session.get('reset_purpose', '')).strip()
    ip = request.remote_addr

    if purpose == 'reset_password':
        success, code, msg, cooldown = OTPService.request_password_reset_otp(ident, ip_address=ip)
    else:
        success, code, msg, cooldown = OTPService.request_otp(ident, ip_address=ip)

    if not success:
        status_code = 403 if code == "INACTIVE" else (429 if code in ("COOLDOWN", "RATE_LIMITED") else (500 if code == "EMAIL_FAILED" else 400))
        return jsonify({
            'status': 'error',
            'code': code,
            'message': msg,
            'remaining_seconds': cooldown
        }), status_code

    return jsonify({
        'status': 'success',
        'code': code,
        'message': msg,
        'email': ident,
        'cooldown_seconds': cooldown or 60
    }), 200


@auth_bp.route('/quick-login/<role>')
def quick_login(role):
    """Development quick login for rapid testing across roles."""
    user = User.query.filter_by(username=role).first()
    if not user:
        norm_role = normalize_role(role)
        user = User.query.filter_by(role=norm_role).first()
        
    if user and not user.is_active:
        flash('Account is inactive. Please contact system administrator.', 'danger')
        return redirect(url_for('auth_bp.login'))

    if not user:
        user = User.query.filter_by(is_active=True).first()

    if user and user.is_active:
        login_user(user, remember=True)
        flash(f'Signed in as {user.username.title()} ({user.role})', 'info')
        return redirect(url_for('dashboard'))

    flash('Account is inactive. Please contact system administrator.', 'danger')
    return redirect(url_for('auth_bp.login'))


@auth_bp.route('/logout')
def logout():
    """Logout endpoint terminating the session."""
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('auth_bp.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password recovery request with email OTP verification."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        identifier = (data.get('email') or data.get('username') or data.get('identifier') or '').strip().lower()
        ip = request.remote_addr

        if not identifier:
            flash('Please enter your registered enterprise email address or Login ID.', 'warning')
            return render_template('forgot_password.html', hide_nav=True), 400

        # Request Password Reset OTP (with anti-enumeration and Gmail SMTP dispatch)
        success, code, msg, cooldown = OTPService.request_password_reset_otp(identifier, ip_address=ip)

        if not success:
            status_code = 403 if code == "INACTIVE" else (429 if code in ("COOLDOWN", "RATE_LIMITED") else (500 if code == "EMAIL_FAILED" else 400))
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'code': code,
                    'message': msg,
                    'remaining_seconds': cooldown
                }), status_code

            flash(msg, 'danger' if status_code >= 500 else 'warning')
            return render_template('forgot_password.html', hide_nav=True, email=identifier), status_code

        # Store session state for verification step
        session['reset_identifier'] = identifier
        session['reset_purpose'] = 'reset_password'

        verify_url = url_for('auth_bp.verify_otp', email=identifier, purpose='reset_password')

        if request.is_json:
            return jsonify({
                'status': 'success',
                'code': code,
                'message': msg,
                'email': identifier,
                'cooldown_seconds': cooldown or 60,
                'redirect': verify_url
            }), 200

        flash(msg, 'success')
        return redirect(verify_url)

    return render_template('forgot_password.html', hide_nav=True)


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """
    Reset Password view:
    - GET: Renders the new password form after OTP verification.
    - POST: Updates user password in MySQL database, invalidates OTP, logs audit event, and redirects to login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    reset_token = session.get('reset_token')
    user_id = session.get('reset_user_id')
    user_email = session.get('reset_email')

    # Security check: Block direct access without successful OTP verification
    if not reset_token or not user_id:
        flash('Please verify your OTP code before resetting your password.', 'warning')
        return redirect(url_for('auth_bp.forgot_password'))

    user = User.query.get(user_id)
    if not user or not user.is_active:
        session.pop('reset_token', None)
        session.pop('reset_user_id', None)
        session.pop('reset_email', None)
        flash('Invalid session or inactive user account. Please start again.', 'danger')
        return redirect(url_for('auth_bp.forgot_password'))

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        new_password = (data.get('password') or data.get('new_password') or '').strip()
        confirm_password = (data.get('confirm_password') or '').strip()

        if not new_password or not confirm_password:
            flash('Both password fields are required.', 'warning')
            return render_template('reset_password.html', hide_nav=True, email=user.email), 400

        # Password match check
        if new_password != confirm_password:
            flash('Passwords do not match. Please verify and try again.', 'danger')
            return render_template('reset_password.html', hide_nav=True, email=user.email), 400

        # Password strength policy check
        is_strong, strength_err = validate_password_strength(new_password)
        if not is_strong:
            flash(strength_err, 'warning')
            return render_template('reset_password.html', hide_nav=True, email=user.email), 400

        # Update password hash in MySQL database using Werkzeug's secure hashing
        user.set_password(new_password)

        # Invalidate the verified OTP record in MySQL database
        now_naive = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        latest_reset_otp = PasswordResetOTP.query.filter_by(user_id=user.id, used_at=None).order_by(PasswordResetOTP.id.desc()).first()
        if latest_reset_otp:
            latest_reset_otp.used_at = now_naive

        # Record password reset in audit logs
        AuditService.log(
            action='PASSWORD_RESET',
            entity='USER',
            entity_id=user.id,
            user_id=user.id,
            details=f"Password successfully reset via email OTP verification for user '{user.username}' (email: {user.email}) from IP {request.remote_addr}."
        )

        db.session.commit()

        # Invalidate pending reset session state
        session.pop('reset_token', None)
        session.pop('reset_user_id', None)
        session.pop('reset_email', None)
        session.pop('reset_purpose', None)
        session.pop('reset_identifier', None)

        # User requirement 6: Display "Your password has been reset successfully."
        flash('Your password has been reset successfully.', 'success')

        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': 'Your password has been reset successfully.',
                'redirect': url_for('auth_bp.login')
            }), 200

        return redirect(url_for('auth_bp.login'))

    return render_template('reset_password.html', hide_nav=True, email=user.email)
