import json
import pytest
from app import app
from prediction_service import LogisticsPredictionService

def test_prediction_service_standalone():
    print("\n--- Testing Prediction Service Directly (Baseline & Improved) ---")
    service = LogisticsPredictionService()

    # 1. Baseline Model 01
    payload_m1 = {
        "Days for shipment (scheduled)": 2,
        "Order Item Quantity": 4,
        "Sales": 450.0,
        "Shipping Mode": "First Class",
        "Order Region": "South Asia",
        "Type": "TRANSFER",
        "Market": "Pacific Asia",
        "Primary Category": "Sporting Goods"
    }
    res_m1 = service.predict_order_creation(payload_m1)
    print("Baseline Model 01 Direct Result:", res_m1["model_id"], res_m1["risk_category"])
    assert "predicted_class" in res_m1
    assert "late_delivery_probability" in res_m1

    # 1b. Improved Model 01
    res_m1_imp = service.predict_order_creation_improved(payload_m1)
    print("Improved Model 01 Direct Result:", res_m1_imp["model_id"], res_m1_imp["risk_category"], f"P={res_m1_imp['late_delivery_probability']}")
    assert "predicted_class" in res_m1_imp
    assert "late_delivery_probability" in res_m1_imp

    # 2. Baseline Model 02
    payload_m2 = {
        "Days for shipment (scheduled)": 1,
        "Order-to-Ship Time": 2.5,
        "Shipping Mode": "First Class",
        "Order Region": "Western Europe",
        "Market": "Europe",
        "Department Name": "Fitness",
        "Customer Segment": "Consumer"
    }
    res_m2 = service.predict_dispatch(payload_m2)
    print("Baseline Model 02 Direct Result:", res_m2["model_id"], res_m2["risk_category"])
    assert "predicted_class" in res_m2
    assert "late_delivery_probability" in res_m2

    # 2b. Improved Model 02
    res_m2_imp = service.predict_dispatch_improved(payload_m2)
    print("Improved Model 02 Direct Result:", res_m2_imp["model_id"], res_m2_imp["risk_category"], f"P={res_m2_imp['late_delivery_probability']}")
    assert "predicted_class" in res_m2_imp
    assert "late_delivery_probability" in res_m2_imp

    # 3. Baseline Model 03
    payload_m3 = {
        "Days for shipment (scheduled)": 4,
        "Order-to-Ship Time": 3.0,
        "Shipping Mode": "Standard Class",
        "Customer Segment": "Consumer",
        "Order Region": "South Asia"
    }
    res_m3 = service.predict_delay_duration(payload_m3)
    print("Baseline Model 03 Direct Result:", res_m3["model_id"], res_m3["duration_summary"])
    assert "estimated_delay_duration_days" in res_m3

    # 3b. Improved Model 03
    res_m3_imp = service.predict_delay_duration_improved(payload_m3)
    print("Improved Model 03 Direct Result:", res_m3_imp["model_id"], res_m3_imp["duration_summary"])
    assert "estimated_delay_duration_days" in res_m3_imp

    # 4. Control Tower Unified
    full_payload = {
        "Order Id": 10582,
        "Days for shipment (scheduled)": 2,
        "Type": "DEBIT",
        "Shipping Mode": "Second Class",
        "Order Region": "Central America",
        "Order Status": "PROCESSING",
        "Order Item Quantity": 5,
        "Sales": 599.95,
        "Category Name": "Cardio Equipment"
    }
    res_ct_base = service.evaluate_shipment_control_tower(full_payload, version="baseline")
    assert "control_tower_summary" in res_ct_base
    print("Baseline Control Tower Assessment:", res_ct_base["control_tower_summary"])

    res_ct_imp = service.evaluate_shipment_control_tower(full_payload, version="improved")
    assert "control_tower_summary" in res_ct_imp
    print("Improved Control Tower Assessment:", res_ct_imp["control_tower_summary"])

