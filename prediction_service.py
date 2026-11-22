import os
import json
import joblib
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor

class LogisticsPredictionService:
    """
    Unified Inference Engine for Logistics Control Tower.
    Manages both Baseline and Advanced Machine Learning Models:
      - Baseline Models:
          * Model 01: Logistic Regression (Order Creation Stage)
          * Model 02: XGBoost Classifier (Dispatch Stage)
          * Model 03: CatBoost Regressor (Routing / Delivery Duration Stage)
      - Improved Models:
          * Model 01 Improved: LightGBM / Enhanced Classifier (Order Creation Stage)
          * Model 02 Improved: Tuned XGBoost Classifier (Dispatch Stage)
          * Model 03 Improved: Random Forest / Tuned CatBoost Regressor (Delay Duration Stage)
    """

    def __init__(self, base_models_dir=None):
        if base_models_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            candidate = os.path.join(current_dir, "models")
            if os.path.exists(candidate):
                self.base_dir = candidate
            else:
                self.base_dir = os.path.join(os.getcwd(), "models")
        else:
            self.base_dir = base_models_dir

        # Baseline directories
        self.m1_dir = os.path.join(self.base_dir, "model_01")
        self.m2_dir = os.path.join(self.base_dir, "model_02")
        self.m3_dir = os.path.join(self.base_dir, "model_03")

        # Improved directories
        self.m1_imp_dir = os.path.join(self.base_dir, "model_01_improved")
        self.m2_imp_dir = os.path.join(self.base_dir, "model_02_improved")
        self.m3_imp_dir = os.path.join(self.base_dir, "model_03_improved")

        # Baseline model references
        self.m1_model = None
        self.m1_preprocessor = None
        self.m1_schema = None
        self.m1_threshold = 0.50

        self.m2_model = None
        self.m2_preprocessor = None
        self.m2_schema = None
        self.m2_threshold = 0.50

        self.m3_model = None
        self.m3_preprocessor = None
        self.m3_schema = None

        # Improved model references
        self.m1_imp_model = None
        self.m1_imp_preprocessor = None
        self.m1_imp_schema = None
        self.m1_imp_threshold = 0.35

        self.m2_imp_model = None
        self.m2_imp_preprocessor = None
        self.m2_imp_schema = None
        self.m2_imp_threshold = 0.40

        self.m3_imp_model = None
        self.m3_imp_preprocessor = None
        self.m3_imp_schema = None

        # Reference Pipeline Model (Random Forest from Reference Methodology)
        self.rf_reference_pipeline = None

        # Live Event Manager & Database Adapter
        from pipeline.live_event_manager import LiveEventManager
        from sql.db_adapter import DatabaseAdapter
        self.live_manager = LiveEventManager()
        self.db_adapter = DatabaseAdapter()

        self._load_all_models()

    def _load_all_models(self):
        """Loads both baseline and improved models, preprocessors, and schemas."""
        # 1. Baseline Model 01
        m1_model_path = os.path.join(self.m1_dir, "logistic_regression_model.joblib")
        m1_prep_path = os.path.join(self.m1_dir, "preprocessing_pipeline.joblib")
        m1_schema_path = os.path.join(self.m1_dir, "feature_schema.json")
        m1_thresh_path = os.path.join(self.m1_dir, "threshold.json")
        if os.path.exists(m1_model_path) and os.path.exists(m1_prep_path):
            self.m1_model = joblib.load(m1_model_path)
            self.m1_preprocessor = joblib.load(m1_prep_path)
            if os.path.exists(m1_schema_path):
                with open(m1_schema_path, "r", encoding="utf-8") as f:
                    self.m1_schema = json.load(f)
            if os.path.exists(m1_thresh_path):
                with open(m1_thresh_path, "r", encoding="utf-8") as f:
                    self.m1_threshold = float(json.load(f).get("selected_optimal_threshold", 0.50))

        # 2. Baseline Model 02
        m2_model_path = os.path.join(self.m2_dir, "xgboost_model.joblib")
        m2_prep_path = os.path.join(self.m2_dir, "preprocessing_pipeline.joblib")
        m2_schema_path = os.path.join(self.m2_dir, "feature_schema.json")
        m2_thresh_path = os.path.join(self.m2_dir, "threshold.json")
        if os.path.exists(m2_model_path) and os.path.exists(m2_prep_path):
            self.m2_model = joblib.load(m2_model_path)
            self.m2_preprocessor = joblib.load(m2_prep_path)
            if os.path.exists(m2_schema_path):
                with open(m2_schema_path, "r", encoding="utf-8") as f:
                    self.m2_schema = json.load(f)
            if os.path.exists(m2_thresh_path):
                with open(m2_thresh_path, "r", encoding="utf-8") as f:
                    self.m2_threshold = float(json.load(f).get("selected_optimal_threshold", 0.50))

        # 3. Baseline Model 03
        m3_model_path = os.path.join(self.m3_dir, "catboost_model.cbm")
        m3_prep_path = os.path.join(self.m3_dir, "preprocessing_pipeline.joblib")
        m3_schema_path = os.path.join(self.m3_dir, "feature_schema.json")
        if os.path.exists(m3_model_path):
            self.m3_model = CatBoostRegressor()
            self.m3_model.load_model(m3_model_path)
            if os.path.exists(m3_prep_path):
                self.m3_preprocessor = joblib.load(m3_prep_path)
            if os.path.exists(m3_schema_path):
                with open(m3_schema_path, "r", encoding="utf-8") as f:
                    self.m3_schema = json.load(f)

        # 4. Improved Model 01
        m1_imp_best = os.path.join(self.m1_imp_dir, "best_model.joblib")
        m1_imp_prep = os.path.join(self.m1_imp_dir, "preprocessing_pipeline.joblib")
        m1_imp_schema_f = os.path.join(self.m1_imp_dir, "feature_schema.json")
        m1_imp_thresh_f = os.path.join(self.m1_imp_dir, "threshold.json")
        if os.path.exists(m1_imp_best) and os.path.exists(m1_imp_prep):
            self.m1_imp_model = joblib.load(m1_imp_best)
            self.m1_imp_preprocessor = joblib.load(m1_imp_prep)
            if os.path.exists(m1_imp_schema_f):
                with open(m1_imp_schema_f, "r", encoding="utf-8") as f:
                    self.m1_imp_schema = json.load(f)
            if os.path.exists(m1_imp_thresh_f):
                with open(m1_imp_thresh_f, "r", encoding="utf-8") as f:
                    self.m1_imp_threshold = float(json.load(f).get("optimal_threshold", 0.35))

        # 5. Improved Model 02
        m2_imp_best = os.path.join(self.m2_imp_dir, "xgboost_model_improved.joblib")
        if not os.path.exists(m2_imp_best):
            m2_imp_best = os.path.join(self.m2_imp_dir, "best_model.joblib")
        m2_imp_prep = os.path.join(self.m2_imp_dir, "preprocessing_pipeline.joblib")
        m2_imp_schema_f = os.path.join(self.m2_imp_dir, "feature_schema.json")
        m2_imp_thresh_f = os.path.join(self.m2_imp_dir, "threshold.json")
        if os.path.exists(m2_imp_best) and os.path.exists(m2_imp_prep):
            self.m2_imp_model = joblib.load(m2_imp_best)
            self.m2_imp_preprocessor = joblib.load(m2_imp_prep)
            if os.path.exists(m2_imp_schema_f):
                with open(m2_imp_schema_f, "r", encoding="utf-8") as f:
                    self.m2_imp_schema = json.load(f)
            if os.path.exists(m2_imp_thresh_f):
                with open(m2_imp_thresh_f, "r", encoding="utf-8") as f:
                    self.m2_imp_threshold = float(json.load(f).get("balanced_operational_threshold", 0.40))

        # 6. Improved Model 03
        m3_imp_best = os.path.join(self.m3_imp_dir, "best_regressor.joblib")
        m3_imp_prep = os.path.join(self.m3_imp_dir, "preprocessing_pipeline.joblib")
        m3_imp_schema_f = os.path.join(self.m3_imp_dir, "feature_schema.json")
        if os.path.exists(m3_imp_best) and os.path.exists(m3_imp_prep):
            self.m3_imp_model = joblib.load(m3_imp_best)
            self.m3_imp_preprocessor = joblib.load(m3_imp_prep)
            if os.path.exists(m3_imp_schema_f):
                with open(m3_imp_schema_f, "r", encoding="utf-8") as f:
                    self.m3_imp_schema = json.load(f)

        # 7. Reference Methodology Model (Random Forest)
        ref_model_path = os.path.join(self.base_dir, "order_creation_reference_pipeline", "routemind_order_creation_random_forest.joblib")
        if os.path.exists(ref_model_path):
            try:
                self.rf_reference_pipeline = joblib.load(ref_model_path)
            except Exception as e:
                print(f"Warning: Could not load reference pipeline: {e}")

    # ==========================================================================
    # BASELINE INFERENCE METHODS
    # ==========================================================================
    def predict_order_creation(self, data: dict) -> dict:
        """Baseline Model 01: Logistic Regression."""
        if self.m1_model is None or self.m1_preprocessor is None:
            raise RuntimeError("Baseline Model 01 artifacts are not loaded.")

        df_input = pd.DataFrame([data])
        required_features = self.m1_schema.get("feature_order") or (self.m1_schema.get("mandatory_numerical_features", []) + self.m1_schema.get("mandatory_categorical_features", []))

        for feat in required_features:
            if feat not in df_input.columns:
                raise ValueError(f"Missing required feature for Baseline Model 01: '{feat}'")

        X_proc = self.m1_preprocessor.transform(df_input[required_features])
        proba = float(self.m1_model.predict_proba(X_proc)[0, 1])
        pred_class = int(proba >= self.m1_threshold)

        risk_category = "Critical Risk" if proba >= 0.70 else ("High Risk" if proba >= self.m1_threshold else ("Moderate Risk" if proba >= 0.30 else "Low Risk"))

        return {
            "model_id": "model_01_order_creation_logistic_regression_baseline",
            "model_version": "baseline",
            "prediction_stage": "order_creation",
            "predicted_class": pred_class,
            "late_delivery_probability": round(proba, 4),
            "selected_threshold": self.m1_threshold,
            "risk_category": risk_category,
            "status": "Late Delivery Expected" if pred_class == 1 else "On-Time / Early Expected"
        }

    def predict_dispatch(self, data: dict) -> dict:
        """Baseline Model 02: XGBoost Classifier."""
        if self.m2_model is None or self.m2_preprocessor is None:
            raise RuntimeError("Baseline Model 02 artifacts are not loaded.")

        df_input = pd.DataFrame([data])
        required_features = self.m2_schema.get("feature_order") or (self.m2_schema.get("mandatory_numerical_features", []) + self.m2_schema.get("mandatory_categorical_features", []))

        for feat in required_features:
            if feat not in df_input.columns:
                raise ValueError(f"Missing required feature for Baseline Model 02: '{feat}'")

        X_proc = self.m2_preprocessor.transform(df_input[required_features])
        proba = float(self.m2_model.predict_proba(X_proc)[0, 1])
        eval_thresh = 0.50
        pred_class = int(proba >= eval_thresh)

        risk_category = "Critical Risk" if proba >= 0.75 else ("High Risk" if proba >= eval_thresh else ("Moderate Risk" if proba >= 0.30 else "Low Risk"))

        return {
            "model_id": "model_02_dispatch_xgboost_baseline",
            "model_version": "baseline",
            "prediction_stage": "dispatch",
            "predicted_class": pred_class,
            "late_delivery_probability": round(proba, 4),
            "selected_threshold": eval_thresh,
            "risk_category": risk_category,
            "status": "Late Delivery Expected" if pred_class == 1 else "On-Time / Early Expected"
        }

    def predict_delay_duration(self, data: dict) -> dict:
        """Baseline Model 03: CatBoost Regressor."""
        if self.m3_model is None:
            raise RuntimeError("Baseline Model 03 artifacts are not loaded.")

        input_copy = dict(data)
        if "Category Name" in input_copy and "Primary_Category" not in input_copy:
            input_copy["Primary_Category"] = input_copy["Category Name"]

        df_input = pd.DataFrame([input_copy])
        required_features = self.m3_schema.get("feature_order") or (self.m3_schema.get("numerical_features", []) + self.m3_schema.get("categorical_features", []))

        for feat in required_features:
            if feat not in df_input.columns:
                raise ValueError(f"Missing required feature for Baseline Model 03: '{feat}'")
            if feat in self.m3_schema.get("categorical_features", []):
                df_input[feat] = df_input[feat].astype(str)

        raw_pred = float(self.m3_model.predict(df_input[required_features])[0])
        scheduled_days = int(input_copy.get("Days for shipment (scheduled)", 2))
        
        # Check if target is Days for shipping (real) or Delay Duration
        if self.m3_schema.get("target") == "Days for shipping (real)":
            predicted_real_days = round(raw_pred, 2)
            delay_prediction = round(predicted_real_days - scheduled_days, 2)
        else:
            delay_prediction = round(raw_pred, 2)
            predicted_real_days = round(scheduled_days + delay_prediction, 2)

        if delay_prediction > 0.20:
            interpretation = "Estimated Late Delivery (Delayed)"
            severity = f"+{delay_prediction:.2f} days late relative to schedule"
        elif delay_prediction < -0.20:
            interpretation = "Estimated Early Delivery (Ahead of Schedule)"
            severity = f"{abs(delay_prediction):.2f} days early relative to schedule"
        else:
            interpretation = "Estimated Exact On-Time Delivery"
            severity = "0 days deviation from schedule"

        return {
            "model_id": "model_03_delay_duration_catboost_baseline",
            "model_version": "baseline",
            "prediction_stage": "transit_routing",
            "predicted_real_days": predicted_real_days,
            "estimated_delay_duration_days": delay_prediction,
            "scheduled_shipping_days": scheduled_days,
            "predicted_delivery_duration_relative_to_scheduled": predicted_real_days,
            "interpretation": interpretation,
            "duration_summary": severity
        }

    # ==========================================================================
    # IMPROVED INFERENCE METHODS
    # ==========================================================================
    def _prepare_improved_m1_features(self, data: dict) -> pd.DataFrame:
        """Prepares and imputes full feature schema for Model 01 Improved."""
        total_qty = float(data.get("Total_Quantity", data.get("Order Item Quantity", 1)))
        total_sales = float(data.get("Total_Sales", data.get("Sales", 100.0)))
        total_discount = float(data.get("Total_Discount", data.get("Order Item Discount", 0.0)))
        max_item_price = float(data.get("Max_Item_Price", data.get("Order Item Product Price", total_sales / max(total_qty, 1.0))))
        mean_item_price = float(data.get("Mean_Item_Price", max_item_price))
        item_count = int(data.get("Item_Count", 1))
        sales_per_item = total_sales / max(total_qty, 1.0)
        discount_rate = total_discount / (total_sales + total_discount + 1e-6)

        row = {
            "Days for shipment (scheduled)": int(data.get("Days for shipment (scheduled)", 4)),
            "Total_Quantity": total_qty,
            "Total_Sales": total_sales,
            "Total_Discount": total_discount,
            "Max_Item_Price": max_item_price,
            "Mean_Item_Price": mean_item_price,
            "Item_Count": item_count,
            "Sales_Per_Item": sales_per_item,
            "Discount_Rate_Order": discount_rate,
            "Order_Hour": int(data.get("Order_Hour", 12)),
            "Order_DayOfWeek": int(data.get("Order_DayOfWeek", 2)),
            "Order_Month": int(data.get("Order_Month", 6)),
            "Is_Weekend": int(data.get("Is_Weekend", 0)),
            "Order_Quarter": int(data.get("Order_Quarter", 2)),
            "Type": str(data.get("Type", "DEBIT")),
            "Order Region": str(data.get("Order Region", "Western Europe")),
            "Market": str(data.get("Market", "Europe")),
            "Customer Segment": str(data.get("Customer Segment", "Consumer")),
            "Primary_Category": str(data.get("Primary_Category", data.get("Category Name", "Sporting Goods"))),
            "Primary_Department": str(data.get("Primary_Department", data.get("Department Name", "Fitness")))
        }
        return pd.DataFrame([row])

    def predict_order_creation_improved(self, data: dict, threshold: float = None) -> dict:
        """Improved Model 01: LightGBM / Enhanced Classifier."""
        if self.m1_imp_model is None or self.m1_imp_preprocessor is None:
            raise RuntimeError("Model 01 Improved artifacts are not loaded.")

        df_row = self._prepare_improved_m1_features(data)
        required_features = self.m1_imp_schema["feature_order"]
        X_proc = self.m1_imp_preprocessor.transform(df_row[required_features])

        proba = float(self.m1_imp_model.predict_proba(X_proc)[0, 1])
        active_threshold = threshold if threshold is not None else self.m1_imp_threshold
        pred_class = int(proba >= active_threshold)

        risk_category = "Critical Risk" if proba >= 0.70 else ("High Risk" if proba >= active_threshold else ("Moderate Risk" if proba >= 0.30 else "Low Risk"))

        return {
            "model_id": "model_01_order_creation_improved_lightgbm",
            "model_version": "improved",
            "prediction_stage": "order_creation",
            "predicted_class": pred_class,
            "late_delivery_probability": round(proba, 4),
            "selected_threshold": active_threshold,
            "risk_category": risk_category,
            "status": "Late Delivery Expected" if pred_class == 1 else "On-Time / Early Expected"
        }

    def _prepare_improved_m2_features(self, data: dict) -> pd.DataFrame:
        """Prepares and imputes full feature schema for Model 02 Improved."""
        qty = float(data.get("Order Item Quantity", 1))
        sales = float(data.get("Sales", 100.0))
        discount = float(data.get("Order Item Discount", 0.0))
        product_price = float(data.get("Order Item Product Price", sales / max(qty, 1.0)))
        item_id = int(data.get("Order Item Id", 1))
        sales_per_item = sales / max(qty, 1.0)
        sched_days = int(data.get("Days for shipment (scheduled)", 4))
        sched_x_items = sched_days * qty

        row = {
            "Days for shipment (scheduled)": sched_days,
            "Order Item Quantity": qty,
            "Sales": sales,
            "Order Item Discount": discount,
            "Order Item Product Price": product_price,
            "Order Item Id": item_id,
            "Sales_Per_Item": sales_per_item,
            "Scheduled_Days_x_Item_Count": sched_x_items,
            "Order_Hour": int(data.get("Order_Hour", 12)),
            "Order_DayOfWeek": int(data.get("Order_DayOfWeek", 2)),
            "Order_Month": int(data.get("Order_Month", 6)),
            "Is_Weekend": int(data.get("Is_Weekend", 0)),
            "Shipping Mode": str(data.get("Shipping Mode", "Standard Class")),
            "Order Status": str(data.get("Order Status", "COMPLETE")),
            "Order Region": str(data.get("Order Region", "Western Europe")),
            "Market": str(data.get("Market", "Europe")),
            "Customer Segment": str(data.get("Customer Segment", "Consumer")),
            "Primary_Category": str(data.get("Primary_Category", data.get("Category Name", "Sporting Goods")))
        }
        return pd.DataFrame([row])

    def predict_dispatch_improved(self, data: dict, threshold: float = None) -> dict:
        """Improved Model 02: Tuned XGBoost Classifier with operational threshold."""
        if self.m2_imp_model is None or self.m2_imp_preprocessor is None:
            raise RuntimeError("Model 02 Improved artifacts are not loaded.")

        df_row = self._prepare_improved_m2_features(data)
        required_features = self.m2_imp_schema["feature_order"]
        X_proc = self.m2_imp_preprocessor.transform(df_row[required_features])

        proba = float(self.m2_imp_model.predict_proba(X_proc)[0, 1])
        active_threshold = threshold if threshold is not None else self.m2_imp_threshold
        pred_class = int(proba >= active_threshold)

        risk_category = "Critical Risk" if proba >= 0.75 else ("High Risk" if proba >= active_threshold else ("Moderate Risk" if proba >= 0.30 else "Low Risk"))

        return {
            "model_id": "model_02_dispatch_improved_xgboost",
            "model_version": "improved",
            "prediction_stage": "dispatch",
            "predicted_class": pred_class,
            "late_delivery_probability": round(proba, 4),
            "selected_threshold": active_threshold,
            "risk_category": risk_category,
            "status": "Late Delivery Expected" if pred_class == 1 else "On-Time / Early Expected"
        }

    def _prepare_improved_m3_features(self, data: dict) -> pd.DataFrame:
        """Prepares and imputes full feature schema for Model 03 Improved."""
        qty = float(data.get("Order Item Quantity", 1))
        sales = float(data.get("Sales", 100.0))
        discount = float(data.get("Order Item Discount", 0.0))
        product_price = float(data.get("Order Item Product Price", sales / max(qty, 1.0)))
        item_id = int(data.get("Order Item Id", 1))
        sales_per_item = sales / max(qty, 1.0)
        sched_days = int(data.get("Days for shipment (scheduled)", 4))
        sched_x_items = sched_days * qty

        row = {
            "Days for shipment (scheduled)": sched_days,
            "Order Item Quantity": qty,
            "Sales": sales,
            "Order Item Discount": discount,
            "Order Item Product Price": product_price,
            "Order Item Id": item_id,
            "Sales_Per_Item": sales_per_item,
            "Scheduled_Days_x_Item_Count": sched_x_items,
            "Order_Hour": int(data.get("Order_Hour", 12)),
            "Order_DayOfWeek": int(data.get("Order_DayOfWeek", 2)),
            "Order_Month": int(data.get("Order_Month", 6)),
            "Is_Weekend": int(data.get("Is_Weekend", 0)),
            "Shipping Mode": str(data.get("Shipping Mode", "Standard Class")),
            "Order Region": str(data.get("Order Region", "Western Europe")),
            "Market": str(data.get("Market", "Europe")),
            "Customer Segment": str(data.get("Customer Segment", "Consumer")),
            "Primary_Category": str(data.get("Primary_Category", data.get("Category Name", "Sporting Goods"))),
            "Primary_Department": str(data.get("Primary_Department", data.get("Department Name", "Fitness")))
        }
        return pd.DataFrame([row])

    def predict_delay_duration_improved(self, data: dict) -> dict:
        """Improved Model 03: Random Forest / Tuned CatBoost Regressor."""
        if self.m3_imp_model is None or self.m3_imp_preprocessor is None:
            raise RuntimeError("Model 03 Improved artifacts are not loaded.")

        df_row = self._prepare_improved_m3_features(data)
        required_features = self.m3_imp_schema["feature_order"]
        X_proc = self.m3_imp_preprocessor.transform(df_row[required_features])

        delay_prediction = float(self.m3_imp_model.predict(X_proc)[0])
        scheduled_days = int(data.get("Days for shipment (scheduled)", 4))
        predicted_delivery_duration = round(scheduled_days + delay_prediction, 2)

        if delay_prediction > 0.20:
            interpretation = "Estimated Late Delivery (Delayed)"
            severity = f"+{delay_prediction:.2f} days late relative to schedule"
        elif delay_prediction < -0.20:
            interpretation = "Estimated Early Delivery (Ahead of Schedule)"
            severity = f"{abs(delay_prediction):.2f} days early relative to schedule"
        else:
            interpretation = "Estimated Exact On-Time Delivery"
            severity = "0 days deviation from schedule"

        return {
            "model_id": "model_03_delay_duration_improved_rf_catboost",
            "model_version": "improved",
            "prediction_stage": "transit_routing",
            "estimated_delay_duration_days": round(delay_prediction, 2),
            "scheduled_shipping_days": scheduled_days,
            "predicted_delivery_duration_relative_to_scheduled": predicted_delivery_duration,
            "interpretation": interpretation,
            "duration_summary": severity
        }

    # ==========================================================================
    # COMPREHENSIVE CONTROL TOWER EVALUATION (BASELINE & IMPROVED)
    # ==========================================================================
    def evaluate_shipment_control_tower(self, shipment_record: dict, version: str = "improved") -> dict:
        """
        Runs all three models independently for a comprehensive shipment assessment.
        Parameter 'version' can be 'improved' (default) or 'baseline'.
        """
        results = {
            "order_id": shipment_record.get("Order Id", "N/A"),
            "timestamp": shipment_record.get("order date (DateOrders)", shipment_record.get("order_date", "N/A")),
            "evaluation_engine": version,
            "control_tower_summary": {}
        }

        if version == "baseline":
            try:
                results["model_01_order_creation"] = self.predict_order_creation(shipment_record)
            except Exception as e:
                results["model_01_order_creation"] = {"error": str(e)}

            try:
                results["model_02_dispatch"] = self.predict_dispatch(shipment_record)
            except Exception as e:
                results["model_02_dispatch"] = {"error": str(e)}

            try:
                results["model_03_delay_duration"] = self.predict_delay_duration(shipment_record)
            except Exception as e:
                results["model_03_delay_duration"] = {"error": str(e)}
        else:
            try:
                results["model_01_order_creation"] = self.predict_order_creation_improved(shipment_record)
            except Exception as e:
                results["model_01_order_creation"] = {"error": str(e)}

            try:
                results["model_02_dispatch"] = self.predict_dispatch_improved(shipment_record)
            except Exception as e:
                results["model_02_dispatch"] = {"error": str(e)}

            try:
                results["model_03_delay_duration"] = self.predict_delay_duration_improved(shipment_record)
            except Exception as e:
                results["model_03_delay_duration"] = {"error": str(e)}

        # Synthesize Control Tower prescriptive action
        m1_risk = results.get("model_01_order_creation", {}).get("risk_category", "Unknown")
        m2_risk = results.get("model_02_dispatch", {}).get("risk_category", "Unknown")
        m3_delay = results.get("model_03_delay_duration", {}).get("estimated_delay_duration_days", 0.0)

        if m2_risk in ["High Risk", "Critical Risk"] or m3_delay > 1.0:
            recommended_action = "EXPEDITE: Priority carrier upgrade or alternate hub routing required immediately."
            alert_level = "RED"
        elif m1_risk in ["High Risk", "Critical Risk"] or m3_delay > 0.3:
            recommended_action = "MONITOR: Schedule fulfillment priority at warehouse dock; alert carrier."
            alert_level = "YELLOW"
        else:
            recommended_action = "STANDARD: Order progressing normally within scheduled delivery window."
            alert_level = "GREEN"

        results["control_tower_summary"] = {
            "alert_level": alert_level,
            "recommended_action": recommended_action,
            "overall_status": "HIGH RISK" if alert_level == "RED" else ("WATCH" if alert_level == "YELLOW" else "NORMAL")
        }

        # Automatically persist assessment to database
        try:
            self.db_adapter.record_prediction({
                "shipment_id": shipment_record.get("Order Id", "N/A"),
                "model_id": f"control_tower_{version}",
                "prediction_stage": "control_tower",
                "late_delivery_probability": float(results.get("model_01_order_creation", {}).get("late_delivery_probability", 0.5)),
                "predicted_class": 1 if alert_level in ["RED", "YELLOW"] else 0,
                "selected_threshold": 0.40,
                "risk_category": m1_risk,
                "alert_level": alert_level
            }, shipment_record)
        except Exception:
            pass

        return results

    # ==========================================================================
    # LIVE EVENT & STREAMING METHODOLOGY (REFERENCE NOTEBOOK CELL 6 & 20)
    # ==========================================================================
    def predict_live_event(self, event_payload: dict) -> dict:
        """
        Ingests a live event, scores it with Random Forest and XGBoost,
        and saves it to the tracking database.
        """
        rf_pipe = self.rf_reference_pipeline

        # Use predict_dispatch_improved to obtain genuine tuned XGBoost probabilities
        class XGBWrapper:
            def __init__(self, svc):
                self.svc = svc
            def predict_proba(self, df):
                d = df.iloc[0].to_dict()
                try:
                    res = self.svc.predict_dispatch_improved(d)
                    p = float(res.get("late_delivery_probability", 0.5))
                    return np.array([[1.0 - p, p]])
                except Exception:
                    return np.array([[0.5, 0.5]])

        xgb_pipe = XGBWrapper(self)

        scoring_result = self.live_manager.add_new_shipment_event(
            event_payload=event_payload,
            rf_pipeline=rf_pipe,
            xgb_pipeline=xgb_pipe,
            rf_threshold=0.33,
            xgb_threshold=self.m2_imp_threshold
        )

        try:
            event_record = dict(event_payload)
            event_record.update(scoring_result)
            self.db_adapter.record_shipment_event(event_record)
        except Exception as e:
            print(f"Warning: Failed to persist shipment event to database: {e}")

        return scoring_result

    def batch_predict(self, shipments: list[dict], version: str = "improved") -> list[dict]:
        """Runs batch predictions across a list of shipment records."""
        results = []
        for ship in shipments:
            results.append(self.evaluate_shipment_control_tower(ship, version=version))
        return results

    def get_registry_catalog(self) -> dict:
        """Retrieves registered models from models/registry.json."""
        reg_file = os.path.join(self.base_dir, "registry.json")
        if os.path.exists(reg_file):
            try:
                with open(reg_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                return {"error": str(e)}
        return {"models": []}

# Singleton instance
service = LogisticsPredictionService()
