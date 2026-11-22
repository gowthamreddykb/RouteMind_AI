# RouteMind AI – Comprehensive Database & ORM Integration Audit

**System Name:** RouteMind AI – Predictive Maritime Shipment Operations & Exception Management  
**Audit Date:** 18 November 2026  
**Auditor:** Database Administrator & Backend Verification Engineer  
**Database Engines Tested:** MySQL 8.0+ (PyMySQL engine) / SQLite 3 (`instance/routemind.db`)  
**ORM Framework:** SQLAlchemy 2.0+ with Flask-SQLAlchemy  

---

## 1. Executive Summary

A comprehensive database audit was performed to verify relational integrity, column specifications, foreign key constraints, indexation, data seed volumes, and complete CRUD operations across all tables supporting the RouteMind AI platform.

All tables strictly mirror the enterprise schema specification. All foreign key constraints are enforced, nullability rules are validated, and maritime operational attributes are indexed for high-performance control tower queries.

---

## 2. Table-by-Table Architectural Audit

### Table 1: `users`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Unique Constraints:** `username` (`VARCHAR(80)`), `email` (`VARCHAR(120)`)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `username` (`VARCHAR(80)`, NOT NULL, Indexed, Unique)
  - `email` (`VARCHAR(120)`, NOT NULL, Indexed, Unique)
  - `password_hash` (`VARCHAR(255)`, NOT NULL)
  - `full_name` (`VARCHAR(120)`, NULL)
  - `role` (`VARCHAR(50)`, NOT NULL, Default: `'Dispatcher'`)
  - `is_active` (`BOOLEAN`, NOT NULL, Default: `True`)
  - `created_at` (`DATETIME`, Default: UTC Timestamp)
- **Relationships:**
  - One-to-Many with `audit_logs` (`user_id`)
- **Seed Record Count:** 4 verified active accounts (`admin`, `manager`, `dispatcher`, `dispatcher1`)
- **CRUD Operations Tested:** Create new user, Read by username/id, Update role/password/name, Toggle `is_active` with last-admin guard.
- **Audit Outcome:** **PASS**

---

### Table 2: `customers`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `name` (`VARCHAR(120)`, NOT NULL, Indexed)
  - `segment` (`VARCHAR(50)`, Default: `'Enterprise'`)
  - `country` (`VARCHAR(50)`, NULL)
  - `city` (`VARCHAR(50)`, NULL)
  - `created_at` (`DATETIME`, Default: UTC Timestamp)
- **Relationships:**
  - One-to-Many with `shipments` (`customer_id`)
- **Seed Record Count:** 5 enterprise cargo clients (`Meridian Imports`, `Pacific Maritime Ltd`, `Bavarian Automotives`, `Nordic Timber`, `Apex Electronics`)
- **CRUD Operations Tested:** Read profiles, Query by customer ID, Join with shipments.
- **Audit Outcome:** **PASS**

---

### Table 3: `products`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `name` (`VARCHAR(150)`, NOT NULL, Indexed)
  - `category` (`VARCHAR(100)`, NULL)
  - `price` (`FLOAT`, NOT NULL, Default: `0.0`)
  - `created_at` (`DATETIME`, Default: UTC Timestamp)
- **Relationships:**
  - One-to-Many with `shipments` (`product_id`)
- **Seed Record Count:** 5 categorized maritime cargo commodities
- **CRUD Operations Tested:** Read product catalog, price verification.
- **Audit Outcome:** **PASS**

---

