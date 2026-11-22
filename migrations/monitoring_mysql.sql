-- MySQL equivalents of src/monitoring.py tables (INSERT-ONLY by convention; grant the app user INSERT/SELECT, not UPDATE/DELETE).
CREATE TABLE IF NOT EXISTS prediction_history (
  prediction_id BIGINT AUTO_INCREMENT PRIMARY KEY, shipment_id BIGINT NULL, prediction_stage VARCHAR(30) NOT NULL, model_version VARCHAR(20) NOT NULL,
  predicted_probability DECIMAL(7,6) NOT NULL, predicted_class TINYINT NOT NULL, risk_level ENUM('LOW','MEDIUM','HIGH') NOT NULL,
  decision_threshold DECIMAL(5,4) NOT NULL, prediction_timestamp DATETIME(6) NOT NULL, feature_snapshot JSON NULL,
  prediction_status VARCHAR(20) NOT NULL, KEY ix_pred_ship (shipment_id));
-- Recommended: model_scores (existing table) can serve as prediction_history; add columns prediction_stage + feature_snapshot instead of a new table.
CREATE TABLE IF NOT EXISTS prediction_failures (
  failure_id BIGINT AUTO_INCREMENT PRIMARY KEY, shipment_id BIGINT NULL, prediction_stage VARCHAR(30), error_code VARCHAR(40),
  error_message TEXT, failed_at DATETIME(6) NOT NULL);
CREATE TABLE IF NOT EXISTS actual_outcomes (
  outcome_id BIGINT AUTO_INCREMENT PRIMARY KEY, shipment_id BIGINT NOT NULL, scheduled_delivery_ts DATETIME NULL, actual_delivery_ts DATETIME NULL,
  actual_outcome ENUM('ON_TIME','LATE') NOT NULL, actual_delay_days DECIMAL(8,3), delay_reason VARCHAR(255) NULL, recorded_at DATETIME(6) NOT NULL,
  KEY ix_out_ship (shipment_id));
-- model_registry additions needed by the registry JSON: prediction_stage, role, approval_status, approved_by, approved_at, deployed_at,
-- dataset_version, target_definition_version, calibration_method, feature_schema (JSON).
