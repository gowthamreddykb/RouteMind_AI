"""flask_example.py - minimal Flask service showing how RouteMind AI calls the ML layer (no training happens here).

    set FLASK_APP=src/flask_example.py   &   python -m flask run
    POST /api/predict/order-creation   body = raw order fields (+ optional shipment_id)
    POST /api/outcomes                 body = shipment_id, scheduled_delivery_ts, actual_delivery_ts[, delay_reason]
    GET  /api/model                    production model info from the registry
Predictions/failures/outcomes are stored through monitoring.MonitoringStore (swap for MySQL in the real app; see sql/monitoring_mysql.sql).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from flask import Flask, jsonify, request
import prediction as PR, monitoring as MON, model_registry as MR
from load_data import MODELS, ROOT

def create_app(models_dir=MODELS, db_path=os.path.join(ROOT, "monitoring.sqlite")):
    app = Flask(__name__); store = MON.MonitoringStore(db_path)
    STATUS = {"VALIDATION_ERROR": 422, "MODEL_UNAVAILABLE": 503, "INTERNAL_ERROR": 500}

    @app.post("/api/predict/order-creation")
    def predict():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"prediction_status": "ERROR", "error": {"code": "VALIDATION_ERROR", "message": "JSON object body required"}}), 422
        resp = PR.predict_order_creation_api(dict(payload), store=store, models_dir=models_dir)
        return jsonify(resp), 200 if resp["prediction_status"] == "PREDICTED" else STATUS.get(resp["error"]["code"], 500)

    @app.post("/api/outcomes")
    def outcome():
        b = request.get_json(silent=True) or {}
        try:
            o = store.record_outcome(b["shipment_id"], b["scheduled_delivery_ts"], b["actual_delivery_ts"], b.get("delay_reason"))
        except (KeyError, ValueError) as e:
            return jsonify({"error": f"invalid outcome payload: {e}"}), 422
        return jsonify({"shipment_id": b["shipment_id"], "actual_outcome": o}), 201

    @app.get("/api/model")
    def model_info():
        m = MR.production("order_creation", models_dir)
        return (jsonify({k: m[k] for k in ["model_id", "model_version", "approval_status", "decision_threshold", "deployed_at"]}), 200) if m else (jsonify({"error": "no production model"}), 503)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})
    return app
