"""
prediction_service.py - Production Machine Learning Prediction Service for RouteMind AI
Author: RouteMind AI Engineering
Handles dual-stage predictive inference, feature validation, and MySQL persistence.
"""
import os
import sys
import datetime as dt
from typing import Dict, Any, Optional, Tuple, List

from extensions import db
from src.models.model_score_model import ModelScore
from src.models.shipment_model import Shipment
import src.prediction as PR
import src.dispatch_prediction as DP

ORDER_CREATION_NUMERICAL = ["Days for shipment (scheduled)", "Order Item Quantity", "Sales"]
ORDER_CREATION_CATEGORICAL = ["Shipping Mode", "Order Region", "Type", "Market", "Primary Category"]
ORDER_CREATION_REQUIRED = ORDER_CREATION_NUMERICAL + ORDER_CREATION_CATEGORICAL

DISPATCH_NUMERICAL = ["Days for shipment (scheduled)", "Order-to-Ship Time"]
DISPATCH_CATEGORICAL = ["Shipping Mode", "Order Region", "Market", "Department Name", "Customer Segment"]
DISPATCH_REQUIRED = DISPATCH_NUMERICAL + DISPATCH_CATEGORICAL


class PredictionService:

    @staticmethod
    def extract_order_creation_features_from_shipment(shipment: Shipment) -> Dict[str, Any]:
        """Extract verified order-creation features from an existing database shipment record."""
        return {
            "Days for shipment (scheduled)": float(shipment.days_scheduled or 4.0),
            "Order Item Quantity": int(shipment.order_item_quantity or 1),
            "Sales": float(shipment.sales_per_customer or 0.0),
            "Shipping Mode": str(shipment.shipping_mode or "Standard Class"),
            "Order Region": str(shipment.destination_region or "Western Europe"),
            "Type": "DEBIT",
            "Market": "Europe",
            "Primary Category": shipment.product.category if shipment.product and shipment.product.category else "General Cargo"
        }

    @staticmethod
    def extract_dispatch_features_from_shipment(shipment: Shipment) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract genuine dispatch-stage features from an existing database shipment record.
        Returns (features_dict, None) if available, or (None, reason) if dispatch stage not reached.
        """
        # Dispatch requires order-to-ship time (warehouse processing duration)
        dwell_time = shipment.warehouse_processing_time_days
        if dwell_time is None or dwell_time <= 0:
            return None, "Shipment has not completed warehouse dock processing ('Order-to-Ship Time' is not recorded)."

        features = {
            "Days for shipment (scheduled)": float(shipment.days_scheduled or 4.0),
            "Order-to-Ship Time": float(dwell_time),
            "Shipping Mode": str(shipment.shipping_mode or "Standard Class"),
            "Order Region": str(shipment.destination_region or "Western Europe"),
            "Market": "Europe",
            "Department Name": "Maritime Logistics",
            "Customer Segment": str(shipment.customer_segment or "Consumer")
        }
        return features, None

    @staticmethod
    def score_order_creation(payload: Dict[str, Any], shipment_id: Optional[Any] = None, models_dir: Optional[str] = None) -> Dict[str, Any]:
        """Execute Stage 1 (Order Creation) prediction."""
        # Ensure non-operational DataCo schema metadata fields are populated if not supplied
        enriched = dict(payload)
        enriched.setdefault("Type", "DEBIT")
        enriched.setdefault("Shipping Mode", "Standard Class")
        enriched.setdefault("order date (DateOrders)", "01/15/2018 10:00")
        enriched.setdefault("Category Name", enriched.get("Primary Category", "Sporting Goods"))
        enriched.setdefault("Primary Category", enriched.get("Category Name", "Sporting Goods"))
        enriched.setdefault("Department Name", "Fitness")
        enriched.setdefault("Product Name", "Standard Cargo")
        enriched.setdefault("Order Item Product Price", float(enriched.get("Sales", 100.0)))
        enriched.setdefault("Order Item Quantity", 1)
        enriched.setdefault("Customer Segment", "Consumer")
        enriched.setdefault("Customer City", "London")
        enriched.setdefault("Customer Country", "United Kingdom")
        enriched.setdefault("Customer State", "Greater London")
        enriched.setdefault("Market", "Europe")
        enriched.setdefault("Order Country", "United Kingdom")
        enriched.setdefault("Order Region", "Western Europe")
        enriched.setdefault("Order Item Discount Rate", 0.0)

        if not models_dir:
            try:
                models_dir = current_app.config.get('MODELS_DIR')
            except Exception:
                pass
            if not models_dir:
                models_dir = getattr(PR, 'MODELS', None)

        res = PR.predict_order_creation_api(enriched, shipment_id=shipment_id, models_dir=models_dir)
        if res.get("prediction_status") == "PREDICTED":
            res["model_name"] = "Model 01: Order Creation Late Delivery Classifier (Logistic Regression)"
            # Persist to MySQL model_scores if shipment_id is integer
            try:
                numeric_shipment_id = int(shipment_id) if shipment_id is not None and str(shipment_id).isdigit() else None
                if numeric_shipment_id:
                    score = ModelScore(
                        shipment_id=numeric_shipment_id,
                        prediction_stage="STAGE_1_ORDER_CREATION",
                        predicted_probability=float(res.get("predicted_probability", 0.0)),
                        predicted_class=int(res.get("predicted_class", 0)),
                        risk_level=str(res.get("risk_level", "LOW"))
                    )
                    db.session.add(score)
                    db.session.commit()
            except Exception:
                db.session.rollback()
        return res

    @staticmethod
    def score_dispatch(payload: Dict[str, Any], shipment_id: Optional[Any] = None, models_dir: Optional[str] = None) -> Dict[str, Any]:
        """Execute Stage 2 (Warehouse Dispatch) XGBoost prediction."""
        if not models_dir:
            try:
                models_dir = current_app.config.get('MODELS_DIR')
            except Exception:
                pass
            if not models_dir:
                models_dir = getattr(DP, 'MODELS', None) or getattr(PR, 'MODELS', None)

        res = DP.predict_dispatch_api(payload, shipment_id=shipment_id, models_dir=models_dir)
        if res.get("prediction_status") == "PREDICTED":
            try:
                numeric_shipment_id = int(shipment_id) if shipment_id is not None and str(shipment_id).isdigit() else None
                if numeric_shipment_id:
                    score = ModelScore(
                        shipment_id=numeric_shipment_id,
                        prediction_stage="STAGE_2_WAREHOUSE_DISPATCH",
                        predicted_probability=float(res.get("predicted_probability", 0.0)),
                        predicted_class=int(res.get("predicted_class", 0)),
                        risk_level=str(res.get("risk_level", "LOW"))
                    )
                    db.session.add(score)
                    db.session.commit()
            except Exception:
                db.session.rollback()
        return res

    @staticmethod
    def score_control_tower_unified(
        order_payload: Optional[Dict[str, Any]],
        dispatch_payload: Optional[Dict[str, Any]],
        shipment_id: Optional[Any] = None,
        models_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified Control Tower prediction preserving Stage 1 and Stage 2 independently.
        Never averages or computes max(p1, p2) as a calibrated probability.
        """
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        if not models_dir:
            try:
                models_dir = current_app.config.get('MODELS_DIR')
            except Exception:
                pass
            if not models_dir:
                models_dir = getattr(PR, 'MODELS', None)
        
        # Stage 1 Execution
        if order_payload:
            m1_res = PredictionService.score_order_creation(order_payload, shipment_id=shipment_id, models_dir=models_dir)
        else:
            m1_res = {
                "prediction_status": "SKIPPED",
                "message": "Order creation features not supplied."
            }

        # Stage 2 Execution
        if dispatch_payload:
            m2_res = PredictionService.score_dispatch(dispatch_payload, shipment_id=shipment_id, models_dir=models_dir)
        else:
            m2_res = {
                "prediction_status": "STAGE_NOT_REACHED",
                "message": "Warehouse dispatch features (Order-to-Ship Time) are not yet available for this consignment."
            }

        p1 = m1_res.get("predicted_probability")
        p2 = m2_res.get("predicted_probability")

        if p1 is not None and p2 is not None:
            drift = round((p2 - p1) * 100, 2)
            if p2 >= 0.50:
                overall_trajectory = "CRITICAL_RISK_ESCALATION"
                action = "HOLD_FOR_EXPEDITE"
            elif p2 >= 0.35:
                overall_trajectory = "ELEVATED_DISPATCH_RISK"
                action = "MONITOR_DOCK_DEPARTURE"
            else:
                overall_trajectory = "ON_TRACK"
                action = "CLEAR_FOR_TRANSIT"
            comparison_note = "Trajectory compares order creation baseline against dock dispatch departure."
        elif p1 is not None:
            drift = None
            overall_trajectory = "PRE_DISPATCH_BASELINE"
            action = "AWAIT_WAREHOUSE_DISPATCH"
            comparison_note = "Only Stage 1 (Order Creation) prediction is available. Stage 2 will execute upon dock release."
        else:
            drift = None
            overall_trajectory = "PENDING_INFERENCE"
            action = "PROVIDE_VALID_FEATURES"
            comparison_note = "Insufficient features provided for dual-stage inference."

        summary = {
            "overall_risk_level": m2_res.get("risk_level") if p2 is not None else (m1_res.get("risk_level") or "UNKNOWN"),
            "recommended_action": action,
            "order_creation_probability": p1,
            "dispatch_probability": p2,
            "probability_drift": drift,
            "overall_trajectory": overall_trajectory,
            "note": comparison_note
        }

        return {
            "shipment_id": shipment_id,
            "evaluation_timestamp": now,
            "control_tower_summary": summary,
            "stage_comparison": {
                "order_creation_probability": p1,
                "dispatch_probability": p2,
                "risk_trajectory": overall_trajectory,
                "risk_drift_percentage_points": drift,
                "calibration_note": "Stage outputs are independent model evaluations (Logistic Regression vs. XGBoost) and not a single joint probability.",
                "context": comparison_note
            },
            "operational_recommendation": action,
            "model_01_order_creation": m1_res,
            "model_02_dispatch": m2_res
        }

    @classmethod
    def score_unified(cls, *args, **kwargs):
        """Backward-compatible alias for score_control_tower_unified."""
        return cls.score_control_tower_unified(*args, **kwargs)

