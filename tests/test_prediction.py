import numpy as np
import pytest
import prediction as PR
import load_data as L
import feature_engineering as FE
import shap_explainability as SX
from conftest import records_from

@pytest.fixture(scope="module")
def recs(parts, production):
    return records_from(parts["test"], 5, production["feature_schema"]["required_raw_fields"][len(FE.BASE_RAW_FIELDS):])

def test_probability_and_stage(recs, production):
    r = PR.predict_at_order_creation(recs[0], shipment_id="SHP1")
    assert 0 <= r["late_delivery_probability"] <= 1 and r["prediction_stage"] == "order_creation"
    assert r["risk_level"] in {"LOW", "MEDIUM", "HIGH"} and r["predicted_class"] in (0, 1)
    assert r["shipment_id"] == "SHP1" and r["model_version"] and r["scoring_timestamp"] and r["prediction_status"] == "PREDICTED"

def test_risk_level_matches_probability(recs):
    r = PR.predict_at_order_creation(recs, explain=False)
    cut = PR.load_model()["risk_cutoffs"]
    for x in r:
        assert x["risk_level"] == PR.risk_level(x["late_delivery_probability"], cut)

def test_batch_equals_single(recs):
    batch = PR.predict_at_order_creation(recs, explain=False)
    single = PR.predict_at_order_creation(recs[2], explain=False)
    assert batch[2]["late_delivery_probability"] == pytest.approx(single["late_delivery_probability"])

def test_missing_field_rejected(recs):
    bad = {k: v for k, v in recs[0].items() if k != "Shipping Mode"}
    with pytest.raises(PR.ValidationError, match="Shipping Mode"):
        PR.predict_at_order_creation(bad)

def test_unexpected_and_outcome_fields_rejected(recs):
    with pytest.raises(PR.ValidationError, match="unexpected"):
        PR.predict_at_order_creation({**recs[0], "Days for shipping (real)": 3})
    with pytest.raises(PR.ValidationError):
        PR.predict_at_order_creation({**recs[0], "Delivery Status": "Late delivery"})

def test_empty_invalid_values_rejected_not_filled(recs):
    for patch in [{"Market": ""}, {"Sales": None}, {"Sales": "abc"}, {"Order Item Quantity": -1}, {FE.RAW_DATE: "garbage"}]:
        with pytest.raises(PR.ValidationError):
            PR.predict_at_order_creation({**recs[0], **patch})

def test_unknown_category_handled(recs):
    r = PR.predict_at_order_creation({**recs[0], "Customer City": "Atlantis"}, explain=False)
    assert 0 <= r["late_delivery_probability"] <= 1 and r["unknown_categories"]["Customer City"] == "Atlantis"

def test_dispatch_disabled_without_valid_model():
    with pytest.raises(PR.ModelUnavailableError, match="Dispatch"):
        PR.predict_at_dispatch({})

def test_dispatch_unavailable_in_empty_models_dir(recs, tmp_path):
    with pytest.raises(PR.ModelUnavailableError):
        PR.predict_at_dispatch(recs[0], models_dir=str(tmp_path))

def test_explanations_match_actual_model(recs, production):
    r = PR.predict_at_order_creation(recs[0], top_k=3)
    schema = production["feature_schema"]; allowed = set(schema["model_input_numeric"] + schema["model_input_categorical"])
    assert len(r["explanations"]) == 3 and set(r["explanations"]) <= allowed
    import pandas as pd
    err, ok = SX.check_additivity(production["pipeline"], pd.DataFrame(recs))
    assert ok, f"SHAP not additive w.r.t. model output (err={err})"
    contribs = [d["shap_contribution"] for d in r["explanation_details"]["top_features"]]
    assert contribs == sorted(contribs, key=abs, reverse=True) and "causation" in r["explanation_note"]

def test_database_rows_insert_only_shape(recs):
    r = PR.predict_at_order_creation(recs[0]); rows = PR.to_database_rows(r, model_id=1, shipment_db_id=10)
    assert rows["model_scores"]["shipment_id"] == 10 and "score_id" not in rows["model_scores"] and rows["risk_factors"]
    assert {"feature_name", "contribution_value", "contribution_direction"} <= set(rows["risk_factors"][0])

def test_model_loaded_once(recs):
    assert PR.load_model() is PR.load_model()
