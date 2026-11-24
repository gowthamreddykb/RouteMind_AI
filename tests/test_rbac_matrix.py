"""
RouteMind AI - Comprehensive RBAC and Security Matrix Test Suite
Validates the complete role-based permission system across all 3 roles:
1. Dispatcher / Operations Analyst
2. Operations Manager
3. Administrator
"""
import sys
import os
import json

# Ensure root and parent directories are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from extensions import db
from src.models.user_model import User
from src.models.shipment_model import Shipment
from src.models.exception_model import ShipmentException
from src.models.escalation_model import ManagerEscalation
from src.security.permissions import ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN

def run_rbac_suite():
    print("=" * 70)
    print("ROUTEMIND AI - COMPREHENSIVE ROLE-BASED ACCESS CONTROL (RBAC) TEST")
    print("=" * 70)
    
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        # Query existing users
        users = User.query.all()
        print(f"Loaded {len(users)} users from database:")
        for u in users:
            print(f"  - User ID: {u.id}, Username: '{u.username}', Role: '{u.role}', Active: {u.is_active}")
            
        admin = User.query.filter_by(username='admin').first()
        manager = User.query.filter_by(username='manager').first()
        dispatcher = User.query.filter_by(username='dispatcher').first()
        deactivated = User.query.filter_by(username='deactivated_test').first()
        
        client = app.test_client()
        
        print("\n" + "-" * 70)
        print("TEST 1: UNAUTHENTICATED GATING & PUBLIC ROUTES")
        print("-" * 70)
        
        # 1.1 Public routes should succeed (200)
        public_paths = ['/auth/login', '/auth/forgot-password']
        for path in public_paths:
            res = client.get(path)
            assert res.status_code == 200, f"Expected 200 for public path {path}, got {res.status_code}"
            assert b'id="appNavbar"' not in res.data, f"Navbar leaked on unauthenticated route {path}!"
            assert b'id="copilotFab"' not in res.data, f"AI Copilot launcher leaked on unauthenticated route {path}!"
            print(f"  [PASS] Public access allowed for {path} (Navbar & AI FAB hidden)")
            
        # 1.2 Protected routes should redirect to /auth/login (302)
        protected_paths = [
            '/', '/dashboard', '/reports/', '/shipments/', '/shipments/new',
            '/exceptions/', '/ai/assistant', '/escalations/', '/users/', '/admin/settings'
        ]
        for path in protected_paths:
            res = client.get(path, follow_redirects=False)
            assert res.status_code == 302, f"Expected 302 redirect for unauthenticated {path}, got {res.status_code}"
            assert '/auth/login' in res.headers.get('Location', ''), f"Redirect location missing login for {path}"
            print(f"  [PASS] Unauthenticated access to {path} redirected to login (302)")
            
        print("\n" + "-" * 70)
        print("TEST 2: DISPATCHER / OPERATIONS ANALYST ROLE PERMISSIONS")
        print("-" * 70)
        client.get('/auth/quick-login/dispatcher', follow_redirects=True)
            
        # Allowed for Dispatcher
        allowed_dispatcher = [
            ('/', 200),
            ('/dashboard', 200),
            ('/shipments/', 200),
            ('/shipments/new', 200),
            ('/shipments/1', 200),
            ('/exceptions/', 200),
            ('/ai/assistant', 200),
            ('/escalations/', 200),
        ]
        for path, code in allowed_dispatcher:
            res = client.get(path, follow_redirects=True)
            assert res.status_code == code, f"Dispatcher failed access to {path}: expected {code}, got {res.status_code}"
            # Check navbar has Dispatcher items and DOES NOT have Admin items
            if path == '/':
                assert b'User Management' not in res.data, "Admin User Management visible to Dispatcher in navbar!"
                assert b'System Settings' not in res.data, "Admin Settings visible to Dispatcher in navbar!"
                assert b'<span>Exceptions</span>' in res.data, "Exceptions link missing from Dispatcher navbar!"
                assert b'<span>Escalations</span>' in res.data, "Escalations link missing from Dispatcher navbar!"
            print(f"  [PASS] Dispatcher GET {path} -> {res.status_code}")

        # Dispatcher CAN create an escalation
        shipment = Shipment.query.first()
        res = client.post('/escalations/create', json={
            'shipment_id': shipment.id,
            'priority': 'HIGH',
            'reason': 'RBAC Automated Test - Singapore terminal dwell delay alert',
            'dispatcher_remarks': 'Transit SLA risk observed.'
        })
        assert res.status_code == 201, f"Dispatcher must be able to create escalation! Got {res.status_code}: {res.data}"
        esc_id = res.get_json()['escalation']['id']
        print(f"  [PASS] Dispatcher POST /escalations/create -> 201 (Created escalation #{esc_id})")
            
        # Forbidden for Dispatcher
        forbidden_dispatcher = [
            ('/users/', 'GET', 403),
            ('/users/new', 'GET', 403),
            ('/admin/settings', 'GET', 403),
            ('/admin/thresholds', 'POST', 403),
            (f'/escalations/{esc_id}/update-status', 'POST', 403),
            (f'/escalations/{esc_id}/assign', 'POST', 403),
            (f'/escalations/{esc_id}/resolve', 'POST', 403),
        ]
        for path, method, code in forbidden_dispatcher:
            if method == 'POST':
                res = client.post(path, json={'status': 'RESOLVED', 'reason': 'Test', 'assigned_to_name': 'Tester'})
            else:
                res = client.get(path)
            assert res.status_code == code, f"Dispatcher should be forbidden ({code}) on {path}, got {res.status_code}"
            print(f"  [PASS] Dispatcher {method} {path} -> {res.status_code} (Properly blocked)")

        # Verify Dispatcher cannot assign exceptions
        exc = ShipmentException.query.first()
        if exc:
            res = client.post('/exceptions/api/assign', json={'exception_id': exc.id, 'assigned_to': 'analyst'})
            assert res.status_code == 403, f"Dispatcher must NOT be able to assign exceptions! Got {res.status_code}"
            print(f"  [PASS] Dispatcher POST /exceptions/api/assign -> 403 (Exception assignment blocked)")

        print("\n" + "-" * 70)
        print("TEST 3: OPERATIONS MANAGER ROLE PERMISSIONS")
        print("-" * 70)
        client.get('/auth/quick-login/manager', follow_redirects=True)
            
        # Allowed for Manager
        allowed_manager = [
            ('/', 200),
            ('/dashboard', 200),
            ('/shipments/', 200),
            ('/shipments/1', 200),
            ('/exceptions/', 200),
            ('/ai/assistant', 200),
            ('/escalations/', 200),
        ]
        for path, code in allowed_manager:
            res = client.get(path, follow_redirects=True)
            assert res.status_code == code, f"Manager failed access to {path}: expected {code}, got {res.status_code}"
            if path == '/':
                assert b'User Management' not in res.data, "Admin User Management visible to Manager in navbar!"
                assert b'System Settings' not in res.data, "Admin Settings visible to Manager in navbar!"
                assert b'<span>Exceptions</span>' in res.data, "Exceptions link missing from Manager navbar!"
                assert b'<span>Escalations</span>' in res.data, "Escalations link missing from Manager navbar!"
            print(f"  [PASS] Operations Manager GET {path} -> {res.status_code}")
            
        # Forbidden for Manager
        forbidden_manager = [
            ('/users/', 403),
            ('/users/new', 403),
            ('/admin/settings', 403),
        ]
        for path, code in forbidden_manager:
            res = client.get(path, follow_redirects=True)
            assert res.status_code == code, f"Manager should be forbidden ({code}) on {path}, got {res.status_code}"
            print(f"  [PASS] Operations Manager GET {path} -> {res.status_code} (Properly blocked)")

        # Manager CAN update status, assign, and resolve escalations
        res = client.post(f'/escalations/{esc_id}/update-status', json={'status': 'UNDER_REVIEW', 'manager_remarks': 'Reviewing terminal slot.'})
        assert res.status_code == 200, f"Manager must be able to update escalation status! Got {res.status_code}"
        print(f"  [PASS] Operations Manager POST /escalations/{esc_id}/update-status -> 200 (Status updated to UNDER_REVIEW)")

        res = client.post(f'/escalations/{esc_id}/assign', json={'assigned_to_name': 'Suresh Raina (Ops Manager)'})
        assert res.status_code == 200, f"Manager must be able to assign escalation! Got {res.status_code}"
        print(f"  [PASS] Operations Manager POST /escalations/{esc_id}/assign -> 200 (Assignment successful)")

        res = client.post(f'/escalations/{esc_id}/resolve', json={'resolution_notes': 'Vessel berthing expedited with PSA port authority.'})
        assert res.status_code == 200, f"Manager must be able to resolve escalation! Got {res.status_code}"
        print(f"  [PASS] Operations Manager POST /escalations/{esc_id}/resolve -> 200 (Escalation marked RESOLVED)")

        # Manager CAN assign exceptions
        if exc:
            res = client.post('/exceptions/api/assign', json={'exception_id': exc.id, 'assigned_to': dispatcher.id})
            assert res.status_code == 200, f"Manager must be able to assign exceptions! Got {res.status_code}"
            print(f"  [PASS] Operations Manager POST /exceptions/api/assign -> 200 (Assignment successful)")

        print("\n" + "-" * 70)
        print("TEST 4: ADMINISTRATOR ROLE PERMISSIONS")
        print("-" * 70)
        client.get('/auth/quick-login/admin', follow_redirects=True)
            
        # Allowed for Admin
        allowed_admin = [
            ('/', 200),
            ('/dashboard', 200),
            ('/shipments/', 200),
            ('/users/', 200),
            ('/users/new', 200),
            ('/admin/settings', 200),
            ('/ai/assistant', 200),
            ('/escalations/', 200),
        ]
        for path, code in allowed_admin:
            res = client.get(path, follow_redirects=True)
            assert res.status_code == code, f"Admin failed access to {path}: expected {code}, got {res.status_code}"
            if path == '/':
                assert b'<span>User Management</span>' in res.data, "User Management link missing from Admin navbar!"
                assert b'<span>System Settings</span>' in res.data, "Settings link missing from Admin navbar!"
                assert b'<span>Escalations</span>' not in res.data, "Escalations link should not be in Admin operational navbar!"
            print(f"  [PASS] Administrator GET {path} -> {res.status_code}")

        # Administrator MUST NOT have supervisory resolution authority over escalations
        res = client.post(f'/escalations/{esc_id}/update-status', json={'status': 'RESOLVED'})
        assert res.status_code == 403, f"Administrator must NOT be able to resolve escalations! Got {res.status_code}"
        print(f"  [PASS] Administrator POST /escalations/{esc_id}/update-status -> 403 (Supervisory update forbidden for Admin)")
        
        res = client.post(f'/escalations/{esc_id}/resolve', json={'resolution_notes': 'Unauthorized admin closure attempt'})
        assert res.status_code == 403, f"Administrator must NOT be able to resolve escalations! Got {res.status_code}"
        print(f"  [PASS] Administrator POST /escalations/{esc_id}/resolve -> 403 (Resolution forbidden for Admin)")

        print("\n" + "-" * 70)
        print("TEST 5: DEACTIVATED USER RESTRICTION")
        print("-" * 70)
        client.get('/auth/logout', follow_redirects=True)
        if deactivated:
            res = client.get(f'/auth/quick-login/{deactivated.username}', follow_redirects=True)
            assert res.status_code == 200
            assert b'Sign In' in res.data or b'Inactive' in res.data or b'inactive' in res.data, "Deactivated user was allowed into the system!"
            print(f"  [PASS] Deactivated user '{deactivated.username}' is blocked from accessing the system.")
            
        print("\n" + "=" * 70)
        print("ALL RBAC AND SECURITY MATRIX TESTS PASSED PERFECTLY!")
        print("=" * 70)

if __name__ == '__main__':
    run_rbac_suite()
