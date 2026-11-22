# RouteMind AI - Database Schema

- `users`: ID, username, email, password_hash, role, is_active, created_at
- `customers`: ID, first_name, last_name, segment, city, state, country
- `products`: ID, product_name, category_name, department_name, product_price
- `shipments`: ID, shipment_number, customer_id, product_id, scheduled_days, shipping_mode, risk_level, clearance_status
- `shipment_events`: ID, shipment_id, event_type, warehouse_processing_time, timestamp
- `model_registry`: ID, model_name, version, stage, algorithm, accuracy, roc_auc
- `model_scores`: ID, shipment_id, stage, predicted_probability, predicted_class, risk_level
- `risk_factors`: ID, score_id, feature_name, feature_value, contribution_value, direction
- `shipment_exceptions`: ID, shipment_id, exception_type, severity, status, assigned_to
- `communication_logs`: ID, shipment_id, recipient, channel, message_body, sent_at
- `audit_logs`: ID, user_id, action, entity, entity_id, timestamp