### Table 4: `shipments`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Unique Constraints:** `shipment_number` (`VARCHAR(50)`)
- **Foreign Keys:**
  - `customer_id` $\rightarrow$ `customers.id` (Nullable)
  - `product_id` $\rightarrow$ `products.id` (Nullable)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `shipment_number` (`VARCHAR(50)`, NOT NULL, Indexed, Unique)
  - `customer_id` (`INTEGER`, NULL)
  - `product_id` (`INTEGER`, NULL)
  - `shipping_mode` (`VARCHAR(50)`, Default: `'Maritime'`)
  - `origin_region` (`VARCHAR(50)`, NULL)
  - `destination_region` (`VARCHAR(50)`, NULL)
  - `customer_country` (`VARCHAR(50)`, NULL)
  - `customer_city` (`VARCHAR(50)`, NULL)
  - `days_scheduled` (`FLOAT`, NOT NULL, Default: `4.0`)
  - `days_real` (`FLOAT`, NULL)
  - `sales_per_customer` (`FLOAT`, Default: `0.0`)
  - `order_item_quantity` (`INTEGER`, Default: `1`)
  - `order_item_discount_rate` (`FLOAT`, Default: `0.0`)
  - `product_price` (`FLOAT`, Default: `0.0`)
  - `customer_segment` (`VARCHAR(50)`, NULL)
  - `warehouse_processing_time_days` (`FLOAT`, Default: `1.0`)
  - `carrier_turnaround_time_hours` (`FLOAT`, Default: `12.0`)
  - `port_congestion_delay_hours` (`FLOAT`, Default: `0.0`)
  - `port_congestion_index` (`FLOAT`, Default: `0.0`)
  - `weather_delay_risk_score` (`FLOAT`, Default: `0.0`)
  - `shipping_delay_risk_score` (`FLOAT`, Default: `0.0`)
  - `lane_historical_delay_rate` (`FLOAT`, Default: `0.0`)
  - `customer_risk_profile` (`FLOAT`, Default: `0.0`)
  - `predicted_late` (`BOOLEAN`, Default: `False`)
  - `prediction_stage` (`VARCHAR(50)`, Default: `'STAGE_1_ORDER_CREATION'`)
  - `prediction_probability` (`FLOAT`, Default: `0.0`)
  - `risk_level` (`VARCHAR(20)`, Default: `'LOW'`)
  - `predicted_delay_hours` (`FLOAT`, Default: `0.0`)
  - `shipment_status` (`VARCHAR(50)`, Default: `'IN_TRANSIT'`)
  - `vessel_name` (`VARCHAR(100)`, NULL, Indexed)
  - `container_number` (`VARCHAR(50)`, NULL, Indexed)
  - `container_type` (`VARCHAR(50)`, NULL)
  - `origin_port` (`VARCHAR(100)`, NULL, Indexed)
  - `destination_port` (`VARCHAR(100)`, NULL, Indexed)
  - `planned_departure` (`DATETIME`, NULL)
  - `expected_arrival` (`DATETIME`, NULL)
  - `actual_arrival` (`DATETIME`, NULL)
  - `order_id_code` (`VARCHAR(50)`, NULL, Indexed)
  - `created_at` (`DATETIME`, Default: UTC Timestamp)
- **Relationships:**
  - One-to-Many with `shipment_events` (`shipment_id`)
  - One-to-Many with `exceptions` (`shipment_id`)
  - One-to-Many with `model_scores` (`shipment_id`)
  - One-to-Many with `communication_logs` (`shipment_id`)
- **Seed Record Count:** 13 fully populated maritime container consignments
- **CRUD Operations Tested:** Create shipment via intake form, Paginate with complex filters, Read details by number, Update fields via edit form, Update risk scores via predictive inference.
- **Audit Outcome:** **PASS**

---

### Table 5: `shipment_events`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Foreign Keys:**
  - `shipment_id` $\rightarrow$ `shipments.id` (NOT NULL, Cascade Delete)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `shipment_id` (`INTEGER`, NOT NULL, Indexed)
  - `event_type` (`VARCHAR(50)`, NOT NULL)
  - `location` (`VARCHAR(100)`, NULL)
  - `description` (`TEXT`, NULL)
  - `timestamp` (`DATETIME`, Default: UTC Timestamp)
- **Seed Record Count:** 28 milestone events (Booking, Gate-In, Customs Clear, Vessel Berth, Departure)
- **Audit Outcome:** **PASS**

---

### Table 6: `exceptions`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Foreign Keys:**
  - `shipment_id` $\rightarrow$ `shipments.id` (Nullable)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `shipment_id` (`INTEGER`, NULL, Indexed)
  - `exception_type` (`VARCHAR(50)`, NOT NULL)
  - `severity` (`VARCHAR(20)`, Default: `'MEDIUM'`)
  - `status` (`VARCHAR(20)`, Default: `'OPEN'`)
  - `assigned_to` (`VARCHAR(80)`, NULL, Indexed)
  - `created_at` (`DATETIME`, Default: UTC Timestamp)
- **Relationships:**
  - One-to-Many with `exception_actions` (`exception_id`)
- **Seed Record Count:** 4 active operational SLA exceptions
- **CRUD Operations Tested:** Log exception via modal form, Filter by severity, Assign to officer, Append investigation note, Resolve exception.
- **Audit Outcome:** **PASS**

---

### Table 7: `exception_actions`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Foreign Keys:**
  - `exception_id` $\rightarrow$ `exceptions.id` (NOT NULL)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `exception_id` (`INTEGER`, NOT NULL, Indexed)
  - `action_type` (`VARCHAR(50)`, NOT NULL)
  - `note` (`TEXT`, NULL)
  - `created_at` (`DATETIME`, Default: UTC Timestamp)
