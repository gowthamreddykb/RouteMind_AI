"""prediction.py - Phase 14/15: inference API for the Flask app. NEVER trains anything.

    from prediction import predict_at_order_creation, predict_at_dispatch
    result = predict_at_order_creation({...raw order fields...}, shipment_id="SHP10025")

The model bundle is loaded once and cached. The saved pipeline contains feature engineering + preprocessing +
XGBoost, so callers pass RAW order fields (DataCo column names). Missing/unexpected fields raise ValidationError.
Actual delivery information is never needed and never accepted.
"""
import datetime as dt
import json
import os
import sys
import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, os.path.dirname(__file__))      # so the pickled feature function can be imported
from load_data import MODELS
from feature_engineering import parse_order_date
from shap_explainability import explain_rows, augment

ID_KEYS = ("shipment_id", "order_id")               # identifiers: allowed in input, never used as features
EXPLANATION_NOTE = ("SHAP contributions (log-odds of the XGBoost model) explain how the model used each feature; "
                    "they do not prove real-world causation.")

class ValidationError(ValueError):
    """Raised when incoming data does not match the saved feature schema."""

class ModelUnavailableError(RuntimeError):
    """Raised when a stage has no valid trained model (e.g. dispatch)."""

_CACHE = {}

def _resolve_path(stage, models_dir=None, version=None):
    """explicit version > registry production model > model_01 / stage files."""
    if not models_dir:
        models_dir = MODELS
    if os.path.exists(os.path.join(models_dir, "models")):
        models_dir = os.path.join(models_dir, "models")
    if version:
        v_path = os.path.join(models_dir, stage, "versions", f"v{version}", "best_model.joblib")
        if os.path.exists(v_path):
            return v_path
    reg = os.path.join(models_dir, "registry.json")
    if os.path.exists(reg):
        with open(reg, "r") as f:
            for m in json.load(f).get("models", []):
                if m.get("prediction_stage") == stage and (m.get("role") == "production" or m.get("is_active")):
                    p = os.path.join(models_dir, m.get("artifact_location", ""))
                    if os.path.exists(p):
                        return p
    candidates = [
        os.path.join(models_dir, "model_01", "logistic_regression_pipeline.joblib"),
        os.path.join(models_dir, "model_01_improved", "best_model.joblib"),
        os.path.join(models_dir, "model_01", "logistic_regression_model.joblib"),
        os.path.join(models_dir, stage, "best_model.joblib")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.join(models_dir, stage, "best_model.joblib")

def load_model(stage="order_creation", models_dir=None, reload=False, version=None):
    if not models_dir:
        models_dir = MODELS
    if os.path.exists(os.path.join(models_dir, "models")):
        models_dir = os.path.join(models_dir, "models")
    path = _resolve_path(stage, models_dir, version)
    key = (stage, os.path.abspath(path))
    if reload or key not in _CACHE:
        if not os.path.exists(path):
            raise ModelUnavailableError(f"No trained model for stage '{stage}' at {path}.")
        raw_obj = joblib.load(path)
        if isinstance(raw_obj, dict) and "pipeline" in raw_obj:
            _CACHE[key] = raw_obj
        else:
            # Wrap standalone scikit-learn Pipeline
            meta_p = os.path.join(models_dir, "model_01", "model_metadata.json")
            schema_p = os.path.join(models_dir, "model_01", "feature_schema.json")
            thresh_p = os.path.join(models_dir, "model_01", "threshold.json")
            meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {"model_version": "1.0.0", "algorithm": "Logistic Regression"}
            schema = json.load(open(schema_p)) if os.path.exists(schema_p) else {}
            thresh = json.load(open(thresh_p)) if os.path.exists(thresh_p) else {}

            required = schema.get("feature_order") or (schema.get("mandatory_numerical_features", []) + schema.get("mandatory_categorical_features", []))
            numeric = schema.get("mandatory_numerical_features", ["Days for shipment (scheduled)", "Order Item Quantity", "Sales"])
            schema_dict = {
                "required_raw_fields": required,
                "numeric_raw_fields": numeric,
                "date_field": schema.get("date_field", "order date (DateOrders)")
            }
            opt_thresh = float(thresh.get("selected_optimal_threshold") or schema.get("optimal_threshold") or 0.40)
            _CACHE[key] = {
                "pipeline": raw_obj,
                "metadata": meta,
                "feature_schema": schema_dict,
                "threshold": opt_thresh,
                "risk_cutoffs": {"low": 0.35, "medium": 0.50, "high": 0.65},
                "calibrator": None
            }
    return _CACHE[key]

def risk_level(p, cutoffs):
    return "HIGH" if p >= cutoffs["high"] else ("MEDIUM" if p >= cutoffs["medium"] else "LOW")

def _validate(records, schema):
    """Returns a DataFrame of raw fields. Raises ValidationError listing every problem."""
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, (list, tuple)) or len(records) == 0:
        raise ValidationError("Input must be a non-empty dict or list of dicts.")
    required = schema["required_raw_fields"]; problems, rows = [], []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            problems.append(f"record {i}: must be a dict"); continue
        data = {k: v for k, v in rec.items() if k not in ID_KEYS}
        # Map Category Name alias to Primary Category if needed
        if "Primary Category" in required and "Primary Category" not in data and "Category Name" in data:
            data["Primary Category"] = data["Category Name"]
        if "Category Name" in required and "Category Name" not in data and "Primary Category" in data:
            data["Category Name"] = data["Primary Category"]

        miss = [f for f in required if f not in data]
        ALLOWED_METADATA = {
            "Order Country", "Department Name", "Product Name", "Order Item Product Price",
            "Customer Segment", "Customer City", "Customer Country", "Customer State",
            "Order Item Discount Rate", "order date (DateOrders)", "Category Name",
            "Primary Category", "Order-to-Ship Time", "shipment_id", "order_id"
        }
        LEAKAGE_FIELDS = {"Late_delivery_risk", "Delivery Status", "Days for shipping (real)"}
        extra = [k for k in data if k not in required and k not in ALLOWED_METADATA]
        leak = [k for k in data if k in LEAKAGE_FIELDS]
        if miss: problems.append(f"record {i}: missing required fields {miss}")
        if extra: problems.append(f"record {i}: unexpected fields {extra} (delivery-outcome or unapproved fields are not accepted)")
        if leak: problems.append(f"record {i}: unexpected leakage fields {leak}")
        for f in required:
            v = data.get(f)
            if f in data and (v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and not v.strip())):
                problems.append(f"record {i}: '{f}' is empty (required business data is never auto-filled)")
        for f in schema["numeric_raw_fields"]:
            if f in data and data[f] is not None:
                try:
                    float(data[f])
                except (TypeError, ValueError):
                    problems.append(f"record {i}: '{f}' must be numeric, got {data[f]!r}")
        for f in ("Order Item Quantity", "Sales", "Order Item Product Price", "Days for shipment (scheduled)"):
            if f in data and isinstance(data[f], (int, float)) and data[f] < 0:
                problems.append(f"record {i}: '{f}' cannot be negative")
        dcol = schema["date_field"]
        if dcol in data and data[dcol] is not None and pd.isna(parse_order_date(pd.Series([data[dcol]])).iloc[0]):
            problems.append(f"record {i}: '{dcol}' is not a valid date (expected e.g. '1/31/2018 22:56' or ISO format)")
        rows.append({f: data.get(f) for f in required})
    if problems:
        raise ValidationError("; ".join(problems))
    return pd.DataFrame(rows)

