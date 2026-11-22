-- ==============================================================================
-- ROUTEMIND AI - MASTER SEED DATA
-- Compatible with MySQL 8.0+ and SQLite 3
-- ==============================================================================

-- 1. SEED USERS (Password hashes generated via werkzeug scrypt/pbkdf2)
-- Default passwords:
--   admin@routemind.ai       -> admin123
--   dispatcher@routemind.ai  -> dispatch123
--   manager@routemind.ai     -> manager123
INSERT INTO users (user_id, full_name, email, password_hash, role, is_active, created_at)
VALUES 
(1, 'Gowtham K (Admin)', 'admin@routemind.ai', 'scrypt:32768:8:1$7tS5vX7kH8w19$485303c72b217088924bce6505777174db4c19adfa0bc53dbab1f6f88126e8db30f36f6d0f669a03eb7a4bf00941865c3bbd09796e95aaae9e55767b2d5f0e9e', 'ADMIN', 1, CURRENT_TIMESTAMP),
(2, 'Alex Turner (Dispatcher)', 'dispatcher@routemind.ai', 'scrypt:32768:8:1$9qR3wY8jL2k41$311756a943715103472bc05167664183dc3d08acfa9bc42eaab0f5e77015d7ca29e25e5c9e558992da693ae99830754b2aac98685d84999d8d44656a1c4e9d8d', 'DISPATCHER', 1, CURRENT_TIMESTAMP),
(3, 'Sarah Jenkins (Ops Manager)', 'manager@routemind.ai', 'scrypt:32768:8:1$2pK5mN4vB7x63$622877b854826214583cd16278775294ed4e19bdfb0cd53fbba1f6f88126e8db40f36f6d0f669a03eb7a4bf00941865c3bbd09796e95aaae9e55767b2d5f0e9f', 'MANAGER', 1, CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);

-- 2. SEED REFERENCE DATA (Lookup Values)
INSERT INTO reference_data (reference_type, reference_code, reference_value, description)
VALUES
-- Shipping Modes
('SHIPPING_MODE', 'STANDARD', 'Standard Class', '4-Day standard surface linehaul delivery SLA'),
('SHIPPING_MODE', 'SECOND', 'Second Class', '2-Day priority expedited ground service SLA'),
('SHIPPING_MODE', 'FIRST', 'First Class', '1-Day air express expedited delivery SLA'),
('SHIPPING_MODE', 'SAME_DAY', 'Same Day', 'Zero-buffer same-day express delivery SLA'),

-- Customer Segments
('CUSTOMER_SEGMENT', 'CONSUMER', 'Consumer', 'Individual retail residential consumer accounts'),
('CUSTOMER_SEGMENT', 'CORPORATE', 'Corporate', 'B2B commercial commercial client accounts'),
('CUSTOMER_SEGMENT', 'HOME_OFFICE', 'Home Office', 'Small business and remote home office accounts'),

-- Markets
('MARKET', 'EUROPE', 'Europe', 'European Union and Western/Eastern Europe territory'),
('MARKET', 'LATAM', 'LATAM', 'Latin America and Caribbean regional territory'),
('MARKET', 'PACIFIC_ASIA', 'Pacific Asia', 'Asia-Pacific and Indian subcontinent territory'),
('MARKET', 'USCA', 'USCA', 'United States and Canada domestic trade corridor'),
('MARKET', 'AFRICA', 'Africa', 'African continent regional trade territory'),

-- Payment Types
('PAYMENT_TYPE', 'DEBIT', 'DEBIT', 'Electronic bank debit transfer at checkout'),
('PAYMENT_TYPE', 'TRANSFER', 'TRANSFER', 'Automated Clearing House (ACH) wire transfer'),
('PAYMENT_TYPE', 'PAYMENT', 'PAYMENT', 'Direct credit card merchant settlement'),
('PAYMENT_TYPE', 'CASH', 'CASH', 'Cash on delivery payment commitment'),

-- Risk Levels
('RISK_LEVEL', 'LOW', 'Low Risk', 'On-time delivery expected; no dispatcher intervention required'),
('RISK_LEVEL', 'MODERATE', 'Moderate Risk', 'Monitor warehouse handling and regional hub transfers'),
('RISK_LEVEL', 'HIGH', 'High Risk', 'Critical SLA breach predicted; immediate dispatcher action required')
ON DUPLICATE KEY UPDATE reference_value=VALUES(reference_value);

