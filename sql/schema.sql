-- ==============================================================================
-- ROUTEMIND AI - COMPLETE 12-TABLE DATABASE SCHEMA
-- Project: Predictive Logistics Exception Management & Resolution (BRD Phase 3)
-- Author: Gowtham K
-- Compatible with MySQL 8.0+ and SQLite 3
-- ==============================================================================

-- 1. USERS (Authentication & Role-Based Access Control)
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'DISPATCHER', -- 'DISPATCHER', 'MANAGER', 'ADMIN'
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_email (email),
    INDEX idx_user_role (role)
);

-- 2. CUSTOMERS (Customer Master Data)
CREATE TABLE IF NOT EXISTS customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    external_customer_id VARCHAR(100) NOT NULL UNIQUE,
    customer_name VARCHAR(150) NOT NULL,
    customer_segment VARCHAR(50) NOT NULL DEFAULT 'Consumer', -- 'Consumer', 'Corporate', 'Home Office'
    customer_region VARCHAR(100) NULL,
    customer_country VARCHAR(100) NULL,
    priority_level VARCHAR(30) NOT NULL DEFAULT 'NORMAL', -- 'LOW', 'NORMAL', 'HIGH', 'VIP'
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cust_segment (customer_segment),
    INDEX idx_cust_priority (priority_level)
);

-- 3. PRODUCTS (Product Master Data & Catalog)
CREATE TABLE IF NOT EXISTS products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    external_product_id VARCHAR(100) NOT NULL UNIQUE,
    product_name VARCHAR(200) NOT NULL,
    category_id INT NULL,
    category_name VARCHAR(150) NOT NULL,
    department_name VARCHAR(100) NOT NULL DEFAULT 'Apparel',
    product_price DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_prod_cat (category_name),
    INDEX idx_prod_dept (department_name)
);

-- 4. ORDERS_SHIPMENTS (Core Order-Item & Shipment Lifecycle Table)
CREATE TABLE IF NOT EXISTS orders_shipments (
    shipment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    external_order_id VARCHAR(100) NOT NULL,
    external_order_item_id VARCHAR(100) NULL,
    customer_id INT NULL,
    product_id INT NULL,
    
    -- Timeline & Commitments
    order_date DATETIME NOT NULL,
    scheduled_shipping_days INT NOT NULL DEFAULT 2,
    scheduled_delivery_date DATE NULL,
    
    -- Logistics & Geography
    shipping_mode VARCHAR(50) NOT NULL DEFAULT 'Standard Class',
    market VARCHAR(100) NOT NULL DEFAULT 'Europe',
    order_region VARCHAR(100) NOT NULL DEFAULT 'Western Europe',
    order_country VARCHAR(100) NULL,
    order_city VARCHAR(100) NULL,
    order_state VARCHAR(100) NULL,
    order_zipcode VARCHAR(30) NULL,
    
    -- Commercials
    item_quantity INT NOT NULL DEFAULT 1,
    product_price DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    discount_rate DECIMAL(8, 4) NOT NULL DEFAULT 0.0000,
    sales_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    order_value DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    payment_type VARCHAR(50) NOT NULL DEFAULT 'DEBIT',
    carrier_name VARCHAR(100) NULL,
    shipment_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    
    -- Integrated Machine Learning Predictions (Directly Stored per Streamlined Schema)
    model_01_late_probability DECIMAL(6, 4) NULL,
    model_01_risk_flag TINYINT(1) NULL,
    model_02_late_probability DECIMAL(6, 4) NULL,
    model_02_risk_flag TINYINT(1) NULL,
    order_to_ship_time DECIMAL(5, 2) NULL,
    predicted_real_days DECIMAL(5, 2) NULL,
    predicted_delay_days DECIMAL(5, 2) NULL,
    risk_level VARCHAR(30) NOT NULL DEFAULT 'LOW', -- 'LOW', 'MODERATE', 'HIGH'
    sla_status VARCHAR(100) NULL,
    scored_at DATETIME NULL,
    
    -- Observed Ground Truth Outcomes (Recorded Post-Delivery Only; Strictly Excluded at Prediction Time)
    actual_shipping_date DATE NULL,
    actual_delivery_date DATE NULL,
    actual_delivery_outcome VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN', -- 'ON_TIME', 'LATE', 'UNKNOWN'
    actual_delay_reason VARCHAR(255) NULL,
    
    -- Timestamps
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_order_id (external_order_id),
    INDEX idx_order_date (order_date),
    INDEX idx_ship_mode (shipping_mode),
    INDEX idx_risk_level (risk_level),
    INDEX idx_ship_status (shipment_status)
);

-- 5. SHIPMENT_EVENTS (Operational Event Tracking)
CREATE TABLE IF NOT EXISTS shipment_events (
    event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    shipment_id BIGINT NOT NULL,
    recorded_by INT NULL,
    event_type VARCHAR(100) NOT NULL, -- 'ORDER_PLACED', 'PICK_PACK', 'DISPATCHED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED', 'EXCEPTION'
    event_description TEXT NULL,
    event_location VARCHAR(150) NULL,
    event_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_shipment (shipment_id),
    INDEX idx_event_type (event_type),
    INDEX idx_event_time (event_time)
);