def test_flask_endpoints():
    print("\n--- Testing Flask REST API Endpoints via TestClient ---")
    client = app.test_client()

    # Health
    r = client.get("/health")
    assert r.status_code == 200
    data = json.loads(r.data)
    print("Health Status:", data["status"], "Baseline loaded:", data["baseline_models"]["model_01"]["loaded"], "Improved loaded:", data["improved_models"]["model_01_improved"]["loaded"])

    # Predict Order Creation (Baseline)
    r = client.post("/predict/order-creation", json={
        "Days for shipment (scheduled)": 4,
        "Order Item Quantity": 2,
        "Sales": 150.0,
        "Shipping Mode": "Standard Class",
        "Order Region": "South Asia",
        "Type": "PAYMENT",
        "Market": "Pacific Asia",
        "Primary Category": "Apparel"
    })
    assert r.status_code == 200

    # Predict Order Creation (Improved)
    r = client.post("/predict/order-creation-improved", json={
        "Days for shipment (scheduled)": 4,
        "Order Item Quantity": 2,
        "Sales": 150.0,
        "Shipping Mode": "Standard Class",
        "Order Region": "South Asia",
        "Type": "PAYMENT",
        "Market": "Pacific Asia",
        "Primary Category": "Apparel"
    })
    assert r.status_code == 200
    print("Flask /predict/order-creation-improved:", json.loads(r.data))

    # Predict Dispatch (Baseline)
    r = client.post("/predict/dispatch", json={
        "Days for shipment (scheduled)": 4,
        "Order-to-Ship Time": 3.0,
        "Shipping Mode": "Standard Class",
        "Order Region": "Eastern Asia",
        "Market": "Pacific Asia",
        "Department Name": "Fitness",
        "Customer Segment": "Consumer"
    })
    assert r.status_code == 200

    # Predict Dispatch (Improved)
    r = client.post("/predict/dispatch-improved", json={
        "Days for shipment (scheduled)": 4,
        "Order-to-Ship Time": 3.0,
        "Shipping Mode": "Standard Class",
        "Order Region": "Eastern Asia",
        "Market": "Pacific Asia",
        "Department Name": "Fitness",
        "Customer Segment": "Consumer"
    })
    assert r.status_code == 200
    print("Flask /predict/dispatch-improved:", json.loads(r.data))

    # Predict Delay Duration (Baseline)
    r = client.post("/predict/delay-duration", json={
        "Days for shipment (scheduled)": 2,
        "Order-to-Ship Time": 1.0,
        "Shipping Mode": "First Class",
        "Customer Segment": "Consumer",
        "Order Region": "Western Europe"
    })
    assert r.status_code == 200

    # Predict Delay Duration (Improved)
    r = client.post("/predict/delay-duration-improved", json={
        "Days for shipment (scheduled)": 2,
        "Order-to-Ship Time": 1.0,
        "Shipping Mode": "First Class",
        "Customer Segment": "Consumer",
        "Order Region": "Western Europe"
    })
    assert r.status_code == 200
    print("Flask /predict/delay-duration-improved:", json.loads(r.data))

    # Control Tower Endpoint (default improved)
    r = client.post("/predict/control-tower", json={
        "Order Id": 9999,
        "Days for shipment (scheduled)": 1,
        "Order-to-Ship Time": 2.0,
        "Type": "TRANSFER",
        "Shipping Mode": "First Class",
        "Order Region": "South Asia",
        "Market": "Pacific Asia",
        "Customer Segment": "Consumer",
        "Department Name": "Fitness",
        "Primary Category": "Sporting Goods",
        "Order Item Quantity": 6,
        "Sales": 890.0
    })
    assert r.status_code == 200
    print("Flask /predict/control-tower:", json.loads(r.data)["control_tower_summary"])

    # Metrics
    r = client.get("/metrics")
    assert r.status_code == 200
    metrics_data = json.loads(r.data)
    assert "baseline" in metrics_data
    assert "improved" in metrics_data
    print("Flask /metrics Baseline & Improved Keys verified successfully.")

    # Live Event Ingestion (Reference Notebook Cell 6 & 20)
    live_event_payload = {
        "Order Id": "LIVE-TEST-001",
        "Days for shipment (scheduled)": 2,
        "Type": "DEBIT",
        "Shipping Mode": "Second Class",
        "Order Region": "Central America",
        "Order Item Quantity": 3,
        "Sales": 320.0
    }
    r = client.post("/predict/live-event", json=live_event_payload)
    assert r.status_code == 200
    live_res = json.loads(r.data)
    assert "random_forest" in live_res
    assert "xgboost" in live_res
    assert "consolidated_assessment" in live_res
    print("Flask /predict/live-event:", live_res["consolidated_assessment"])

    # Batch Predictions
    r = client.post("/predict/batch", json={
        "shipments": [
            {
                "Order Id": 1001,
                "Days for shipment (scheduled)": 4,
                "Type": "PAYMENT",
                "Shipping Mode": "Standard Class",
                "Order Region": "South America",
                "Order Item Quantity": 1,
                "Sales": 150.0
            },
            {
                "Order Id": 1002,
                "Days for shipment (scheduled)": 1,
                "Type": "TRANSFER",
                "Shipping Mode": "First Class",
                "Order Region": "Western Europe",
                "Order Item Quantity": 5,
                "Sales": 720.0
            }
        ]
    })
    assert r.status_code == 200
    batch_res = json.loads(r.data)
    assert batch_res["count"] == 2
    print(f"Flask /predict/batch: successfully processed {batch_res['count']} shipments.")

    # Model Registry
    r = client.get("/models/registry")
    assert r.status_code == 200
    reg_data = json.loads(r.data)
    assert "models" in reg_data
    print(f"Flask /models/registry: catalog contains {len(reg_data['models'])} registered models.")

    # Database Recent Scores
    r = client.get("/database/recent-scores?limit=5")
    assert r.status_code == 200
    db_res = json.loads(r.data)
    assert "scores" in db_res
    print(f"Flask /database/recent-scores: retrieved {len(db_res['scores'])} persisted records.")

    print("\nALL FLASK TESTS (BASELINE, IMPROVED, LIVE EVENT & REGISTRY) PASSED!")

if __name__ == "__main__":
    test_prediction_service_standalone()
    test_flask_endpoints()