def _unknown_categories(pipeline, raw_df):
    """Lists category values never seen in training (they are handled safely by the encoder)."""
    try:
        if hasattr(pipeline, "named_steps") and "front" in pipeline.named_steps:
            feat = pipeline.named_steps["front"].named_steps["features"].transform(augment(pipeline, raw_df))
            enc = pipeline.named_steps["front"].named_steps["prep"].named_transformers_["cat"].named_steps["onehot"]
            cat_cols = pipeline.named_steps["front"].named_steps["prep"].transformers_[1][2]
            out = []
            for i in range(len(feat)):
                out.append({c: feat.iloc[i][c] for c, known in zip(cat_cols, enc.categories_)
                            if pd.notna(feat.iloc[i][c]) and feat.iloc[i][c] not in set(known)})
            return out
    except Exception:
        pass
    return [{}] * len(raw_df)

def _predict(stage, records, shipment_ids, explain, top_k, models_dir, version=None):
    bundle = load_model(stage, models_dir, version=version)
    meta, schema = bundle["metadata"], bundle["feature_schema"]
    single = isinstance(records, dict)
    raw = _validate(records, schema)
    n = len(raw)
    ids = shipment_ids if isinstance(shipment_ids, (list, tuple)) else [shipment_ids] * n
    recs = [records] if single else list(records)
    ids = [ids[i] if ids[i] is not None else recs[i].get("shipment_id", recs[i].get("order_id")) for i in range(n)]
    pipe = bundle["pipeline"]
    p_raw = pipe.predict_proba(raw)[:, 1]
    p = np.clip(bundle["calibrator"].transform(p_raw), 0.0, 1.0) if bundle.get("calibrator") else p_raw
    try:
        expl = explain_rows(pipe, raw, top_k) if explain else [None] * n
    except Exception:
        expl = [None] * n
    unknown = _unknown_categories(pipe, raw)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    results = []
    for i in range(n):
        model_name = meta.get("model_name") or meta.get("algorithm") or "Model 01: Logistic Regression Classifier"
        model_version = meta.get("model_version") or meta.get("version", "1.0.0")
        results.append({
            "shipment_id": ids[i], "prediction_stage": stage, "model_name": model_name,
            "model_version": model_version, "late_delivery_probability": float(p[i]),
            "raw_model_probability": float(p_raw[i]), "predicted_class": int(p[i] >= bundle["threshold"]),
            "decision_threshold": bundle["threshold"], "risk_level": risk_level(p[i], bundle["risk_cutoffs"]),
            "prediction_status": "PREDICTED", "scoring_timestamp": now,
            "explanations": None if expl[i] is None else [d["feature"] for d in expl[i]["top_features"]],
            "explanation_details": expl[i], "explanation_note": EXPLANATION_NOTE,
            "unknown_categories": unknown[i],
            # API-contract aliases (Phase 12.2)
            "predicted_probability": float(p[i]), "risk_percentage": round(float(p[i]) * 100, 2), "prediction_timestamp": now,
            "top_risk_factors": [] if expl[i] is None else [{**d, "business_explanation": _business_text(d)} for d in expl[i]["top_features"]]})
    return results[0] if single else results