-- 3. SEED CUSTOMERS
INSERT INTO customers (customer_id, external_customer_id, customer_name, customer_segment, customer_region, customer_country, priority_level)
VALUES
(1, 'CUST-19492', 'Irene Luna', 'Consumer', 'South Asia', 'India', 'VIP'),
(2, 'CUST-20511', 'Acme Logistics Europe', 'Corporate', 'Western Europe', 'Germany', 'HIGH'),
(3, 'CUST-18400', 'Pacific Apex Trading', 'Home Office', 'Pacific Asia', 'Japan', 'NORMAL'),
(4, 'CUST-17220', 'Global Retail USCA', 'Corporate', 'East of USA', 'United States', 'HIGH')
ON DUPLICATE KEY UPDATE customer_name=VALUES(customer_name);

-- 4. SEED PRODUCTS
INSERT INTO products (product_id, external_product_id, product_name, category_id, category_name, department_name, product_price)
VALUES
(1, 'PROD-1360', 'Smart watch with Fitness Tracker', 73, 'Sporting Goods', 'Fitness', 327.75),
(2, 'PROD-1014', 'Perfect Fitness Rip Deck', 45, 'Cardio Equipment', 'Fitness', 59.99),
(3, 'PROD-1025', 'Nike Men Dri-FIT Training Tee', 18, 'Apparel', 'Apparel', 35.00),
(4, 'PROD-1004', 'Field & Stream Sports Backpack', 24, 'Cleats', 'Footwear', 45.00)
ON DUPLICATE KEY UPDATE product_name=VALUES(product_name);

-- 5. SEED ORDERS_SHIPMENTS (Sample Active Control Tower Shipments)
INSERT INTO orders_shipments (
    shipment_id, external_order_id, external_order_item_id, customer_id, product_id,
    order_date, scheduled_shipping_days, scheduled_delivery_date, shipping_mode, market, order_region,
    order_country, order_city, order_state, order_zipcode, item_quantity, product_price,
    discount_rate, sales_amount, order_value, payment_type, carrier_name, shipment_status,
    model_01_late_probability, model_01_risk_flag, model_02_late_probability, model_02_risk_flag,
    order_to_ship_time, predicted_real_days, predicted_delay_days, risk_level, sla_status, scored_at
)
VALUES
-- High Risk Dispatched Shipment (Needs Reroute)
(
    1, 'ORD-75939', 'ITEM-179254', 1, 1,
    '2026-11-13 12:27:00', 4, '2026-11-17', 'Standard Class', 'Pacific Asia', 'South Asia',
    'India', 'Bikaner', 'Rajasthan', '334001', 1, 327.75,
    0.0500, 311.36, 311.36, 'TRANSFER', 'BlueDart Ground', 'DISPATCHED',
    0.7850, 1, 0.9716, 1,
    5.00, 5.00, 1.00, 'HIGH', 'MINOR DELAY (+1 Day Late)', CURRENT_TIMESTAMP
),
-- Moderate Risk Order (At Order Creation)
(
    2, 'ORD-88210', 'ITEM-194012', 2, 2,
    CURRENT_TIMESTAMP, 2, DATE_ADD(CURRENT_DATE, INTERVAL 2 DAY), 'Second Class', 'Europe', 'Western Europe',
    'Germany', 'Frankfurt', 'Hesse', '60311', 3, 59.99,
    0.0000, 179.97, 179.97, 'DEBIT', 'DHL Express', 'PENDING',
    0.5420, 1, 0.4200, 0,
    1.00, 2.50, 0.50, 'MODERATE', 'MODERATE RISK (Monitor Warehouse Fulfillment)', CURRENT_TIMESTAMP
),
-- Low Risk On-Time Order (First Class Air)
(
    3, 'ORD-91045', 'ITEM-204118', 3, 3,
    CURRENT_TIMESTAMP, 1, DATE_ADD(CURRENT_DATE, INTERVAL 1 DAY), 'First Class', 'Pacific Asia', 'Eastern Asia',
    'Japan', 'Tokyo', 'Kanto', '100-0001', 2, 35.00,
    0.1000, 63.00, 63.00, 'PAYMENT', 'Yamato Transport', 'DISPATCHED',
    0.1240, 0, 0.0850, 0,
    0.50, 1.00, 0.00, 'LOW', 'ON-TIME EXPECTED (SLA Satisfied)', CURRENT_TIMESTAMP
)
ON DUPLICATE KEY UPDATE external_order_id=VALUES(external_order_id);
