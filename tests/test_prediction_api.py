import pytest
import prediction as PR
import monitoring as MON
from conftest import records_from

@pytest.fixture(scope="module")
def rec(parts, production):
    return records_from(parts["test"], 2)[0]

def test_success_response_contract(rec, production):
    s = MON.MonitoringStore(); r = PR.predict_order_creation_api(rec, shipment_id="SHP1", store=s)
    for k in ["shipment_id", "prediction_stage", "predicted_probability", "risk_percentage", "risk_level", "decision_threshold", "model_version",
              "prediction_timestamp", "top_risk_factors", "prediction_status"]:
        assert k in r
    assert r["prediction_status"] == "PREDICTED" and r["risk_percentage"] == pytest.approx(r["predicted_probability"] * 100, abs=0.01)
    assert r["top_risk_factors"] and "business_explanation" in r["top_risk_factors"][0]
    assert s.con.execute("select count(*) from prediction_history").fetchone()[0] == 1          # history written

def test_validation_error_is_controlled_and_never_fabricates(rec):
    s = MON.MonitoringStore(); bad = {k: v for k, v in rec.items() if k != "Market"}
    r = PR.predict_order_creation_api(bad, shipment_id="SHP2", store=s)
    assert r["prediction_status"] == "ERROR" and r["error"]["code"] == "VALIDATION_ERROR" and r["predicted_probability"] is None and r["risk_level"] is None
    assert s.con.execute("select count(*) from prediction_failures").fetchone()[0] == 1
    assert s.con.execute("select count(*) from prediction_history").fetchone()[0] == 0

def test_model_unavailable_is_controlled(rec, tmp_path):
    s = MON.MonitoringStore(); r = PR.predict_order_creation_api(rec, shipment_id="SHP3", store=s, models_dir=str(tmp_path))
    assert r["prediction_status"] == "ERROR" and r["error"]["code"] == "MODEL_UNAVAILABLE" and r["predicted_probability"] is None

def test_garbage_payload_does_not_crash():
    for payload in (None, 5, [], "text", {}):
        r = PR.predict_order_creation_api(payload)
        assert r["prediction_status"] == "ERROR" and r["predicted_probability"] is None

def test_explicit_version_loads_that_version(rec):
    r = PR.predict_order_creation_api(rec, version="1.0.0", explain=False)
    assert r["prediction_status"] == "PREDICTED" and r["model_version"] == "1.0.0"