-- 6. RISK_FACTORS (Explainability & SHAP Feature-Level Attributions)
CREATE TABLE IF NOT EXISTS risk_factors (
    factor_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    shipment_id BIGINT NOT NULL,
    model_stage VARCHAR(50) NOT NULL DEFAULT 'order_creation', -- 'order_creation', 'dispatch', 'delay_duration'
    feature_name VARCHAR(150) NOT NULL,
    feature_value VARCHAR(255) NULL,
    contribution_value DECIMAL(12, 6) NOT NULL DEFAULT 0.000000,
    contribution_direction VARCHAR(30) NOT NULL, -- 'INCREASES_RISK', 'DECREASES_RISK'
    explanation TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_risk_shipment (shipment_id),
    INDEX idx_risk_stage (model_stage)
);

-- 7. EXCEPTION_CASES (Operational Exception Management)
CREATE TABLE IF NOT EXISTS exception_cases (
    exception_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    shipment_id BIGINT NOT NULL,
    assigned_to INT NULL,
    created_by INT NULL,
    exception_type VARCHAR(100) NOT NULL DEFAULT 'LATE_DELIVERY_RISK',
    severity VARCHAR(30) NOT NULL DEFAULT 'HIGH', -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    priority VARCHAR(30) NOT NULL DEFAULT 'HIGH', -- 'LOW', 'NORMAL', 'HIGH', 'URGENT'
    exception_description TEXT NULL,
    suspected_cause VARCHAR(255) NULL,
    actual_root_cause VARCHAR(255) NULL,
    resolution_summary TEXT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'
    opened_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    closed_at DATETIME NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_exc_shipment (shipment_id),
    INDEX idx_exc_status (status),
    INDEX idx_exc_severity (severity)
);

-- 8. EXCEPTION_COMMENTS (Investigation Notes)
CREATE TABLE IF NOT EXISTS exception_comments (
    comment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    exception_id BIGINT NOT NULL,
    user_id INT NULL,
    comment_text TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_comment_exception (exception_id)
);

-- 9. EXCEPTION_ACTIONS (Resolution & Mitigation Actions)
CREATE TABLE IF NOT EXISTS exception_actions (
    action_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    exception_id BIGINT NOT NULL,
    generated_by VARCHAR(50) NOT NULL DEFAULT 'AI', -- 'AI', 'USER', 'SYSTEM'
    action_title VARCHAR(200) NOT NULL,
    action_description TEXT NULL,
    assumptions JSON NULL,
    feasibility_status VARCHAR(30) NOT NULL DEFAULT 'VERIFIED', -- 'UNVERIFIED', 'VERIFIED', 'NOT_FEASIBLE'
    approval_status VARCHAR(30) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED'
    approved_by INT NULL,
    approved_at DATETIME NULL,
    execution_status VARCHAR(30) NOT NULL DEFAULT 'NOT_STARTED', -- 'NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    outcome_notes TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_action_exception (exception_id),
    INDEX idx_action_approval (approval_status)
);

-- 10. COMMUNICATIONS (Customer Updates & Escalation Drafts)
CREATE TABLE IF NOT EXISTS communications (
    communication_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    exception_id BIGINT NOT NULL,
    action_id BIGINT NULL,
    audience VARCHAR(30) NOT NULL DEFAULT 'CUSTOMER', -- 'CUSTOMER', 'INTERNAL'
    communication_type VARCHAR(50) NOT NULL DEFAULT 'CUSTOMER_UPDATE', -- 'CUSTOMER_UPDATE', 'ESCALATION', 'STATUS_SUMMARY'
    subject VARCHAR(255) NOT NULL,
    generated_draft TEXT NOT NULL,
    final_text TEXT NULL,
    ai_model_name VARCHAR(100) NULL DEFAULT 'RouteMind-GenAI-v1',
    prompt_version VARCHAR(50) NOT NULL DEFAULT 'v1.0.0',
    approval_status VARCHAR(30) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED'
    created_by INT NULL,
    approved_by INT NULL,
    approved_at DATETIME NULL,
    delivery_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'APPROVED', 'SENT_SIMULATED'
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_comm_exception (exception_id),
    INDEX idx_comm_status (delivery_status)
);

-- 11. AUDIT_LOGS (System Activity & Governance Trail)
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action_type VARCHAR(100) NOT NULL, -- 'LOGIN', 'CREATE_SHIPMENT', 'SCORE_SHIPMENT', 'APPROVE_ACTION', 'OVERRIDE_THRESHOLD'
    object_type VARCHAR(100) NOT NULL,
    object_id BIGINT NULL,
    old_value JSON NULL,
    new_value JSON NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action_type)
);

-- 12. REFERENCE_DATA (Lookup Tables for Operational Codes)
CREATE TABLE IF NOT EXISTS reference_data (
    reference_id INT AUTO_INCREMENT PRIMARY KEY,
    reference_type VARCHAR(100) NOT NULL, -- 'SHIPPING_MODE', 'MARKET', 'REGION', 'CUSTOMER_SEGMENT', 'SEVERITY'
    reference_code VARCHAR(100) NOT NULL,
    reference_value VARCHAR(150) NOT NULL,
    description TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_ref_code (reference_type, reference_code),
    INDEX idx_ref_type (reference_type)
);
