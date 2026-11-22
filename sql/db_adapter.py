"""
sql/db_adapter.py - Complete Enterprise Database Adapter for RouteMind AI
Author: Gowtham K
Supports MySQL 8.0+ and SQLite (Zero-Config local embedded development).
Implements complete CRUD for the 12 active RouteMind AI database tables.
"""

import os
import json
import sqlite3
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseAdapter:
    def __init__(self, db_path: Optional[str] = None):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if db_path is None:
            db_path = os.path.join(self.project_root, "data", "routemind_control_tower.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.use_mysql = bool(os.environ.get("MYSQL_HOST") or os.environ.get("DB_HOST"))
        self._init_database()

    def get_connection(self):
        """Returns a connection with Row dictionary mapping."""
        if self.use_mysql:
            import pymysql
            return pymysql.connect(
                host=os.environ.get("MYSQL_HOST", "localhost"),
                user=os.environ.get("MYSQL_USER", "root"),
                password=os.environ.get("MYSQL_PASSWORD", ""),
                database=os.environ.get("MYSQL_DATABASE", "routemind_db"),
                port=int(os.environ.get("MYSQL_PORT", 3306)),
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn

    def _init_database(self):
        """Initializes database schema and seed data."""
        if not self.use_mysql:
            self._init_sqlite()

    def _init_sqlite(self):
        """Creates the 12-table SQLite database if not existing."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. USERS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'DISPATCHER',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 2. CUSTOMERS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_customer_id TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL,
            customer_segment TEXT NOT NULL DEFAULT 'Consumer',
            customer_region TEXT,
            customer_country TEXT,
            priority_level TEXT NOT NULL DEFAULT 'NORMAL',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 3. PRODUCTS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_product_id TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            category_id INTEGER,
            category_name TEXT NOT NULL,
            department_name TEXT NOT NULL DEFAULT 'Apparel',
            product_price REAL NOT NULL DEFAULT 0.00,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 4. ORDERS_SHIPMENTS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders_shipments (
            shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_order_id TEXT NOT NULL,
            external_order_item_id TEXT,
            customer_id INTEGER,
            product_id INTEGER,
            order_date TEXT NOT NULL,
            scheduled_shipping_days INTEGER NOT NULL DEFAULT 2,
            scheduled_delivery_date TEXT,
            shipping_mode TEXT NOT NULL DEFAULT 'Standard Class',
            market TEXT NOT NULL DEFAULT 'Europe',
            order_region TEXT NOT NULL DEFAULT 'Western Europe',
            order_country TEXT,
            order_city TEXT,
            order_state TEXT,
            order_zipcode TEXT,
            item_quantity INTEGER NOT NULL DEFAULT 1,
            product_price REAL NOT NULL DEFAULT 0.00,
            discount_rate REAL NOT NULL DEFAULT 0.0000,
            sales_amount REAL NOT NULL DEFAULT 0.00,
            order_value REAL NOT NULL DEFAULT 0.00,
            payment_type TEXT NOT NULL DEFAULT 'DEBIT',
            carrier_name TEXT,
            shipment_status TEXT NOT NULL DEFAULT 'PENDING',
            model_01_late_probability REAL,
            model_01_risk_flag INTEGER,
            model_02_late_probability REAL,
            model_02_risk_flag INTEGER,
            order_to_ship_time REAL,
            predicted_real_days REAL,
            predicted_delay_days REAL,
            risk_level TEXT NOT NULL DEFAULT 'LOW',
            sla_status TEXT,
            scored_at TEXT,
            actual_shipping_date TEXT,
            actual_delivery_date TEXT,
            actual_delivery_outcome TEXT NOT NULL DEFAULT 'UNKNOWN',
            actual_delay_reason TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 5. SHIPMENT_EVENTS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipment_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER NOT NULL,
            recorded_by INTEGER,
            event_type TEXT NOT NULL,
            event_description TEXT,
            event_location TEXT,
            event_time TEXT NOT NULL DEFAULT (datetime('now')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 6. RISK_FACTORS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_factors (
            factor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER NOT NULL,
            model_stage TEXT NOT NULL DEFAULT 'order_creation',
            feature_name TEXT NOT NULL,
            feature_value TEXT,
            contribution_value REAL NOT NULL DEFAULT 0.0,
            contribution_direction TEXT NOT NULL,
            explanation TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 7. EXCEPTION_CASES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exception_cases (
            exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER NOT NULL,
            assigned_to INTEGER,
            created_by INTEGER,
            exception_type TEXT NOT NULL DEFAULT 'LATE_DELIVERY_RISK',
            severity TEXT NOT NULL DEFAULT 'HIGH',
            priority TEXT NOT NULL DEFAULT 'HIGH',
            exception_description TEXT,
            suspected_cause TEXT,
            actual_root_cause TEXT,
            resolution_summary TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN',
            opened_at TEXT NOT NULL DEFAULT (datetime('now')),
            resolved_at TEXT,
            closed_at TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 8. EXCEPTION_COMMENTS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exception_comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_id INTEGER NOT NULL,
            user_id INTEGER,
            comment_text TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 9. EXCEPTION_ACTIONS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exception_actions (
            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_id INTEGER NOT NULL,
            generated_by TEXT NOT NULL DEFAULT 'AI',
            action_title TEXT NOT NULL,
            action_description TEXT,
            assumptions TEXT,
            feasibility_status TEXT NOT NULL DEFAULT 'VERIFIED',
            approval_status TEXT NOT NULL DEFAULT 'PENDING',
            approved_by INTEGER,
            approved_at TEXT,
            execution_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
            outcome_notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 10. COMMUNICATIONS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS communications (
            communication_id INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_id INTEGER NOT NULL,
            action_id INTEGER,
            audience TEXT NOT NULL DEFAULT 'CUSTOMER',
            communication_type TEXT NOT NULL DEFAULT 'CUSTOMER_UPDATE',
            subject TEXT NOT NULL,
            generated_draft TEXT NOT NULL,
            final_text TEXT,
            ai_model_name TEXT DEFAULT 'RouteMind-GenAI-v1',
            prompt_version TEXT NOT NULL DEFAULT 'v1.0.0',
            approval_status TEXT NOT NULL DEFAULT 'PENDING',
            created_by INTEGER,
            approved_by INTEGER,
            approved_at TEXT,
            delivery_status TEXT NOT NULL DEFAULT 'DRAFT',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 11. AUDIT_LOGS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id INTEGER,
            old_value TEXT,
            new_value TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

        # 12. REFERENCE_DATA
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reference_data (
            reference_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_type TEXT NOT NULL,
            reference_code TEXT NOT NULL,
            reference_value TEXT NOT NULL,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(reference_type, reference_code)
        )
        """)

        # 13. MODEL_SCORES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_scores (
            score_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT,
            model_id TEXT,
            prediction_stage TEXT,
            late_delivery_probability REAL,
            predicted_class INTEGER,
            selected_threshold REAL,
            risk_category TEXT,
            alert_level TEXT,
            scored_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Migration check: ensure prompt_version column exists on communications & communication_logs
        try:
            cursor.execute("PRAGMA table_info(communications)")
            comm_cols = [c[1] for c in cursor.fetchall()]
            if 'prompt_version' not in comm_cols and comm_cols:
                cursor.execute("ALTER TABLE communications ADD COLUMN prompt_version TEXT NOT NULL DEFAULT 'v1.0.0'")
            cursor.execute("PRAGMA table_info(communication_logs)")
            log_cols = [c[1] for c in cursor.fetchall()]
            if 'prompt_version' not in log_cols and log_cols:
                cursor.execute("ALTER TABLE communication_logs ADD COLUMN prompt_version TEXT NOT NULL DEFAULT 'v1.0.0'")
        except Exception:
            pass

        conn.commit()

        # Seed initial data if users table is empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            self._seed_initial_data(cursor)
            conn.commit()

        conn.close()

    def _seed_initial_data(self, cursor):
        """Seeds default users and references into SQLite."""
        admin_hash = generate_password_hash("admin123")
        disp_hash = generate_password_hash("dispatch123")
        mgr_hash = generate_password_hash("manager123")

        cursor.executemany("""
            INSERT OR IGNORE INTO users (user_id, full_name, email, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (1, "Gowtham K (Admin)", "admin@routemind.ai", admin_hash, "ADMIN", 1),
            (2, "Alex Turner (Dispatcher)", "dispatcher@routemind.ai", disp_hash, "DISPATCHER", 1),
            (3, "Sarah Jenkins (Ops Manager)", "manager@routemind.ai", mgr_hash, "MANAGER", 1)
        ])

        cursor.executemany("""
            INSERT OR IGNORE INTO reference_data (reference_type, reference_code, reference_value, description)
            VALUES (?, ?, ?, ?)
        """, [
            ("SHIPPING_MODE", "STANDARD", "Standard Class", "4-Day standard surface linehaul delivery SLA"),
            ("SHIPPING_MODE", "SECOND", "Second Class", "2-Day priority expedited ground service SLA"),
            ("SHIPPING_MODE", "FIRST", "First Class", "1-Day air express expedited delivery SLA"),
            ("SHIPPING_MODE", "SAME_DAY", "Same Day", "Zero-buffer same-day express delivery SLA"),
            ("CUSTOMER_SEGMENT", "CONSUMER", "Consumer", "Individual retail residential consumer accounts"),
            ("CUSTOMER_SEGMENT", "CORPORATE", "Corporate", "B2B commercial client accounts"),
            ("CUSTOMER_SEGMENT", "HOME_OFFICE", "Home Office", "Small business and remote home office accounts"),
            ("MARKET", "EUROPE", "Europe", "European Union and Western/Eastern Europe territory"),
            ("MARKET", "LATAM", "LATAM", "Latin America and Caribbean regional territory"),
            ("MARKET", "PACIFIC_ASIA", "Pacific Asia", "Asia-Pacific and Indian subcontinent territory"),
            ("MARKET", "USCA", "USCA", "United States and Canada domestic trade corridor"),
            ("MARKET", "AFRICA", "Africa", "African continent regional trade territory"),
            ("PAYMENT_TYPE", "DEBIT", "DEBIT", "Electronic bank debit transfer at checkout"),
            ("PAYMENT_TYPE", "TRANSFER", "TRANSFER", "Automated Clearing House (ACH) wire transfer"),
            ("PAYMENT_TYPE", "PAYMENT", "PAYMENT", "Direct credit card merchant settlement"),
            ("PAYMENT_TYPE", "CASH", "CASH", "Cash on delivery payment commitment")
        ])

        cursor.executemany("""
            INSERT OR IGNORE INTO customers (customer_id, external_customer_id, customer_name, customer_segment, customer_region, customer_country, priority_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (1, "CUST-19492", "Irene Luna", "Consumer", "South Asia", "India", "VIP"),
            (2, "CUST-20511", "Acme Logistics Europe", "Corporate", "Western Europe", "Germany", "HIGH"),
            (3, "CUST-18400", "Pacific Apex Trading", "Home Office", "Pacific Asia", "Japan", "NORMAL")
        ])

        cursor.executemany("""
            INSERT OR IGNORE INTO products (product_id, external_product_id, product_name, category_id, category_name, department_name, product_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (1, "PROD-1360", "Smart watch with Fitness Tracker", 73, "Sporting Goods", "Fitness", 327.75),
            (2, "PROD-1014", "Perfect Fitness Rip Deck", 45, "Cardio Equipment", "Fitness", 59.99),
            (3, "PROD-1025", "Nike Men Dri-FIT Training Tee", 18, "Apparel", "Apparel", 35.00)
        ])

        cursor.execute("""
            INSERT OR IGNORE INTO orders_shipments (
                shipment_id, external_order_id, external_order_item_id, customer_id, product_id,
                order_date, scheduled_shipping_days, scheduled_delivery_date, shipping_mode, market, order_region,
                order_country, order_city, order_state, order_zipcode, item_quantity, product_price,
                discount_rate, sales_amount, order_value, payment_type, carrier_name, shipment_status,
                model_01_late_probability, model_01_risk_flag, model_02_late_probability, model_02_risk_flag,
                order_to_ship_time, predicted_real_days, predicted_delay_days, risk_level, sla_status, scored_at
            )
            VALUES (
                1, 'ORD-75939', 'ITEM-179254', 1, 1,
                '2026-11-13 12:27:00', 4, '2026-11-17', 'Standard Class', 'Pacific Asia', 'South Asia',
                'India', 'Bikaner', 'Rajasthan', '334001', 1, 327.75,
                0.0500, 311.36, 311.36, 'TRANSFER', 'BlueDart Ground', 'DISPATCHED',
                0.7850, 1, 0.9716, 1,
                5.00, 5.00, 1.00, 'HIGH', 'MINOR DELAY (+1 Day Late)', datetime('now')
            )
        """)

    # =========================================================================
    # USER AUTHENTICATION & MANAGEMENT (FR-01)
    # =========================================================================
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email.strip().lower(),))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_email(email)
        if not user:
            return None
        if check_password_hash(user["password_hash"], password):
            return user
        return None

    def list_users(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, full_name, email, role, is_active, created_at FROM users ORDER BY user_id ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    # =========================================================================
    # SHIPMENT MANAGEMENT & EXPLORER (FR-03)
    # =========================================================================
    def get_shipments(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
        SELECT s.*, c.customer_name, c.customer_segment, c.priority_level, p.product_name, p.department_name, p.category_name
        FROM orders_shipments s
        LEFT JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN products p ON s.product_id = p.product_id
        WHERE 1=1
        """
        params = []
        if filters:
            if filters.get("risk_level"):
                query += " AND s.risk_level = ?"
                params.append(filters["risk_level"])
            if filters.get("shipping_mode"):
                query += " AND s.shipping_mode = ?"
                params.append(filters["shipping_mode"])
            if filters.get("order_region"):
                query += " AND s.order_region = ?"
                params.append(filters["order_region"])
            if filters.get("shipment_status"):
                query += " AND s.shipment_status = ?"
                params.append(filters["shipment_status"])
            if filters.get("search"):
                search_term = f"%{filters['search']}%"
                query += " AND (s.external_order_id LIKE ? OR c.customer_name LIKE ? OR p.product_name LIKE ?)"
                params.extend([search_term, search_term, search_term])

        query += " ORDER BY s.shipment_id DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_shipment_by_id(self, shipment_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, c.customer_name, c.customer_segment, c.priority_level, p.product_name, p.department_name, p.category_name
            FROM orders_shipments s
            LEFT JOIN customers c ON s.customer_id = c.customer_id
            LEFT JOIN products p ON s.product_id = p.product_id
            WHERE s.shipment_id = ?
        """, (shipment_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def insert_shipment(self, data: Dict[str, Any]) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        order_date = data.get("order_date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO orders_shipments (
                external_order_id, external_order_item_id, customer_id, product_id,
                order_date, scheduled_shipping_days, scheduled_delivery_date,
                shipping_mode, market, order_region, order_country, order_city, order_state, order_zipcode,
                item_quantity, product_price, discount_rate, sales_amount, order_value,
                payment_type, carrier_name, shipment_status,
                model_01_late_probability, model_01_risk_flag,
                model_02_late_probability, model_02_risk_flag,
                order_to_ship_time, predicted_real_days, predicted_delay_days,
                risk_level, sla_status, scored_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(data.get("external_order_id", f"ORD-{int(datetime.now().timestamp())}")),
            data.get("external_order_item_id"),
            data.get("customer_id", 1),
            data.get("product_id", 1),
            order_date,
            int(data.get("scheduled_shipping_days", 2)),
            data.get("scheduled_delivery_date"),
            data.get("shipping_mode", "Standard Class"),
            data.get("market", "Europe"),
            data.get("order_region", "Western Europe"),
            data.get("order_country", "United States"),
            data.get("order_city"),
            data.get("order_state"),
            data.get("order_zipcode"),
            int(data.get("item_quantity", 1)),
            float(data.get("product_price", 0.0)),
            float(data.get("discount_rate", 0.0)),
            float(data.get("sales_amount", 0.0)),
            float(data.get("order_value", data.get("sales_amount", 0.0))),
            data.get("payment_type", "DEBIT"),
            data.get("carrier_name", "Standard Ground"),
            data.get("shipment_status", "PENDING"),
            data.get("model_01_late_probability"),
            data.get("model_01_risk_flag"),
            data.get("model_02_late_probability"),
            data.get("model_02_risk_flag"),
            data.get("order_to_ship_time"),
            data.get("predicted_real_days"),
            data.get("predicted_delay_days"),
            data.get("risk_level", "LOW"),
            data.get("sla_status"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        shipment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return shipment_id

    # =========================================================================
    # EXPLAINABILITY & RISK FACTORS (FR-06)
    # =========================================================================
    def record_risk_factors(self, shipment_id: int, factors: List[Dict[str, Any]]):
        conn = self.get_connection()
        cursor = conn.cursor()
        for f in factors:
            cursor.execute("""
                INSERT INTO risk_factors (
                    shipment_id, model_stage, feature_name, feature_value,
                    contribution_value, contribution_direction, explanation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                shipment_id,
                f.get("model_stage", "control_tower"),
                f.get("feature_name", "Unknown"),
                str(f.get("feature_value", "")),
                float(f.get("contribution_value", 0.0)),
                f.get("contribution_direction", "INCREASES_RISK"),
                f.get("explanation", "")
            ))
        conn.commit()
        conn.close()

    def get_risk_factors(self, shipment_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM risk_factors WHERE shipment_id = ? ORDER BY abs(contribution_value) DESC", (shipment_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def record_shipment_event(self, event_data: dict) -> int:
        """Records a live shipment tracking event into shipment_events."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO shipment_events (
                shipment_id, recorded_by, event_type, event_description, event_location, event_time
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            event_data.get("shipment_id", 1),
            event_data.get("recorded_by", 1),
            str(event_data.get("event_type", "LIVE_STREAM_EVENT")),
            str(event_data.get("recommended_action") or event_data.get("alert_level", "NORMAL")),
            str(event_data.get("Order Region", "Global Network Hub")),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id

    def record_prediction(self, data: dict) -> int:
        """Records a model prediction score into model_scores."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO model_scores (
                shipment_id, model_id, prediction_stage, late_delivery_probability,
                predicted_class, selected_threshold, risk_category, alert_level
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(data.get("shipment_id", "UNKNOWN")),
            str(data.get("model_id", "v1.0.0")),
            str(data.get("prediction_stage", "order_creation")),
            float(data.get("late_delivery_probability", 0.0)),
            int(data.get("predicted_class", 0)),
            float(data.get("selected_threshold", 0.5)),
            str(data.get("risk_category", "Low Risk")),
            str(data.get("alert_level", "NORMAL"))
        ))
        last_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return last_id

    def log_communication(self, comm_data: Dict[str, Any]) -> int:
        """Logs a customer or internal operational communication draft/event with prompt versioning."""
        conn = self.get_connection()
        cursor = conn.cursor()
        prompt_version = comm_data.get('prompt_version', 'v1.0.0')

        if self.use_sqlite:
            cursor.execute("""
                INSERT INTO communications (
                    exception_id, action_id, audience, communication_type,
                    subject, generated_draft, final_text, ai_model_name,
                    prompt_version, approval_status, created_by, approved_by,
                    delivery_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comm_data.get('exception_id', 1),
                comm_data.get('action_id'),
                comm_data.get('audience', 'CUSTOMER'),
                comm_data.get('communication_type', 'CUSTOMER_UPDATE'),
                comm_data.get('subject', 'Logistics Exception Notice'),
                comm_data.get('generated_draft', comm_data.get('body', '')),
                comm_data.get('final_text'),
                comm_data.get('ai_model_name', 'RouteMind-GenAI-v1'),
                prompt_version,
                comm_data.get('approval_status', 'PENDING'),
                comm_data.get('created_by'),
                comm_data.get('approved_by'),
                comm_data.get('delivery_status', 'DRAFT')
            ))
            comm_id = cursor.lastrowid
        else:
            cursor.execute("""
                INSERT INTO communications (
                    exception_id, action_id, audience, communication_type,
                    subject, generated_draft, final_text, ai_model_name,
                    prompt_version, approval_status, created_by, approved_by,
                    delivery_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                comm_data.get('exception_id', 1),
                comm_data.get('action_id'),
                comm_data.get('audience', 'CUSTOMER'),
                comm_data.get('communication_type', 'CUSTOMER_UPDATE'),
                comm_data.get('subject', 'Logistics Exception Notice'),
                comm_data.get('generated_draft', comm_data.get('body', '')),
                comm_data.get('final_text'),
                comm_data.get('ai_model_name', 'RouteMind-GenAI-v1'),
                prompt_version,
                comm_data.get('approval_status', 'PENDING'),
                comm_data.get('created_by'),
                comm_data.get('approved_by'),
                comm_data.get('delivery_status', 'DRAFT')
            ))
            comm_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return comm_id

    def get_recent_scores(self, limit: int = 10) -> list:
        """Fetches the latest scored predictions directly from model_scores or orders_shipments."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_scores ORDER BY score_id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        if not rows:
            cursor.execute("""
                SELECT shipment_id, external_order_id, shipping_mode, order_region,
                       model_01_late_probability, model_02_late_probability,
                       predicted_real_days, predicted_delay_days, risk_level, sla_status, scored_at
                FROM orders_shipments
                ORDER BY shipment_id DESC LIMIT ?
            """, (limit,))
            rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    # =========================================================================
    # DASHBOARD KPI METRICS (FR-12)
    # =========================================================================
    def get_dashboard_stats(self) -> Dict[str, Any]:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM orders_shipments")
        total_shipments = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders_shipments WHERE risk_level = 'HIGH'")
        high_risk_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders_shipments WHERE risk_level = 'MODERATE'")
        mod_risk_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders_shipments WHERE risk_level = 'LOW'")
        low_risk_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM exception_cases WHERE status IN ('OPEN', 'ASSIGNED', 'IN_PROGRESS')")
        open_exceptions = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(predicted_delay_days) FROM orders_shipments WHERE predicted_delay_days > 0")
        avg_delay = cursor.fetchone()[0] or 0.0

        conn.close()
        return {
            "total_shipments": total_shipments,
            "high_risk_count": high_risk_count,
            "moderate_risk_count": mod_risk_count,
            "low_risk_count": low_risk_count,
            "open_exceptions": open_exceptions,
            "avg_delay_days": round(float(avg_delay), 2)
        }
