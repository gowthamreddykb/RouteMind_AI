import os
import sys
import datetime as dt
from werkzeug.security import generate_password_hash

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from extensions import db
from src.models.user_model import User
from src.models.customer_model import Customer
from src.models.product_model import Product
from src.models.shipment_model import Shipment
from src.models.shipment_event_model import ShipmentEvent
from src.models.exception_model import ShipmentException
from src.models.exception_action_model import ExceptionAction
from src.models.communication_model import CommunicationLog

def seed_database(config_env=None):
    env = config_env or os.environ.get('FLASK_ENV', 'development')
    app = create_app(env)
    with app.app_context():
        print("Seeding database tables with diverse, non-duplicate production records...")

        # 1. Seed Users
        users_data = [
            ("admin", "admin@routemind.ai", "admin123", "admin"),
            ("manager", "manager@routemind.ai", "manager123", "manager"),
            ("dispatcher", "dispatcher@routemind.ai", "dispatcher123", "dispatcher"),
            ("analyst", "analyst@routemind.ai", "analyst123", "analyst"),
            ("suresh_raina", "suresh@routemind.ai", "suresh123", "manager"),
            ("gowtham_k", "gowtham@routemind.ai", "gowtham123", "dispatcher")
        ]
        for uname, uemail, upass, urole in users_data:
            u = User.query.filter_by(email=uemail).first()
            if not u:
                u = User(
                    username=uname,
                    email=uemail,
                    password_hash=generate_password_hash(upass),
                    role=urole,
                    is_active=True
                )
                db.session.add(u)
        db.session.commit()
        print(f"Users seeded: {User.query.count()}")

        # 2. Seed Customers
        customers_data = [
            ("Meridian", "Imports", "Corporate", "Chennai", "Tamil Nadu", "India"),
            ("Pacific", "Trade Co", "Corporate", "Mumbai", "Maharashtra", "India"),
            ("Eastport", "Global", "Consumer", "Visakhapatnam", "Andhra Pradesh", "India"),
            ("Oceanic", "Retail", "Home Office", "Kochi", "Kerala", "India"),
            ("Apex", "Transatlantic", "Corporate", "Singapore", "Central", "Singapore"),
            ("Nordic", "Cargo Ltd", "Corporate", "Rotterdam", "South Holland", "Netherlands"),
            ("Horizon", "Logistics", "Consumer", "Hamburg", "Hamburg", "Germany"),
            ("Vertex", "Trade Inc", "Corporate", "Antwerp", "Flanders", "Belgium"),
            ("Sunbelt", "Distributors", "Home Office", "Dubai", "Dubai", "United Arab Emirates"),
            ("Atlas", "Maritime", "Corporate", "Los Angeles", "CA", "United States")
        ]
        for fn, ln, seg, city, state, country in customers_data:
            c = Customer.query.filter_by(first_name=fn, last_name=ln).first()
            if not c:
                c = Customer(first_name=fn, last_name=ln, segment=seg, city=city, state=state, country=country)
                db.session.add(c)
        db.session.commit()
        print(f"Customers seeded: {Customer.query.count()}")

        # 3. Seed Products
        products_data = [
            ("Smart GPS Container Tracker", "Tracking & Telemetry", "Technology", 280.00),
            ("Industrial Marine Valve 4-Inch", "Marine Engineering", "Hardware", 450.00),
            ("Lithium Marine Auxiliary Battery", "Power Systems", "Electrical", 890.00),
            ("Cold-Chain Reefer Sensor Set", "Reefer Monitoring", "Electronics", 320.00),
            ("Heavy Duty Cargo Lashing Straps", "Deck Equipment", "Safety", 75.00),
            ("Marine AIS Class-A Transponder", "Navigation Equipment", "Avionics/Marine", 1250.00),
            ("Digital Fuel Flow Meter Sensor", "Engine Telemetry", "Instrumentation", 620.00),
            ("High-Pressure Bilge Pump 24V", "Pumping Systems", "Mechanical", 540.00)
        ]
        for pname, cat, dept, price in products_data:
            p = Product.query.filter_by(product_name=pname).first()
            if not p:
                p = Product(product_name=pname, category_name=cat, department_name=dept, product_price=price)
                db.session.add(p)
        db.session.commit()
        print(f"Products seeded: {Product.query.count()}")

        custs = Customer.query.all()
        prods = Product.query.all()

        # 4. Seed Shipments
        shipments_spec = [
            {
                "num": "SHP-10482", "cust": custs[0], "prod": prods[0],
                "mode": "Standard Class", "days": 4, "sales": 1120.0, "qty": 4,
                "dest_reg": "Western Europe", "dest_country": "France", "mkt": "Europe",
                "risk": "HIGH", "clearance": "DOCK_HOLD_INSPECTION", "status": "IN_TRANSIT",
                "p1": 0.42, "p2": 0.82
            },
            {
                "num": "SHP-10476", "cust": custs[1], "prod": prods[1],
                "mode": "Second Class", "days": 2, "sales": 450.0, "qty": 1,
                "dest_reg": "Middle East", "dest_country": "United Arab Emirates", "mkt": "Pacific Asia",
                "risk": "MEDIUM", "clearance": "CLEAR_FOR_TRANSIT", "status": "PENDING",
                "p1": 0.28, "p2": 0.64
            },
            {
                "num": "SHP-10469", "cust": custs[2], "prod": prods[2],
                "mode": "Standard Class", "days": 4, "sales": 890.0, "qty": 1,
                "dest_reg": "South Asia", "dest_country": "Sri Lanka", "mkt": "Pacific Asia",
                "risk": "LOW", "clearance": "CLEAR_FOR_TRANSIT", "status": "IN_TRANSIT",
                "p1": 0.14, "p2": 0.28
            },
            {
                "num": "SHP-10455", "cust": custs[3], "prod": prods[3],
                "mode": "First Class", "days": 1, "sales": 640.0, "qty": 2,
                "dest_reg": "Western Europe", "dest_country": "Germany", "mkt": "Europe",
                "risk": "CRITICAL", "clearance": "CARRIER_EXPEDITE", "status": "DELAYED",
                "p1": 0.48, "p2": 0.94
            },
            {
                "num": "SHP-10451", "cust": custs[4], "prod": prods[4],
                "mode": "Standard Class", "days": 4, "sales": 375.0, "qty": 5,
                "dest_reg": "Pacific Asia", "dest_country": "Singapore", "mkt": "Pacific Asia",
                "risk": "LOW", "clearance": "CLEAR_FOR_TRANSIT", "status": "DELIVERED",
                "p1": 0.11, "p2": 0.22
            },
            {
                "num": "SHP-10440", "cust": custs[5], "prod": prods[5],
                "mode": "Second Class", "days": 2, "sales": 2500.0, "qty": 2,
                "dest_reg": "Western Europe", "dest_country": "Netherlands", "mkt": "Europe",
                "risk": "HIGH", "clearance": "DOCK_HOLD_INSPECTION", "status": "IN_TRANSIT",
                "p1": 0.39, "p2": 0.78
            },
            {
                "num": "SHP-10435", "cust": custs[6], "prod": prods[6],
                "mode": "Standard Class", "days": 4, "sales": 620.0, "qty": 1,
                "dest_reg": "North America", "dest_country": "United States", "mkt": "USCA",
                "risk": "LOW", "clearance": "CLEAR_FOR_TRANSIT", "status": "IN_TRANSIT",
                "p1": 0.16, "p2": 0.25
            },
            {
                "num": "SHP-10428", "cust": custs[7], "prod": prods[7],
                "mode": "Same Day", "days": 1, "sales": 1080.0, "qty": 2,
                "dest_reg": "Western Europe", "dest_country": "Belgium", "mkt": "Europe",
                "risk": "MEDIUM", "clearance": "CLEAR_FOR_TRANSIT", "status": "PENDING",
                "p1": 0.32, "p2": 0.58
            },
            {
                "num": "SHP-10420", "cust": custs[8], "prod": prods[0],
                "mode": "Standard Class", "days": 4, "sales": 560.0, "qty": 2,
                "dest_reg": "Middle East", "dest_country": "United Arab Emirates", "mkt": "Pacific Asia",
                "risk": "LOW", "clearance": "CLEAR_FOR_TRANSIT", "status": "DELIVERED",
                "p1": 0.15, "p2": 0.19
            },
            {
                "num": "SHP-10415", "cust": custs[9], "prod": prods[1],
                "mode": "First Class", "days": 1, "sales": 900.0, "qty": 2,
                "dest_reg": "North America", "dest_country": "United States", "mkt": "USCA",
                "risk": "HIGH", "clearance": "CARRIER_EXPEDITE", "status": "DELAYED",
                "p1": 0.44, "p2": 0.86
            }
        ]

        now = dt.datetime.now(dt.timezone.utc)
        for idx, s in enumerate(shipments_spec):
            existing = Shipment.query.filter_by(shipment_number=s["num"]).first()
            if not existing:
                order_time = now - dt.timedelta(days=idx * 2)
                shp = Shipment(
                    shipment_number=s["num"],
                    customer_id=s["cust"].id,
                    product_id=s["prod"].id,
                    order_date=order_time,
                    scheduled_days=s["days"],
                    shipping_mode=s["mode"],
                    order_status=s["status"],
                    sales=s["sales"],
                    quantity=s["qty"],
                    product_price=s["prod"].product_price,
                    origin_region="US Center",
                    destination_region=s["dest_reg"],
                    destination_country=s["dest_country"],
                    market=s["mkt"],
                    order_creation_prob=s["p1"],
                    dispatch_prob=s["p2"],
                    risk_level=s["risk"],
                    dock_clearance_status=s["clearance"]
                )
                db.session.add(shp)
                db.session.flush()

                # Add events
                e1 = ShipmentEvent(
                    shipment_id=shp.id,
                    event_type='ORDER_CREATED',
                    notes=f"Order booked via {s['mode']}",
                    event_timestamp=order_time
                )
                e2 = ShipmentEvent(
                    shipment_id=shp.id,
                    event_type='DOCK_DISPATCHED',
                    warehouse_processing_time=2.5,
                    notes=f"Dock departure recorded. Status: {s['clearance']}",
                    event_timestamp=order_time + dt.timedelta(hours=18)
                )
                db.session.add_all([e1, e2])

        db.session.commit()
        print(f"Shipments seeded: {Shipment.query.count()}")
        print(f"Shipment Events seeded: {ShipmentEvent.query.count()}")

        # 5. Seed Exceptions
        high_risk_shipments = Shipment.query.filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL'])).all()
        exc_types = [
            ("Port Congestion & Berthing Hold", "HIGH", "CRITICAL", "Priya Sharma"),
            ("Feeder Vessel Delay", "HIGH", "CRITICAL", "Arun Kumar"),
            ("Customs Documentation Hold", "MEDIUM", "HIGH", "Alexander Wright"),
            ("Carrier Capacity Reroute", "HIGH", "CRITICAL", "Sarah Jenkins")
        ]
        for i, shp in enumerate(high_risk_shipments[:4]):
            ex = ShipmentException.query.filter_by(shipment_id=shp.id).first()
            if not ex:
                et, sev, prio, officer = exc_types[i % len(exc_types)]
                ex = ShipmentException(
                    shipment_id=shp.id,
                    exception_type=et,
                    severity=sev,
                    status='OPEN' if i % 2 == 0 else 'INVESTIGATING',
                    assigned_to=officer,
                    created_at=now - dt.timedelta(hours=i*6)
                )
                db.session.add(ex)
                db.session.flush()
                act = ExceptionAction(
                    exception_id=ex.id,
                    action_taken="Requested priority terminal offload queue and customs pre-clearance.",
                    taken_by=officer,
                    action_timestamp=now - dt.timedelta(hours=i*3)
                )
                db.session.add(act)

        db.session.commit()
        print(f"Exceptions seeded: {ShipmentException.query.count()}")

        # 6. Seed Communications
        comms_data = [
            ("Meridian Imports", "logistics@meridianimports.com", "[RouteMind Operational Notice] Delivery Commitment Notice - SHP-10482", "Anticipated 48-72h delay due to Singapore port congestion. Priority handling applied."),
            ("Oceanic Retail", "supplychain@oceanicretail.com", "[RouteMind Update] Carrier Handover Priority Linehaul - SHP-10455", "Express feeder vessel upgrade confirmed to meet SLA window."),
            ("Nordic Cargo Ltd", "dispatch@nordiccargo.nl", "[RouteMind Notice] Dock Clearance Documentation Verified - SHP-10440", "Quay inspection clearance complete. Consignment released to linehaul.")
        ]
        for i, (rec_name, rec_email, subj, body) in enumerate(comms_data):
            c_log = CommunicationLog.query.filter_by(subject=subj).first()
            if not c_log and i < len(high_risk_shipments):
                c_log = CommunicationLog(
                    shipment_id=high_risk_shipments[i].id,
                    recipient=f"{rec_name} <{rec_email}>",
                    channel="EMAIL",
                    subject=subj,
                    message_body=body,
                    sent_at=now - dt.timedelta(hours=i * 8)
                )
                db.session.add(c_log)

        db.session.commit()
        print(f"Communications seeded: {CommunicationLog.query.count()}")

        print("\nAll database tables successfully seeded with authentic, non-duplicate records!")

if __name__ == '__main__':
    seed_database()
