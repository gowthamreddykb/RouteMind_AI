import pytest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import app as APP

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_file = str(tmp_path_factory.mktemp("db") / "test_app_monitor.sqlite")
    flask_app = APP.create_app(db_path=db_file)
    flask_app.config["TESTING"] = True
    return flask_app.test_client()

def test_dashboard_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"RouteMind" in r.data
    assert b"Control Tower" in r.data

def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.get_json()
    assert j["status"] == "healthy"
    assert j["models"]["model_01_order_creation"]["status"] == "active"
    assert j["models"]["model_02_dispatch"]["status"] == "active"

def test_list_models_endpoint(client):
    r = client.get("/api/models")
    assert r.status_code == 200
    j = r.get_json()
    stages = [m["prediction_stage"] for m in j["models"]]
    assert "order_creation" in stages
    assert "dispatch" in stages

def test_predict_order_creation(client):
    payload = {
        "Type": "DEBIT",
        "Shipping Mode": "Standard Class",
        "Days for shipment (scheduled)": 4,
        "Order Region": "Western Europe",
        "Order Country": "France",
        "Market": "Europe",
        "Category Name": "Sporting Goods",
        "Department Name": "Fitness",
        "Product Name": "Standard Ball",
        "Order Item Product Price": 50.0,
        "Order Item Quantity": 2,
        "Sales": 100.0,
        "Customer Segment": "Consumer",
        "Customer City": "Paris",
        "Customer Country": "France",
        "Customer State": "IDF",
        "Order Item Discount Rate": 0.0,
        "order date (DateOrders)": "2026-11-17 10:00:00",
        "shipment_id": "TEST-APP-001"
    }
    r = client.post("/api/predict/order-creation", json=payload)
    assert r.status_code == 200
    j = r.get_json()
    assert j["prediction_status"] == "PREDICTED"
    assert 0 <= j["predicted_probability"] <= 1
    assert j["risk_level"] in ("LOW", "MEDIUM", "HIGH")

def test_predict_dispatch(client):
    payload = {
        "Days for shipment (scheduled)": 4,
        "Order-to-Ship Time": 2.0,
        "Shipping Mode": "Standard Class",
        "Order Region": "Western Europe",
        "Market": "Europe",
        "Department Name": "Fan Shop",
        "Customer Segment": "Consumer",
        "shipment_id": "TEST-DSP-001"
    }
    r = client.post("/api/predict/dispatch", json=payload)
    assert r.status_code == 200
    j = r.get_json()
    assert j["prediction_status"] == "PREDICTED"
    assert 0 <= j["predicted_probability"] <= 1
    assert "dock_clearance_status" in j

def test_predict_control_tower_unified(client):
    payload = {
        "Type": "DEBIT",
        "Shipping Mode": "Standard Class",
        "Days for shipment (scheduled)": 4,
        "Order-to-Ship Time": 1.5,
        "Order Region": "Western Europe",
        "Order Country": "France",
        "Market": "Europe",
        "Category Name": "Sporting Goods",
        "Department Name": "Fan Shop",
        "Product Name": "Standard Ball",
        "Order Item Product Price": 50.0,
        "Order Item Quantity": 2,
        "Sales": 100.0,
        "Customer Segment": "Consumer",
        "Customer City": "Paris",
        "Customer Country": "France",
        "Customer State": "IDF",
        "Order Item Discount Rate": 0.0,
        "order date (DateOrders)": "2026-11-17 10:00:00",
        "shipment_id": "TEST-CT-001"
    }
    r = client.post("/api/predict/control-tower", json=payload)
    assert r.status_code == 200
    j = r.get_json()
    assert "control_tower_summary" in j
    summary = j["control_tower_summary"]
    assert "overall_risk_level" in summary
    assert "recommended_action" in summary
    assert "order_creation_probability" in summary
    assert "dispatch_probability" in summary

def test_batch_prediction(client):
    batch = [
        {
            "shipment_id": "BATCH-001",
            "Shipping Mode": "First Class",
            "Days for shipment (scheduled)": 1,
            "Order-to-Ship Time": 3.0,
            "Order Region": "Western Europe",
            "Market": "Europe",
            "Department Name": "Fan Shop",
            "Customer Segment": "Consumer"
        },
        {
            "shipment_id": "BATCH-002",
            "Shipping Mode": "Standard Class",
            "Days for shipment (scheduled)": 4,
            "Order-to-Ship Time": 1.5,
            "Order Region": "Central America",
            "Market": "LATAM",
            "Department Name": "Apparel",
            "Customer Segment": "Consumer"
        }
    ]
    r = client.post("/api/predict/batch", json={"shipments": batch, "stage": "dispatch"})
    assert r.status_code == 200
    j = r.get_json()
    assert j["total_processed"] == 2
    assert len(j["results"]) == 2

def test_metrics_summary(client):
    r = client.get("/api/metrics/summary")
    assert r.status_code == 200
    j = r.get_json()
    assert "model_01" in j
    assert "model_02" in j
    assert j["model_01"]["accuracy"] > 60
    assert j["model_02"]["accuracy"] > 90
