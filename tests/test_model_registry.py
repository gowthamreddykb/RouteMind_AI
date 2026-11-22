import json, os
import pytest
import model_registry as MR
import model_saving as MS
import model_calibration as MC
import prediction as PR

SCHEMA = {"required_raw_fields": [], "numeric_raw_fields": [], "date_field": "x"}

@pytest.fixture()
def reg(small_model, tmp_path):
    b = {"pipeline": small_model[0], "calibrator": MC.Calibrator("none"), "threshold": 0.4, "risk_cutoffs": {"medium": 0.3, "high": 0.4}}
    md = {"algorithm": "XGBoost", "decision_threshold": 0.4, "test_metrics": {}, "validation_metrics": {}, "feature_names_raw": []}
    v1, _ = MS.save_stage_model("order_creation", b, dict(md), SCHEMA, str(tmp_path), "1.0.0")
    v2, _ = MS.save_stage_model("order_creation", b, dict(md), SCHEMA, str(tmp_path), "2.0.0", set_current=False)
    MR.register("order_creation", v1, str(tmp_path), role="production", approval_status="BASELINE")
    MR.register("order_creation", v2, str(tmp_path), role="candidate")
    return str(tmp_path), v1, v2

def test_registering_a_candidate_never_changes_production(reg):
    d, v1, v2 = reg
    assert MR.production("order_creation", d)["model_version"] == v1 and MR.get("order_creation", v2, d)["role"] == "candidate"

def test_promotion_refused_without_passing_acceptance_report(reg):
    d, v1, v2 = reg
    with pytest.raises(PermissionError):
        MR.promote("order_creation", v2, "QA lead", d)
    MR.attach_acceptance("order_creation", v2, d, {"passed": False})
    with pytest.raises(PermissionError):
        MR.promote("order_creation", v2, "QA lead", d)
    assert MR.production("order_creation", d)["model_version"] == v1

def test_promotion_requires_named_human(reg):
    d, v1, v2 = reg; MR.attach_acceptance("order_creation", v2, d, {"passed": True})
    for who in ("", "  ", None):
        with pytest.raises(PermissionError):
            MR.promote("order_creation", v2, who, d)

def test_promote_then_rollback_restores_previous(reg):
    d, v1, v2 = reg; MR.attach_acceptance("order_creation", v2, d, {"passed": True})
    MR.promote("order_creation", v2, "QA lead", d)
    prod = MR.production("order_creation", d); assert prod["model_version"] == v2 and prod["approved_by"] == "QA lead"
    assert MR.get("order_creation", v1, d)["role"] == "previous"
    assert PR.load_model("order_creation", d, reload=True)["metadata"]["model_version"] == v2          # loader follows the registry
    MR.rollback("order_creation", d, by="QA lead")
    assert MR.production("order_creation", d)["model_version"] == v1 and MR.get("order_creation", v2, d)["approval_status"] == "ROLLED_BACK"
    assert PR.load_model("order_creation", d, reload=True)["metadata"]["model_version"] == v1
    assert os.path.exists(os.path.join(d, "order_creation", "versions", f"v{v2}", "best_model.joblib"))   # nothing deleted

def test_rollback_without_previous_fails(reg):
    d, v1, v2 = reg
    with pytest.raises(LookupError):
        MR.rollback("order_creation", d, by="x")

def test_champion_challenger_identical_models_pass(small_model, parts):
    b = {"pipeline": small_model[0], "calibrator": MC.Calibrator("none"), "threshold": 0.4}
    va = parts["val"].head(1500); y = va["Late_delivery_risk"].values
    r = MR.champion_challenger(b, b, va, y)
    assert r["passed"] and set(r["checks"]) >= {"roc_auc_not_worse", "brier_not_worse", "latency_p95_within_limit"}

def test_champion_challenger_rejects_a_worse_model(small_model, parts):
    import numpy as np
    class Bad:                       # a random scorer
        def predict_proba(self, X):
            p = np.random.default_rng(0).random(len(X)); return np.c_[1 - p, p]
    good = {"pipeline": small_model[0], "calibrator": MC.Calibrator("none"), "threshold": 0.4}
    bad = {"pipeline": Bad(), "calibrator": MC.Calibrator("none"), "threshold": 0.4}
    va = parts["val"].head(1500); r = MR.champion_challenger(good, bad, va, va["Late_delivery_risk"].values)
    assert not r["passed"] and not r["checks"]["roc_auc_not_worse"]
