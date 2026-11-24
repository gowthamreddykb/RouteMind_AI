import os
import sys
import json
import sqlite3

# Ensure RouteMind_AI root is on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from src.models.user_model import User
from src.models.shipment_model import Shipment
from src.models.customer_model import Customer
from src.models.product_model import Product
from src.models.model_score_model import ModelScore
from src.models.exception_model import ShipmentException
from src.models.communication_model import CommunicationLog
from src.models.audit_log_model import AuditLog

def test_database_tables():
    print("=== Testing Database Tables & Data Persistence ===")
    app = create_app('development')
    with app.app_context():
        # Check SQLite db directly
        db_path = os.path.join(ROOT, "instance", "routemind.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"Total tables found: {len(tables)}")
        for t in sorted(tables):
            cnt = cur.execute(f"SELECT count(1) FROM [{t}]").fetchone()[0]
            print(f"  - {t}: {cnt} rows")
        conn.close()

        # Test SQLAlchemy queries
        user_count = User.query.count()
        shipment_count = Shipment.query.count()
        customer_count = Customer.query.count()
        product_count = Product.query.count()
        print(f"SQLAlchemy ORM Queries:")
        print(f"  - Users: {user_count}")
        print(f"  - Shipments: {shipment_count}")
        print(f"  - Customers: {customer_count}")
        print(f"  - Products: {product_count}")

def test_routes_and_buttons():
    print("\n=== Testing Flask Application Routes & UI Endpoints ===")
    app = create_app('development')
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    print("\n--- 1. Testing Unauthenticated Gate (Before Sign In) ---")
    resp = client.get('/', follow_redirects=False)
    print(f"GET / (unauthenticated) -> {resp.status_code} (Redirects to: {resp.headers.get('Location')})")
    assert resp.status_code in [302, 301]
    assert '/auth/login' in resp.headers.get('Location')

    resp_login = client.get('/auth/login')
    print(f"GET /auth/login -> {resp_login.status_code}")
    assert resp_login.status_code == 200
    assert b'id="appNavbar"' not in resp_login.data, "FAIL: Navbar must be hidden on login page!"
    assert b'copilot-fab' not in resp_login.data, "FAIL: AI Copilot FAB must be hidden on login page!"
    print("  [PASS] Navbar and AI Copilot FAB are HIDDEN on /auth/login.")

    resp_forgot = client.get('/auth/forgot-password')
    print(f"GET /auth/forgot-password -> {resp_forgot.status_code}")
    assert resp_forgot.status_code == 200
    assert b'id="appNavbar"' not in resp_forgot.data, "FAIL: Navbar must be hidden on forgot-password page!"
    assert b'copilot-fab' not in resp_forgot.data, "FAIL: AI Copilot FAB must be hidden on forgot-password page!"
    print("  [PASS] Navbar and AI Copilot FAB are HIDDEN on /auth/forgot-password.")

    print("\n--- 2. Testing Authentication (Sign In Flow) ---")
    login_resp = client.get('/auth/quick-login/dispatcher', follow_redirects=True)
    print(f"GET /auth/quick-login/dispatcher -> {login_resp.status_code} [Sign In Success]")
    assert login_resp.status_code == 200
    assert b'id="appNavbar"' in login_resp.data, "FAIL: Navbar must be visible once signed in!"
    assert b'copilot-fab' in login_resp.data, "FAIL: AI Copilot FAB must be visible once signed in!"
    print("  [PASS] Navbar and AI Copilot FAB are VISIBLE on authenticated Control Tower.")

    print("\n--- 3. Testing Authenticated Application Routes ---")
    authenticated_routes = [
        ('/', 200),
        ('/dashboard', 200),
        ('/health', 200),
        ('/api/models', 200),
        ('/shipments/', 200),
        ('/shipments/new', 200),
        ('/exceptions/', 200),
        ('/ai/assistant', 200),
        ('/escalations/', 200),
        ('/shipments/1', 200),
        ('/shipments/SHP-10482', 200)
    ]

    for url, expected_code in authenticated_routes:
        resp = client.get(url, follow_redirects=True)
        status = "OK" if resp.status_code == expected_code else f"FAILED (Got {resp.status_code})"
        print(f"GET {url} -> {resp.status_code} [{status}]")
        assert resp.status_code == expected_code

    print("\n--- 4. Testing Sign Out Flow ---")
    logout_resp = client.get('/auth/logout', follow_redirects=True)
    print(f"GET /auth/logout -> {logout_resp.status_code} (Redirected back to login)")
    assert logout_resp.status_code == 200
    assert b'id="appNavbar"' not in logout_resp.data
    assert b'copilot-fab' not in logout_resp.data
    print("  [PASS] Logged out successfully. Navbar and AI Copilot FAB are hidden again.")

def test_data_insertion():
    print("\n=== Testing Data Insertion & SQLAlchemy Commit ===")
    app = create_app('development')
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        # Insert a test customer if needed
        cust = Customer.query.filter_by(first_name="TestFlow").first()
        if not cust:
            cust = Customer(
                first_name="TestFlow",
                last_name="Customer",
                segment="Consumer",
                city="San Jose",
                state="CA",
                country="United States"
            )
            db.session.add(cust)
            db.session.commit()
            print("Successfully inserted Test Customer via SQLAlchemy!")
        else:
            print("Test Customer already exists.")

        # Insert a test product if needed
        prod = Product.query.filter_by(product_name="TestFlow Smart Tracker").first()
        if not prod:
            prod = Product(
                product_name="TestFlow Smart Tracker",
                category_name="Electronics",
                department_name="Technology",
                product_price=199.99
            )
            db.session.add(prod)
            db.session.commit()
            print("Successfully inserted Test Product via SQLAlchemy!")
        else:
            print("Test Product already exists.")

        # Test creating a new shipment
        import random
        test_ship_num = f"SHP-TEST-{random.randint(10000, 99999)}"
        new_shipment = Shipment(
            shipment_number=test_ship_num,
            customer_id=cust.id,
            product_id=prod.id,
            order_date=db.func.current_timestamp(),
            scheduled_days=4,
            shipping_mode="Standard Class",
            destination_region="South Asia",
            market="Pacific Asia",
            quantity=2,
            sales=399.98,
            order_status="PENDING",
            risk_level="PENDING_ANALYSIS",
            dock_clearance_status="HOLD"
        )
        db.session.add(new_shipment)
        db.session.commit()

        # Verify saved shipment
        retrieved = Shipment.query.filter_by(shipment_number=test_ship_num).first()
        assert retrieved is not None
        print(f"Successfully inserted and verified Shipment {test_ship_num} (ID: {retrieved.id}) in database!")

        # Clean up test shipment
        db.session.delete(retrieved)
        db.session.commit()
        print("Cleaned up test shipment.")

if __name__ == '__main__':
    test_database_tables()
    test_routes_and_buttons()
    test_data_insertion()
