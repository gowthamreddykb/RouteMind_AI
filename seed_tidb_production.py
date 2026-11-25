"""
seed_tidb_production.py - Production Seeder for RouteMind AI TiDB Cloud Database
Populates 60+ realistic maritime consignments across all 9 lifecycle stages,
diverse destination regions, ML model scores, shipment exceptions, actions,
events, manager escalations, and communication logs.
"""
import os
import sys
import random
import datetime as dt

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
from src.models.model_score_model import ModelScore
from src.models.exception_model import ShipmentException
from src.models.exception_action_model import ExceptionAction
from src.models.escalation_model import ManagerEscalation
from src.models.communication_model import CommunicationLog


def seed_tidb():
    print("=" * 70)
    print("ROUTEMIND AI - PRODUCTION TIDB DATABASE SEEDER")
    print("=" * 70)

    app = create_app('development')
    with app.app_context():
        # Verify active database URI
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        print(f"Target Database: {db_uri.split('@')[-1] if '@' in db_uri else 'SQLite'}")

        # -------------------------------------------------------------
        # 1. Ensure Key Users Exist
        # -------------------------------------------------------------
        users = {u.username: u for u in User.query.all()}
        gowtham_user = users.get('gowtham')
        gowtham_k = users.get('gowtham_k')
        dispatcher_user = users.get('dispatcher')
        manager_user = users.get('manager')
        admin_user = users.get('admin')

        print(f"Found existing users: {[u.username for u in users.values()]}")

        # -------------------------------------------------------------
        # 2. Seed Rich Customers
        # -------------------------------------------------------------
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
            ("Atlas", "Maritime", "Corporate", "Los Angeles", "CA", "United States"),
            ("Kyoto", "Marine Supply", "Corporate", "Yokohama", "Kanagawa", "Japan"),
            ("Baltic", "Freight Alliance", "Corporate", "Gdansk", "Pomeranian", "Poland"),
            ("Mediterranean", "Logistics SA", "Corporate", "Valencia", "Valencia", "Spain"),
            ("Astra", "Pharma Global", "Corporate", "Basel", "Basel-City", "Switzerland"),
            ("Southern", "Cross Shipping", "Consumer", "Sydney", "NSW", "Australia")
        ]

        for fn, ln, seg, city, state, country in customers_data:
            c = Customer.query.filter_by(first_name=fn, last_name=ln).first()
            if not c:
                c = Customer(first_name=fn, last_name=ln, segment=seg, city=city, state=state, country=country)
                db.session.add(c)
        db.session.commit()
        all_customers = Customer.query.all()
        print(f"Customers active: {len(all_customers)}")

        # -------------------------------------------------------------
        # 3. Seed Products
        # -------------------------------------------------------------
        products_data = [
            ("Smart GPS Container Tracker", "Tracking & Telemetry", "Technology", 280.00),
            ("Industrial Marine Valve 4-Inch", "Marine Engineering", "Hardware", 450.00),
            ("Lithium Marine Auxiliary Battery", "Power Systems", "Electrical", 890.00),
            ("Cold-Chain Reefer Sensor Set", "Reefer Monitoring", "Electronics", 320.00),
            ("Heavy Duty Cargo Lashing Straps", "Deck Equipment", "Safety", 75.00),
            ("Marine AIS Class-A Transponder", "Navigation Equipment", "Avionics/Marine", 1250.00),
            ("Digital Fuel Flow Meter Sensor", "Engine Telemetry", "Instrumentation", 620.00),
            ("High-Pressure Bilge Pump 24V", "Pumping Systems", "Mechanical", 540.00),
            ("Hydrostatic Release Unit HRU", "Safety Systems", "Safety", 160.00),
            ("Acoustic Underwater Transducer", "Sonar Systems", "Electronics", 1850.00),
            ("Marine Engine Turbocharger Cartridge", "Propulsion Spares", "Mechanical", 2100.00),
            ("Anti-Fouling Hull Sonar Sensor", "Hull Telemetry", "Technology", 940.00)
        ]

        for pname, cat, dept, price in products_data:
            p = Product.query.filter_by(product_name=pname).first()
            if not p:
                p = Product(product_name=pname, category_name=cat, department_name=dept, product_price=price)
                db.session.add(p)
        db.session.commit()
        all_products = Product.query.all()
        print(f"Products active: {len(all_products)}")

        # -------------------------------------------------------------
        # 4. Generate 60+ Realistic Maritime Shipments
        # -------------------------------------------------------------
        # Target all 9 lifecycle statuses
        statuses = [
            "CREATED",
            "BOOKING_CONFIRMED",
            "READY_FOR_DISPATCH",
            "DISPATCHED",
            "IN_TRANSIT",
            "ARRIVED_AT_DESTINATION",
            "OUT_FOR_DELIVERY",
            "DELIVERED",
            "COMPLETED"
        ]

        regions_and_countries = [
            ("Western Europe", "Netherlands", "Europe"),
            ("Western Europe", "Germany", "Europe"),
            ("Western Europe", "France", "Europe"),
            ("Western Europe", "Belgium", "Europe"),
            ("Pacific Asia", "Singapore", "Pacific Asia"),
            ("Pacific Asia", "Japan", "Pacific Asia"),
            ("Pacific Asia", "South Korea", "Pacific Asia"),
            ("South Asia", "India", "Pacific Asia"),
            ("South Asia", "Sri Lanka", "Pacific Asia"),
            ("North America", "United States", "USCA"),
            ("North America", "Canada", "USCA"),
            ("Middle East", "United Arab Emirates", "Pacific Asia"),
            ("Middle East", "Saudi Arabia", "Pacific Asia"),
            ("Latin America", "Brazil", "LATAM"),
            ("Latin America", "Panama", "LATAM"),
            ("East of USA", "United States", "USCA"),
            ("Mediterranean", "Spain", "Europe"),
            ("Mediterranean", "Italy", "Europe"),
            ("Southeast Asia", "Malaysia", "Pacific Asia"),
            ("Southeast Asia", "Vietnam", "Pacific Asia")
        ]

        shipping_modes = [
            ("Standard Class", 4),
            ("Second Class", 2),
            ("First Class", 1),
            ("Same Day", 1)
        ]

        now = dt.datetime.now(dt.timezone.utc)
        random.seed(42)

        created_shipments = []
        # Create 60 diverse consignments with sequential numbers
        for i in range(1, 61):
            shp_num = f"SHP-{10500 + i}"
            existing = Shipment.query.filter_by(shipment_number=shp_num).first()
            if existing:
                created_shipments.append(existing)
                continue

            cust = random.choice(all_customers)
            prod = random.choice(all_products)
            mode, days = random.choice(shipping_modes)
            dest_reg, dest_country, market = random.choice(regions_and_countries)

            # Distribute lifecycle status
            if i <= 8:
                status = "CREATED"
            elif i <= 14:
                status = "BOOKING_CONFIRMED"
            elif i <= 20:
                status = "READY_FOR_DISPATCH"
            elif i <= 28:
                status = "DISPATCHED"
            elif i <= 44:
                status = "IN_TRANSIT"
            elif i <= 49:
                status = "ARRIVED_AT_DESTINATION"
            elif i <= 52:
                status = "OUT_FOR_DELIVERY"
            elif i <= 56:
                status = "DELIVERED"
            else:
                status = "COMPLETED"

            # Assign risk level and probabilities
            # Low: prob < 0.40, Med: 0.40 <= prob < 0.70, High/Critical: prob >= 0.70
            risk_roll = random.random()
            if risk_roll < 0.45:
                risk_level = "LOW"
                p1 = round(random.uniform(0.08, 0.35), 3)
                p2 = round(random.uniform(0.12, 0.38), 3)
                dock_clearance = "CLEAR_FOR_TRANSIT"
            elif risk_roll < 0.75:
                risk_level = "MEDIUM"
                p1 = round(random.uniform(0.38, 0.55), 3)
                p2 = round(random.uniform(0.42, 0.68), 3)
                dock_clearance = "CLEAR_FOR_TRANSIT" if random.random() > 0.4 else "DOCK_HOLD_INSPECTION"
            elif risk_roll < 0.90:
                risk_level = "HIGH"
                p1 = round(random.uniform(0.55, 0.82), 3)
                p2 = round(random.uniform(0.70, 0.88), 3)
                dock_clearance = random.choice(["DOCK_HOLD_INSPECTION", "CARRIER_EXPEDITE", "CUSTOMS_HOLD"])
            else:
                risk_level = "CRITICAL"
                p1 = round(random.uniform(0.72, 0.94), 3)
                p2 = round(random.uniform(0.85, 0.97), 3)
                dock_clearance = "CARRIER_EXPEDITE"

            # Assign to users: Gowtham (active user), Gowtham K, Dispatcher, or Unassigned
            assign_roll = i % 4
            if assign_roll == 0 and gowtham_user:
                assigned_id = gowtham_user.id
                assigned_name = gowtham_user.username
            elif assign_roll == 1 and gowtham_k:
                assigned_id = gowtham_k.id
                assigned_name = gowtham_k.username
            elif assign_roll == 2 and dispatcher_user:
                assigned_id = dispatcher_user.id
                assigned_name = dispatcher_user.username
            else:
                assigned_id = None
                assigned_name = None

            # Order date within the last 15 days
            order_time = now - dt.timedelta(days=random.randint(0, 14), hours=random.randint(1, 23))
            qty = random.randint(1, 6)
            sales = round(prod.product_price * qty, 2)

            shp = Shipment(
                shipment_number=shp_num,
                customer_id=cust.id,
                product_id=prod.id,
                order_date=order_time,
                scheduled_days=days,
                shipping_mode=mode,
                order_status=status,
                sales=sales,
                quantity=qty,
                product_price=prod.product_price,
                origin_region="US Center" if i % 2 == 0 else "East Coast",
                destination_region=dest_reg,
                destination_country=dest_country,
                market=market,
                order_creation_prob=p1,
                dispatch_prob=p2,
                risk_level=risk_level,
                dock_clearance_status=dock_clearance,
                assigned_to_id=assigned_id,
                assigned_to_name=assigned_name,
                created_by_id=gowtham_user.id if gowtham_user else 1,
                created_by_name=gowtham_user.username if gowtham_user else 'system'
            )
            db.session.add(shp)
            db.session.flush()
            created_shipments.append(shp)

            # Add Timeline Events
            e1 = ShipmentEvent(
                shipment_id=shp.id,
                event_type='ORDER_CREATED',
                notes=f"Order recorded via {mode} service line.",
                event_timestamp=order_time
            )
            events_to_add = [e1]

            if status not in ['CREATED', 'BOOKING_CONFIRMED']:
                e2 = ShipmentEvent(
                    shipment_id=shp.id,
                    event_type='DOCK_DISPATCHED',
                    warehouse_processing_time=round(random.uniform(1.2, 3.8), 1),
                    notes=f"Consignment cleared dock gate. Status: {dock_clearance}",
                    event_timestamp=order_time + dt.timedelta(hours=14)
                )
                events_to_add.append(e2)

            if status in ['IN_TRANSIT', 'ARRIVED_AT_DESTINATION', 'OUT_FOR_DELIVERY', 'DELIVERED', 'COMPLETED']:
                e3 = ShipmentEvent(
                    shipment_id=shp.id,
                    event_type='TRANSIT_UPDATE',
                    notes=f"Ocean passage logged heading to port of {dest_country}.",
                    event_timestamp=order_time + dt.timedelta(hours=36)
                )
                events_to_add.append(e3)

            db.session.add_all(events_to_add)

        db.session.commit()
        print(f"Total Shipments in database: {Shipment.query.count()}")

        # -------------------------------------------------------------
        # 5. Populate Model Scores (model_scores table)
        # -------------------------------------------------------------
        # For active shipments (not DELIVERED or COMPLETED), generate model_scores
        active_shipments = Shipment.query.filter(
            Shipment.order_status.notin_(['DELIVERED', 'COMPLETED'])
        ).all()

        new_scores = 0
        for s in active_shipments:
            existing_score = ModelScore.query.filter_by(shipment_id=s.id).first()
            if not existing_score:
                # Stage 1 Score
                prob1 = float(s.order_creation_prob or 0.25)
                mscore1 = ModelScore(
                    shipment_id=s.id,
                    prediction_stage='ORDER_CREATION',
                    predicted_probability=prob1,
                    predicted_class=1 if prob1 >= 0.40 else 0,
                    risk_level=s.risk_level,
                    scoring_timestamp=s.order_date + dt.timedelta(minutes=5)
                )
                # Stage 2 Score (Dispatch stage)
                prob2 = float(s.dispatch_prob or 0.35)
                mscore2 = ModelScore(
                    shipment_id=s.id,
                    prediction_stage='DOCK_DISPATCH',
                    predicted_probability=prob2,
                    predicted_class=1 if prob2 >= 0.39 else 0,
                    risk_level=s.risk_level,
                    scoring_timestamp=s.order_date + dt.timedelta(hours=12)
                )
                db.session.add_all([mscore1, mscore2])
                new_scores += 2

        db.session.commit()
        print(f"Model Scores active: {ModelScore.query.count()} (+{new_scores} new)")

        # -------------------------------------------------------------
        # 6. Populate Diverse Shipment Exceptions
        # -------------------------------------------------------------
        exc_scenarios = [
            ("Port Congestion & Berthing Hold", "CRITICAL", "OPEN", "Terminal berth delay exceeding 48h at destination gateway."),
            ("Customs Documentation Hold", "HIGH", "INVESTIGATING", "Missing commercial invoice and HS code discrepancy flagged."),
            ("Carrier Capacity Reroute", "HIGH", "OPEN", "Feeder vessel bypassed port; alternative feeder assignment required."),
            ("Feeder Vessel Delay", "MEDIUM", "INVESTIGATING", "Adverse weather in transit corridor adding 24-36h linehaul delay."),
            ("Reefer Temperature Variance", "CRITICAL", "OPEN", "Reefer container reported +2.4C variance against cold-chain SLA."),
            ("Terminal Offload Queue", "MEDIUM", "RESOLVED", "Container transferred to priority inland intermodal terminal."),
            ("Container Seal Inspection", "LOW", "RESOLVED", "Secondary port authority security inspection complete.")
        ]

        # Attach exceptions to elevated, high, and critical risk shipments
        candidate_shipments = Shipment.query.filter(
            Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'MEDIUM'])
        ).all()

        added_exceptions = 0
        officers = [
            gowtham_user.username if gowtham_user else "gowtham",
            "Priya Sharma",
            "Arun Kumar",
            "Alexander Wright",
            dispatcher_user.username if dispatcher_user else "dispatcher"
        ]

        for idx, shp in enumerate(candidate_shipments[:16]):
            existing_exc = ShipmentException.query.filter_by(shipment_id=shp.id).first()
            if not existing_exc:
                etype, sev, stat, desc = exc_scenarios[idx % len(exc_scenarios)]
                assigned_officer = officers[idx % len(officers)]
                exc = ShipmentException(
                    shipment_id=shp.id,
                    exception_type=etype,
                    severity=sev,
                    status=stat,
                    assigned_to=assigned_officer,
                    created_at=now - dt.timedelta(hours=idx * 4 + 2)
                )
                db.session.add(exc)
                db.session.flush()

                action = ExceptionAction(
                    exception_id=exc.id,
                    action_taken=f"Operational Response: {desc} Escalated priority queue.",
                    taken_by=assigned_officer,
                    action_timestamp=now - dt.timedelta(hours=idx * 2)
                )
                db.session.add(action)
                added_exceptions += 1

        db.session.commit()
        print(f"Shipment Exceptions active: {ShipmentException.query.count()} (+{added_exceptions} new)")

        # -------------------------------------------------------------
        # 7. Seed Manager Escalations
        # -------------------------------------------------------------
        high_risk_for_escalation = Shipment.query.filter(
            Shipment.risk_level.in_(['HIGH', 'CRITICAL'])
        ).all()

        added_escalations = 0
        for i, shp in enumerate(high_risk_for_escalation[:6]):
            existing_esc = ManagerEscalation.query.filter_by(shipment_id=shp.id).first()
            if not existing_esc:
                esc = ManagerEscalation(
                    shipment_id=shp.id,
                    priority=shp.risk_level,
                    reason=f"Predicted SLA Breach: Transit delay on {shp.shipping_mode} consignment to {shp.destination_region}.",
                    dispatcher_remarks="Autonomous alert triggered by RouteMind AI Dual-Stage ML model pipeline.",
                    risk_score=float(shp.dispatch_prob or 0.85),
                    escalated_by_id=gowtham_user.id if gowtham_user else 1,
                    escalated_by_name=gowtham_user.username if gowtham_user else "gowtham",
                    status="UNDER_REVIEW" if i % 2 == 0 else "PENDING",
                    assigned_to_id=manager_user.id if manager_user else None,
                    assigned_to_name=manager_user.username if manager_user else "manager",
                    created_at=now - dt.timedelta(hours=i * 6 + 1)
                )
                db.session.add(esc)
                added_escalations += 1

        db.session.commit()
        print(f"Manager Escalations active: {ManagerEscalation.query.count()} (+{added_escalations} new)")

        # -------------------------------------------------------------
        # 8. Seed Communication Logs
        # -------------------------------------------------------------
        comms_spec = [
            ("Meridian Imports", "logistics@meridianimports.com", "[RouteMind Operational Notice] Delivery Commitment Notice - High Priority", "Anticipated port congestion notice dispatched with updated ETA window."),
            ("Pacific Trade Co", "supplychain@pacifictrade.co", "[RouteMind Update] Carrier Handover Priority Linehaul Scheduled", "Express feeder vessel booking confirmed to prevent SLA breach."),
            ("Nordic Cargo Ltd", "dispatch@nordiccargo.nl", "[RouteMind Notice] Dock Clearance Documentation Verified", "Quay inspection clearance complete. Consignment released to linehaul corridor."),
            ("Atlas Maritime", "operations@atlasmaritime.com", "[RouteMind Alert] Customs Pre-Clearance Submitted", "Automated digital customs clearance manifest generated and submitted to port customs."),
            ("Kyoto Marine Supply", "logistics@kyotomarine.jp", "[RouteMind Status] Reefer Temperature Restabilized", "Telemetry confirms container temperature returned within standard cold-chain parameters.")
        ]

        added_comms = 0
        for i, (rec_name, rec_email, subj, body) in enumerate(comms_spec):
            existing_comm = CommunicationLog.query.filter_by(subject=subj).first()
            if not existing_comm and i < len(high_risk_for_escalation):
                c_log = CommunicationLog(
                    shipment_id=high_risk_for_escalation[i].id,
                    recipient=f"{rec_name} <{rec_email}>",
                    channel="EMAIL",
                    subject=subj,
                    message_body=body,
                    sent_at=now - dt.timedelta(hours=i * 5 + 3)
                )
                db.session.add(c_log)
                added_comms += 1

        db.session.commit()
        print(f"Communication Logs active: {CommunicationLog.query.count()} (+{added_comms} new)")

        print("=" * 70)
        print("PRODUCTION TIDB SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 70)


if __name__ == '__main__':
    seed_tidb()
