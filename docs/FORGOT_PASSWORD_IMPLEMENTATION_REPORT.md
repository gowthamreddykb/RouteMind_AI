# RouteMind AI – Forgot Password & Reset Password Workflow Implementation Report

## Executive Summary
A production-ready **Forgot Password & Reset Password Workflow** has been implemented in the RouteMind AI Maritime Logistics Control Tower Flask application. The workflow features **Gmail SMTP TLS email dispatch**, **cryptographic 6-digit OTP generation**, **salted one-way database hashing**, **strict 60-second cooldown**, **5-minute expiry**, **5-attempt lockout**, **anti-user-enumeration**, **password complexity enforcement**, **audit logging**, and **automatic session invalidation**.

All data operations are directly persisted in MySQL (`routemind_db`), with zero reliance on synthetic, mock, or hardcoded values.

---

## 1. Architecture & Workflow Design

The workflow follows a 6-stage lifecycle:

```
[1. Login Page] ──► "Forgot Password?" Link
        │
        ▼
[2. Forgot Password Page] (/auth/forgot-password)
        │ ──► User enters email or Login ID
        │ ──► Look up in MySQL `users` table
        │ ──► Anti-enumeration: Generic response for non-existent accounts
        │ ──► Check 60s cooldown against latest OTP request
        │ ──► Generate cryptographic 6-digit OTP (secrets.randbelow)
        │ ──► Dispatch HTML verification email via Gmail SMTP
        │ ──► Store salted OTP hash in `password_reset_otps` table (never plaintext)
        ▼
[3. OTP Verification Page] (/auth/verify-otp?purpose=reset_password)
        │ ──► User enters 6-digit OTP
        │ ──► Validates against DB hash (check_password_hash)
        │ ──► Rejects expired (>5 min), consumed, or invalid OTPs
        │ ──► Tracks failed attempts: locks after 5 attempts
        │ ──► On success: Generates one-time cryptographically secure reset token
        ▼
[4. Create New Password Page] (/auth/reset-password)
        │ ──► Requires verified session token (blocks direct URL access)
        │ ──► Validates password matching & complexity:
        │       - Minimum 8 characters
        │       - Uppercase (A-Z) & lowercase (a-z)
        │       - Number (0-9) or symbol
        │ ──► Show/hide eye toggles on both inputs
        ▼
[5. MySQL Database & Audit Log Update]
        │ ──► Hash new password with Werkzeug generate_password_hash
        │ ──► Update `users.password_hash` in MySQL
        │ ──► Mark OTP as consumed (`used_at = NOW()`)
        │ ──► Invalidate reset session tokens
        │ ──► Record `PASSWORD_RESET` event in MySQL `audit_logs` table
        ▼
[6. Redirect to Login Page] (/auth/login)
        │ ──► Flash: "Your password has been reset successfully."
        │ ──► User authenticates with new credentials
        │ ──► Old password is permanently invalidated
        │ ──► Loads role-based permissions and routes to Control Tower Dashboard
```

---

## 2. SMTP Email Configuration & Gmail Dispatch

The email service uses the configured Gmail App Password credentials:

- **SMTP Host**: `smtp.gmail.com`
- **Port**: `587` (STARTTLS)
- **Encryption**: TLS (`MAIL_USE_TLS=true`)
- **Sender**: `RouteMind AI <gowthamreddykb@gmail.com>`
- **Authentication**: Gmail App Password (`gdvz hpwo tqak rgle`)

### Security in Email Service:
- **No Plaintext Logging**: OTP values are **never** logged to server stdout or application logs.
- **Delivery Verification**: If Gmail SMTP fails to deliver, the transaction is rejected, preventing password reset without receipt of the code.
- **Maritime Enterprise Template**: Includes RouteMind AI branding, 6-digit spaced code display, 5-minute expiry notice, and security incident advisory.

---

## 3. Database Schema: `password_reset_otps`

A dedicated, indexed table was created in MySQL with a cascade foreign key constraint linking to `users(id)`:

