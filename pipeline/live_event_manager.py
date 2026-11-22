"""
live_event_manager.py - Real-Time Shipment Event Ingestion & Dual-Model Prediction
Implements the live event addition and dual-model prediction methodology from reference notebook Cells 6, 11, and 20:
- add_new_event(): Appends live shipment events into the tracking buffer
- Dual-model real-time scoring (Random Forest & XGBoost)
- Live activity comparison (before vs after event addition)
"""

import os
import json
import pandas as pd
from datetime import datetime

class LiveEventManager:
    def __init__(self, tracking_history_file: str = "data/live_shipment_events.csv"):
        self.tracking_history_file = tracking_history_file
        self.event_buffer = []
        os.makedirs(os.path.dirname(self.tracking_history_file), exist_ok=True)
        if os.path.exists(self.tracking_history_file):
            try:
                self.events_df = pd.read_csv(self.tracking_history_file)
            except Exception:
                self.events_df = pd.DataFrame()
        else:
            self.events_df = pd.DataFrame()

    def add_new_shipment_event(
        self,
        event_payload: dict,
        rf_pipeline=None,
        xgb_pipeline=None,
        rf_threshold: float = 0.5,
        xgb_threshold: float = 0.4
    ) -> dict:
        """
        Adds a new shipment record into the tracking stream (Cell 6 add_new_event logic)
        and scores it across both Random Forest and XGBoost (Cell 20 logic).
        """
        timestamp_str = event_payload.get("event_timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
        shipment_id = event_payload.get("Order Id", f"LIVE-{len(self.events_df)+1:05d}")

        record = dict(event_payload)
        record["event_timestamp"] = timestamp_str
        record["ingested_at"] = datetime.utcnow().isoformat() + "Z"

        # Prepare 1-row DataFrame for inference with schema completion
        input_df = pd.DataFrame([event_payload])

        # Fill common schema columns if missing
        expected_defaults = {
            "Days for shipment (scheduled)": 3,
            "Order Item Quantity": 1,
            "Sales": 100.0,
            "Order Item Product Price": 100.0,
            "Order Item Discount Rate": 0.0,
            "Type": "DEBIT",
            "Shipping Mode": "Standard Class",
            "Order Region": "South Asia",
            "Market": "Pacific Asia",
            "Order Country": "India",
            "Customer Segment": "Consumer",
            "Category Name": "Sporting Goods"
        }
        for k, v in expected_defaults.items():
            if k not in input_df.columns:
                input_df[k] = v

        # 1. Random Forest prediction (Reference notebook Cell 20)
        rf_prob = 0.5
        rf_pred = 0
        if rf_pipeline is not None:
            try:
                rf_prob = float(rf_pipeline.predict_proba(input_df)[0][1])
                rf_pred = int(rf_prob >= rf_threshold)
            except Exception as e:
                print(f"Warning: RF live prediction fallback: {e}")

        # 2. XGBoost prediction (Reference notebook Cell 20)
        xgb_prob = 0.5
        xgb_pred = 0
        if xgb_pipeline is not None:
            try:
                xgb_prob = float(xgb_pipeline.predict_proba(input_df)[0][1])
                xgb_pred = int(xgb_prob >= xgb_threshold)
            except Exception as e:
                print(f"Warning: XGBoost live prediction fallback: {e}")

        # Determine consolidated operational risk
        max_risk_prob = max(rf_prob, xgb_prob)
        if max_risk_prob >= 0.65:
            alert_level = "CRITICAL (RED)"
            recommended_action = "EXPEDITE: Upgrade to priority courier or reroute via alternative air hub."
        elif max_risk_prob >= 0.40:
            alert_level = "WARNING (YELLOW)"
            recommended_action = "MONITOR: Flag for proactive tracking; verify carrier transit SLA."
        else:
            alert_level = "NORMAL (GREEN)"
            recommended_action = "STANDARD: On schedule for normal delivery window."

        scoring_result = {
            "shipment_id": shipment_id,
            "event_timestamp": timestamp_str,
            "random_forest": {
                "prediction": "Late Delivery Risk" if rf_pred == 1 else "On-Time Delivery",
                "late_probability": round(rf_prob, 4),
                "threshold": rf_threshold
            },
            "xgboost": {
                "prediction": "Late Delivery Risk" if xgb_pred == 1 else "On-Time Delivery",
                "late_probability": round(xgb_prob, 4),
                "threshold": xgb_threshold
            },
            "consolidated_assessment": {
                "alert_level": alert_level,
                "highest_risk_score": round(max_risk_prob, 4),
                "recommended_action": recommended_action
            }
        }

        # Append to live history
        record["rf_late_probability"] = rf_prob
        record["xgb_late_probability"] = xgb_prob
        record["alert_level"] = alert_level

        self.events_df = pd.concat([self.events_df, pd.DataFrame([record])], ignore_index=True)
        self.events_df.to_csv(self.tracking_history_file, index=False)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Live Event Ingested: {shipment_id} -> Alert: {alert_level} (RF={rf_prob:.2%}, XGB={xgb_prob:.2%})")
        return scoring_result

    def get_activity_summary(self) -> dict:
        """Returns streaming volume and risk breakdown (reproducing Cell 7 & 10 before/after comparison)."""
        if self.events_df.empty:
            return {"total_events": 0, "critical_alerts": 0, "warning_alerts": 0, "normal_alerts": 0}

        return {
            "total_events": len(self.events_df),
            "critical_alerts": int((self.events_df["alert_level"] == "CRITICAL (RED)").sum()),
            "warning_alerts": int((self.events_df["alert_level"] == "WARNING (YELLOW)").sum()),
            "normal_alerts": int((self.events_df["alert_level"] == "NORMAL (GREEN)").sum())
        }
