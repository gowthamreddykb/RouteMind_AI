import pytest
flask = pytest.importorskip("flask")
import flask_example as FX
from conftest import records_from

@pytest.fixture(scope="module")
def client(production, tmp_path_factory):
    return FX.create_app(db_path=":memory:").test_client()

def test_health_and_model_info(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    r = client.get("/api/model"); assert r.status_code == 200 and r.get_json()["approval_status"]

def test_predict_ok_and_persisted(client, parts):
    rec = records_from(parts["test"], 1)[0]; rec["shipment_id"] = "SHP77"
    r = client.post("/api/predict/order-creation", json=rec); j = r.get_json()
    assert r.status_code == 200 and j["prediction_status"] == "PREDICTED" and 0 <= j["predicted_probability"] <= 1 and j["shipment_id"] == "SHP77"

def test_invalid_input_gives_422_not_a_prediction(client, parts):
    rec = records_from(parts["test"], 1)[0]; del rec["Shipping Mode"]
    r = client.post("/api/predict/order-creation", json=rec)
    assert r.status_code == 422 and r.get_json()["predicted_probability"] is None
    assert client.post("/api/predict/order-creation", data="not json").status_code == 422

def test_outcome_endpoint(client):
    r = client.post("/api/outcomes", json={"shipment_id": "SHP77", "scheduled_delivery_ts": "2026-01-05", "actual_delivery_ts": "2026-01-07"})
    assert r.status_code == 201 and r.get_json()["actual_outcome"] == "LATE"
    assert client.post("/api/outcomes", json={"shipment_id": "x"}).status_code == 422

def test_model_unavailable_gives_503(parts, tmp_path):
    c = FX.create_app(models_dir=str(tmp_path), db_path=":memory:").test_client()
    assert c.post("/api/predict/order-creation", json=records_from(parts["test"], 1)[0]).status_code == 503