- **Audit Outcome:** **PASS**

---

### Table 8: `communication_logs`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Foreign Keys:**
  - `shipment_id` $\rightarrow$ `shipments.id` (Nullable)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `shipment_id` (`INTEGER`, NULL, Indexed)
  - `recipient` (`VARCHAR(120)`, NOT NULL)
  - `channel` (`VARCHAR(50)`, Default: `'EMAIL'`)
  - `subject` (`VARCHAR(255)`, NULL)
  - `message_body` (`TEXT`, NOT NULL)
  - `sent_at` (`DATETIME`, Default: UTC Timestamp)
- **Seed Record Count:** 4 verified customer dispatch notices
- **CRUD Operations Tested:** Submit draft, Approve & dispatch, Save revision notes.
- **Audit Outcome:** **PASS**

---

### Table 9: `audit_logs`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Foreign Keys:**
  - `user_id` $\rightarrow$ `users.id` (Nullable)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `user_id` (`INTEGER`, NULL, Indexed)
  - `action` (`VARCHAR(80)`, NOT NULL, Indexed)
  - `entity` (`VARCHAR(50)`, NULL)
  - `entity_id` (`VARCHAR(50)`, NULL)
  - `details` (`TEXT`, NULL)
  - `created_at` (`DATETIME`, Default: UTC Timestamp, Indexed)
- **Audit Outcome:** **PASS**

---

### Table 10: `reference_data`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `category` (`VARCHAR(50)`, NOT NULL, Indexed)
  - `code` (`VARCHAR(50)`, NOT NULL, Indexed)
  - `label` (`VARCHAR(100)`, NOT NULL)
  - `is_active` (`BOOLEAN`, Default: `True`)
- **Seed Record Count:** 35 standardized records (10 Seaports, 7 Vessels, 5 Container Types, 9 Shipment Statuses, 4 Shipping Classes)
- **Audit Outcome:** **PASS**

---

### Table 11: `model_registry`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `model_name` (`VARCHAR(100)`, NOT NULL, Unique)
  - `stage` (`VARCHAR(50)`, NOT NULL)
  - `version` (`VARCHAR(20)`, Default: `'v1.0'`)
  - `accuracy` (`FLOAT`, Default: `0.0`)
  - `roc_auc` (`FLOAT`, Default: `0.0`)
  - `is_active` (`BOOLEAN`, Default: `True`)
  - `created_at` (`DATETIME`, Default: UTC Timestamp)
- **Seed Record Count:** 3 production models (Stage 1 Logistic Regression / XGBoost, Stage 2 Dispatch XGBoost, Stage 3 CatBoost Regressor)
- **Audit Outcome:** **PASS**

---

### Table 12: `model_scores`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Foreign Keys:**
  - `shipment_id` $\rightarrow$ `shipments.id` (Nullable)
  - `model_id` $\rightarrow$ `model_registry.id` (Nullable)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `shipment_id` (`INTEGER`, NULL, Indexed)
  - `model_id` (`INTEGER`, NULL)
  - `prediction` (`INTEGER`, NOT NULL)
  - `probability` (`FLOAT`, NOT NULL)
  - `stage` (`VARCHAR(50)`, NULL)
  - `created_at` (`DATETIME`, Default: UTC Timestamp)
- **Relationships:**
  - One-to-Many with `risk_factors` (`score_id`)
- **Audit Outcome:** **PASS**

---

### Table 13: `risk_factors`
- **Primary Key:** `id` (`INTEGER`, Auto-Increment)
- **Foreign Keys:**
  - `score_id` $\rightarrow$ `model_scores.id` (NOT NULL, Cascade Delete)
- **Columns & Data Types:**
  - `id` (`INTEGER`, NOT NULL)
  - `score_id` (`INTEGER`, NOT NULL, Indexed)
  - `feature_name` (`VARCHAR(80)`, NOT NULL)
  - `shap_value` (`FLOAT`, NOT NULL)
  - `display_order` (`INTEGER`, Default: `0`)
- **Audit Outcome:** **PASS**

---

## 3. Database Audit Verification Summary

- **Total Relational Tables:** 13
- **Primary Key Coverage:** 100%
- **Foreign Key Constraints Verified:** 100%
- **Relational Integrity Violations:** 0
- **Total Seed Data Volume:** 100+ production records
- **MySQL PyMySQL Driver Compatibility:** Verified
- **Overall Database Integrity Status:** **PASS (Production Ready)**
