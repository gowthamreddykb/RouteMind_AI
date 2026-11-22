from functools import wraps
from flask import abort, request, jsonify, render_template
from flask_login import current_user

ROLE_DISPATCHER = "Dispatcher"
ROLE_MANAGER = "Operations Manager"
ROLE_ADMIN = "Administrator"
ROLE_SUPPORT = "Customer Support"

ALL_ROLES = (ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, ROLE_SUPPORT)

ROLE_ALIASES = {
    'dispatcher': ROLE_DISPATCHER,
    'analyst': ROLE_DISPATCHER,
    'operations analyst': ROLE_DISPATCHER,
    'dispatcher / operations analyst': ROLE_DISPATCHER,
    'manager': ROLE_MANAGER,
    'operations manager': ROLE_MANAGER,
    'ops manager': ROLE_MANAGER,
    'admin': ROLE_ADMIN,
    'administrator': ROLE_ADMIN,
    'system administrator': ROLE_ADMIN,
    'customer support': ROLE_SUPPORT,
    'support': ROLE_SUPPORT,
    'customer service': ROLE_SUPPORT,
}

def normalize_role(role_name):
    if not role_name:
        return ""
    key = str(role_name).strip().lower()
    return ROLE_ALIASES.get(key, str(role_name).strip())

def roles_required(*allowed_roles):
    """
    Restrict access to users with the specified application roles.
    Enforces exact role-based authorization for views and API endpoints.
    """
    normalized_allowed = {normalize_role(r) for r in allowed_roles}

    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            from flask import current_app
            if current_app.config.get('LOGIN_DISABLED') or current_app.config.get('TESTING'):
                return function(*args, **kwargs)

            if not current_user.is_authenticated:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required', 'status': 401}), 401
                abort(401)

            user_role = normalize_role(getattr(current_user, 'role', ''))
            if user_role not in normalized_allowed:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'error': 'Access denied: Insufficient role permissions.',
                        'user_role': user_role,
                        'required_roles': list(normalized_allowed)
                    }), 403
                abort(403)

            return function(*args, **kwargs)
        return wrapper
    return decorator

def can_manage_escalations(user):
    """Only Operations Managers can update status, assign responsibility, and resolve escalations."""
    if not user or not user.is_authenticated:
        return False
    return normalize_role(getattr(user, 'role', '')) == ROLE_MANAGER

def can_approve_communication(user):
    """Backward compatibility helper mapping to manager authority."""
    return can_manage_escalations(user)

def can_manage_users(user):
    """Only Administrators can manage user accounts and role assignments."""
    if not user or not user.is_authenticated:
        return False
    return normalize_role(getattr(user, 'role', '')) == ROLE_ADMIN

def can_manage_settings(user):
    """Only Administrators can manage system configurations and model thresholds."""
    if not user or not user.is_authenticated:
        return False
    return normalize_role(getattr(user, 'role', '')) == ROLE_ADMIN

def can_assign_exceptions(user):
    """Operations Managers can assign and resolve exceptions."""
    if not user or not user.is_authenticated:
        return False
    return normalize_role(getattr(user, 'role', '')) == ROLE_MANAGER

role_required = roles_required