LABELS = {"scheduled_days": "Scheduled shipping days", "order_value": "Order value", "Shipping Mode": "Shipping mode", "Order Region": "Destination region",
          "Order Country": "Destination country", "Category Name": "Product category", "Customer Segment": "Customer segment", "order_hour": "Order hour",
          "order_day_of_week": "Order weekday", "order_month": "Order month", "order_year": "Order year", "Type": "Payment type", "Market": "Market",
          "Customer City": "Customer city", "Customer State": "Customer state", "Product Name": "Product", "Department Name": "Department",
          "Order Item Quantity": "Item quantity", "Order Item Product Price": "Unit price", "Order Item Discount Rate": "Discount rate", "is_weekend": "Weekend order"}

def _business_text(d):
    word = "raises" if d["shap_contribution"] > 0 else "lowers"
    return f"{LABELS.get(d['feature'], d['feature'])} ({d['feature_value']}) {word} the model's late-delivery risk estimate (association, not proven cause)."

def predict_at_order_creation(records, shipment_id=None, explain=True, top_k=3, models_dir=MODELS, version=None):
    """Score one order (dict) or many (list of dicts) at ORDER CREATION. Returns a dict (or list of dicts)."""
    return _predict("order_creation", records, shipment_id, explain, top_k, models_dir, version)

