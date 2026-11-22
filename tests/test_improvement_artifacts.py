import hashlib, json, os, glob
import joblib
import pandas as pd
import pytest
import load_data as L
import model_registry as MR

OUT = os.path.join(L.REPORTS, "improvement")
def _need(path):
    if not os.path.exists(path):
        pytest.skip(f"{path} not generated yet (run src/improve.py finalize)")

def test_candidate_registered_not_promoted():
    _need(os.path.join(L.MODELS, "registry.json"))
    c = MR.get("order_creation", "2.0.0", L.MODELS)
    if not c:
        pytest.skip("order_creation 2.0.0 candidate not generated yet (run src/improve.py finalize)")
    p = MR.production("order_creation", L.MODELS)
    assert c is not None and c["role"] in ("candidate", "production")
    if c["role"] == "candidate":
        assert p["model_version"] == "1.0.0" and c["approval_status"] == "PENDING_APPROVAL" and c["approved_by"] is None
    assert c["acceptance_report"]["passed"] in (True, False)

def test_baseline_v1_artifacts_unchanged_since_backup():
    backups = sorted(glob.glob(os.path.join(L.MODELS, "_backup_v1.0.0_*")))
    if not backups: pytest.skip("no backup folder")
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    v1 = os.path.join(L.MODELS, "order_creation", "versions", "v1.0.0", "best_model.joblib")
    assert sha(v1) == sha(os.path.join(backups[0], "versions", "v1.0.0", "best_model.joblib"))

def test_candidate_bundle_loads_and_predicts_probabilities(parts):
    _need(os.path.join(L.MODELS, "order_creation", "versions", "v2.0.0", "best_model.joblib"))
    b = joblib.load(os.path.join(L.MODELS, "order_creation", "versions", "v2.0.0", "best_model.joblib"))
    p = b["calibrator"].transform(b["pipeline"].predict_proba(parts["test"].head(300))[:, 1])
    assert ((p >= 0) & (p <= 1)).all() and b["metadata"]["target_definition_version"].startswith("target_v2")

def test_hyperparameter_search_and_threshold_never_saw_test_labels():
    _need(os.path.join(OUT, "threshold_grid_validation.csv"))
    g = pd.read_csv(os.path.join(OUT, "threshold_grid_validation.csv")); s = json.load(open(os.path.join(OUT, "improvement_summary.json")))
    assert list(g.threshold) == [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
    meta_path = os.path.join(L.MODELS, "order_creation", "versions", "v2.0.0", "model_metadata.json")
    _need(meta_path)
    n_val = json.load(open(meta_path))["validation_metrics"]
    assert (g.TP.iloc[0] + g.FP.iloc[0] + g.FN.iloc[0] + g.TN.iloc[0]) == n_val["TP"] + n_val["FP"] + n_val["FN"] + n_val["TN"]   # grid built on the validation rows

def test_false_negative_report_complete():
    _need(os.path.join(OUT, "false_negative_report.csv"))
    fn = pd.read_csv(os.path.join(OUT, "false_negative_report.csv")); s = json.load(open(os.path.join(OUT, "improvement_summary.json")))
    assert len(fn) == s["fn"] and (fn.actual_outcome == "LATE").all() and (fn.predicted_probability < fn.decision_threshold).all()
    assert fn.shap_top3_features_log_odds.astype(str).str.len().gt(0).any()

def test_backtests_cover_multiple_periods_without_test_period():
    _need(os.path.join(OUT, "backtest_results.csv"))
    b = pd.read_csv(os.path.join(OUT, "backtest_results.csv")); assert len(b) >= 4 and b.eval_window.str[-10:].max() <= "2017-04-01"
