from src.security.permissions import (
    ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, ALL_ROLES, normalize_role
)

ROLES = {
    'ADMIN': ROLE_ADMIN,
    'MANAGER': ROLE_MANAGER,
    'DISPATCHER': ROLE_DISPATCHER
}

PERMISSIONS = {
    ROLE_ADMIN: ['read', 'write', 'execute', 'administer', 'model_management'],
    ROLE_MANAGER: ['read', 'write', 'execute', 'manage_escalations', 'resolve_escalations', 'resolve_exceptions', 'approve_communications'],
    ROLE_DISPATCHER: ['read', 'write', 'execute', 'create_escalations', 'create_exceptions', 'draft_communications']
}

def has_permission(role, permission):
    norm = normalize_role(role)
    return permission in PERMISSIONS.get(norm, [])
