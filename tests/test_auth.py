import pytest
from src.security.authentication import hash_password, verify_password
from src.security.role_permissions import has_permission

def test_password_hashing():
    p = 'secure_password_123'
    h = hash_password(p)
    assert h != p
    assert verify_password(p, h)
    assert not verify_password('wrong', h)

def test_permissions():
    assert has_permission('admin', 'administer')
    assert has_permission('dispatcher', 'write')
    assert not has_permission('viewer', 'write')
