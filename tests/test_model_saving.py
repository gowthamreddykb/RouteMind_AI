import json, os
import joblib
import numpy as np
import model_saving as MS
import load_data as L

def _schema(): return {"required_raw_fields": [], "numeric_raw_fields": [], "date_field": "x"}

def test_save_and_reload_same_predictions(small_model, parts, tmp_path):
    pipe = small_model[0]
    v, vdir = MS.save_stage_model("order_creation", {"pipeline": pipe, "calibrator": None, "threshold": 0.5, "risk_cutoffs": {}},
                                  {"algorithm": "XGBoost"}, _schema(), str(tmp_path))
    for f in ["best_model.joblib", "feature_schema.json", "model_metadata.json"]:
        assert os.path.exists(tmp_path / "order_creation" / f) and os.path.exists(os.path.join(vdir, f))
    loaded = joblib.load(tmp_path / "order_creation" / "best_model.joblib")
    X = parts["test"].head(200)
    np.testing.assert_allclose(loaded["pipeline"].predict_proba(X), pipe.predict_proba(X))
    assert json.load(open(tmp_path / "order_creation" / "model_metadata.json"))["model_version"] == v

def test_previous_version_is_never_overwritten(small_model, tmp_path):
    b = {"pipeline": small_model[0], "calibrator": None, "threshold": 0.5, "risk_cutoffs": {}}
    v1, _ = MS.save_stage_model("order_creation", b, {"algorithm": "x"}, _schema(), str(tmp_path))
    v2, _ = MS.save_stage_model("order_creation", b, {"algorithm": "x"}, _schema(), str(tmp_path))
    assert v1 != v2 and os.path.exists(tmp_path / "order_creation" / "versions" / f"v{v1}" / "best_model.joblib")

def test_dispatch_requirements_do_not_create_a_model(tmp_path):
    MS.write_dispatch_requirements(str(tmp_path))
    assert os.path.exists(tmp_path / "dispatch" / "dispatch_requirements.json")
    assert not os.path.exists(tmp_path / "dispatch" / "best_model.joblib")

def test_production_artifacts_consistent():
    d = os.path.join(L.MODELS, "order_creation")
    if not os.path.exists(os.path.join(d, "best_model.joblib")):
        import pytest; pytest.skip("production model not trained yet")
    meta = json.load(open(os.path.join(d, "model_metadata.json")))
    b = joblib.load(os.path.join(d, "best_model.joblib"))
    assert b["metadata"]["model_version"] == meta["model_version"] and 0 < b["threshold"] < 1
    assert os.path.exists(os.path.join(d, "versions", f"v{meta['model_version']}", "best_model.joblib"))
    assert not os.path.exists(os.path.join(L.MODELS, "dispatch", "best_model.joblib"))