```sql
CREATE TABLE IF NOT EXISTS `password_reset_otps` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `otp_hash` VARCHAR(255) NOT NULL,
    `expires_at` DATETIME NOT NULL,
    `attempts` INT NOT NULL DEFAULT 0,
    `verified_at` DATETIME NULL,
    `used_at` DATETIME NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_pwd_reset_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_pwd_reset_user_id` (`user_id`),
    INDEX `idx_pwd_reset_expires_at` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 4. Key Security Controls

| Security Control | Implementation |
| :--- | :--- |
| **Cryptographic Randomness** | Generated using `secrets.randbelow(1000000):06d` |
| **Password & OTP Hashing** | Salted PBKDF2/scrypt hashes via Werkzeug; zero plaintext storage |
| **Anti-User-Enumeration** | Generic response returned if email or username does not exist |
| **Rate Limiting & Cooldown** | Strict 60-second cooldown between OTP dispatches |
| **Expiry Enforcement** | OTP records expire strictly after 5 minutes (`expires_at < utcnow`) |
| **Brute-Force Protection** | Counter tracks failed attempts; locks code permanently after 5 attempts |
| **Direct URL Access Blocking** | `/auth/reset-password` blocks access if valid reset token is missing |
| **Single-Use Invalidation** | OTPs and reset tokens are invalidated immediately upon password change |
| **Audit Logging** | Every password reset generates an immutable entry in `audit_logs` |

---

## 5. Automated Test Suite Results

A dedicated automated test suite (`tests/test_forgot_password.py`) was created and executed alongside the complete regression suite:

```
tests/test_forgot_password.py::test_forgot_password_page_loads PASSED              [12%]
tests/test_forgot_password.py::test_anti_enumeration_nonexistent_user PASSED       [25%]
tests/test_forgot_password.py::test_inactive_account_rejected PASSED               [37%]
tests/test_forgot_password.py::test_otp_dispatch_and_cooldown PASSED               [50%]
tests/test_forgot_password.py::test_otp_verification_attempt_limit_and_lockout PASSED [62%]
tests/test_forgot_password.py::test_otp_verification_expired PASSED                [75%]
tests/test_forgot_password.py::test_direct_access_to_reset_password_blocked PASSED [87%]
tests/test_forgot_password.py::test_full_reset_password_end_to_end PASSED         [100%]

tests/test_flow_buttons.py:         1 PASSED (All 11 interactive buttons & transitions verified)
Regression Suites:
tests/test_email_otp_auth.py:      13 PASSED
tests/test_auth.py:                 2 PASSED
tests/test_dashboard_charts.py:     5 PASSED

======================= TOTAL: 29 PASSED, 0 FAILED =======================
```

---

## 6. Changed Files Summary

1. `src/models/otp_model.py`: Added `PasswordResetOTP` model with lifecycle properties (`is_expired`, `is_consumed`, `check_otp()`, `create_otp()`).
2. `src/services/email_service.py`: Added purpose-specific password reset email template with Gmail SMTP dispatch, removed dev plaintext logs.
3. `src/services/otp_service.py`: Implemented `request_password_reset_otp()` and `verify_password_reset_otp()` with anti-enumeration, 60s cooldown, and 5-attempt lockout.
4. `src/routes/auth_routes.py`:
   - Updated `/forgot-password` route with email/login ID validation and anti-enumeration.
   - Updated `/verify-otp` route to handle password reset OTP verification and session token generation.
   - Updated `/resend-otp` route to support password reset cooldown resends.
   - Enhanced `/reset-password` route with password complexity check, MySQL password update, OTP invalidation, and audit logging.
5. `templates/login.html`: Updated login ID input field to accept email or username.
6. `templates/forgot_password.html`: Updated form to accept registered enterprise email or Login ID.
7. `templates/verify_otp.html`: Updated UI to handle password reset flow, countdown timers, and resend.
8. `templates/reset_password.html`: Added password strength criteria checkmarks, mismatch alerts, and show/hide password eye toggles.
9. `.env`: Configured Gmail SMTP credentials for automated dispatch.
10. `tests/test_forgot_password.py`: 8 end-to-end integration and security test cases.
11. Mirrored all files to `C:\gowtham_mithraz\RouteMind_AI\`.