def predict_order_creation_api(payload, shipment_id=None, store=None, models_dir=MODELS, explain=True, version=None):
    """Flask-facing wrapper: NEVER raises, NEVER fabricates a prediction. Failures return a controlled error dict and are logged."""
    base = {"shipment_id": shipment_id or (payload.get("shipment_id") if isinstance(payload, dict) else None), "prediction_stage": "order_creation",
            "predicted_probability": None, "risk_percentage": None, "risk_level": None, "decision_threshold": None, "model_version": None,
            "prediction_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(), "top_risk_factors": []}
    try:
        r = predict_at_order_creation(payload, shipment_id=shipment_id, explain=explain, models_dir=models_dir, version=version)
        resp = {k: r.get(k) for k in ["shipment_id", "prediction_stage", "model_name", "predicted_probability", "risk_percentage", "risk_level", "decision_threshold",
                                  "model_version", "prediction_timestamp", "top_risk_factors", "prediction_status", "predicted_class", "unknown_categories"]}
        if store is not None:
            store.log_prediction(resp, features=payload)
        return resp
    except ValidationError as e:
        code, msg = "VALIDATION_ERROR", str(e)
    except ModelUnavailableError as e:
        code, msg = "MODEL_UNAVAILABLE", str(e)
    except Exception as e:                                  # unexpected: keep the application running safely
        code, msg = "INTERNAL_ERROR", f"{type(e).__name__}: {e}"
    if store is not None:
        store.log_failure(base["shipment_id"], "order_creation", code, msg)
    return {**base, "prediction_status": "ERROR", "error": {"code": code, "message": msg}}

def predict_at_dispatch(records, shipment_id=None, explain=True, top_k=3, models_dir=MODELS, version=None):
    """Enabled only if a valid dispatch model exists. In this project it does NOT (no genuine dispatch data)."""
    path = os.path.join(models_dir, "dispatch", "best_model.joblib")
    if not os.path.exists(path):
        req = os.path.join(models_dir, "dispatch", "dispatch_requirements.json")
        raise ModelUnavailableError("Dispatch-stage prediction is disabled: no valid dispatch model exists because the "
                                    f"DataCo data has no genuine dispatch-time information. See {req}.")
    return _predict("dispatch", records, shipment_id, explain, top_k, models_dir)

# ------------------------------------------------------------------ database preparation (MySQL)
def to_database_rows(result, model_id, shipment_db_id):
    """Maps one prediction to INSERT-ONLY rows for model_scores and risk_factors (history is never overwritten).
    risk_factors rows need the new score_id, which MySQL returns after inserting the model_scores row."""
    score = {"shipment_id": shipment_db_id, "model_id": model_id, "predicted_probability": result["late_delivery_probability"],
             "predicted_class": result["predicted_class"], "risk_level": result["risk_level"],
             "decision_threshold": result["decision_threshold"], "scoring_timestamp": result["scoring_timestamp"],
             "prediction_notes": f"stage={result['prediction_stage']}; {result['explanation_note']}"}
    factors = []
    for d in (result["explanation_details"] or {}).get("top_features", []):
        factors.append({"feature_name": d["feature"], "feature_value": str(d["feature_value"]),
                        "contribution_value": d["shap_contribution"],
                        "contribution_direction": "INCREASES_RISK" if d["shap_contribution"] > 0 else "DECREASES_RISK",
                        "explanation": f"{d['feature']} = {d['feature_value']} {d['direction'].replace('_', ' ')} (model contribution, not causation)"})
    return {"model_scores": score, "risk_factors": factors}

def registry_row(metadata, model_path):
    """Row for model_registry. Binary stays on disk; only its path + metrics go into MySQL."""
    t = metadata["test_metrics"]
    return {"model_name": f"RouteMind {metadata['prediction_stage']} {metadata['algorithm']}", "model_version": metadata["model_version"],
            "algorithm": metadata["algorithm"], "target_column": metadata["target_column"],
            "feature_list": json.dumps(metadata["feature_names_raw"]), "model_file_path": model_path,
            "preprocessing_version": metadata["model_version"], "training_rows": metadata["training_rows"],
            "accuracy": t["accuracy"], "precision_score": t["precision"], "recall_score": t["recall"], "f1_score": t["f1"],
            "roc_auc": t["roc_auc"], "pr_auc": t["pr_auc"], "decision_threshold": metadata["decision_threshold"],
            "trained_at": metadata["trained_at"], "is_active": 1}
