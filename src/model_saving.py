"""model_saving.py - Phase 13: versioned saving of the complete inference bundle."""
import datetime as dt
import hashlib
import json
import os
import shutil
import joblib

def file_fingerprint(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()

def _next_version(stage_dir, wanted):
    """Never overwrite an existing version: bump the patch number if the folder already exists."""
    major, minor, patch = (int(x) for x in wanted.split("."))
    while os.path.exists(os.path.join(stage_dir, "versions", f"v{major}.{minor}.{patch}")):
        patch += 1
    return f"{major}.{minor}.{patch}"

def save_stage_model(stage, bundle, metadata, schema, models_dir, version="1.0.0", set_current=True):
    """bundle: dict with pipeline, calibrator, threshold, risk_cutoffs, ... Saves into versions/vX.Y.Z/ and
    refreshes the 'current' copy in models/<stage>/ (the previous current model is already preserved in versions/)."""
    stage_dir = os.path.join(models_dir, stage)
    version = _next_version(stage_dir, version)
    vdir = os.path.join(stage_dir, "versions", f"v{version}")
    os.makedirs(vdir, exist_ok=True)
    metadata = {**metadata, "model_version": version, "prediction_stage": stage,
                "trained_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    bundle = {**bundle, "metadata": metadata, "feature_schema": schema}
    joblib.dump(bundle, os.path.join(vdir, "best_model.joblib"), compress=3)
    for name, obj in [("feature_schema.json", schema), ("model_metadata.json", metadata)]:
        with open(os.path.join(vdir, name), "w") as f:
            json.dump(obj, f, indent=2, default=str)
    if set_current:      # candidates are saved with set_current=False so the production/current files are never touched
        for name in ["best_model.joblib", "feature_schema.json", "model_metadata.json"]:
            shutil.copy2(os.path.join(vdir, name), os.path.join(stage_dir, name))
    return version, vdir

def write_dispatch_requirements(models_dir):
    """Dispatch model is BLOCKED (no genuine dispatch data). Write the future schema; NO model artifact is saved."""
    d = os.path.join(models_dir, "dispatch")
    os.makedirs(d, exist_ok=True)
    spec = {
        "status": "NOT_TRAINED",
        "reason": "DataCo has no genuine dispatch-time data. 'shipping date (DateOrders)' equals order date + actual shipping days "
                  "(derived from the delivery outcome), so it cannot be used as a dispatch timestamp.",
        "future_feature_schema": {
            "order_creation_features": "all features of models/order_creation/feature_schema.json",
            "required_new_dispatch_fields": {
                "actual_dispatch_timestamp": "datetime recorded by the warehouse/WMS when the parcel leaves (orders_shipments.actual_shipping_date, but as a full timestamp)",
                "dispatch_year/month/day/weekday/hour": "derived from actual_dispatch_timestamp",
                "hours_to_dispatch": "actual_dispatch_timestamp - order_date (hours)",
                "carrier_name": "carrier assigned at dispatch (orders_shipments.carrier_name)",
                "warehouse_id / dispatch_location": "origin facility (not in DataCo)",
                "dispatch_processing_status / delays": "e.g. picking/packing delays (shipment_events)"},
            "must_not_include": ["actual delivery date", "Days for shipping (real)", "Delivery Status", "any value created after dispatch"]},
        "data_required_to_train": "Historical shipments with a verified dispatch event timestamp and later actual delivery outcome; "
                                  "snapshot features must be taken at dispatch time (e.g. from shipment_events), then split chronologically by order group.",
    }
    with open(os.path.join(d, "dispatch_requirements.json"), "w") as f:
        json.dump(spec, f, indent=2)
    return spec
