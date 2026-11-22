import numpy as np
import pandas as pd
import model_evaluation as ME
import model_calibration as MC

def test_metrics_on_known_case():
    y = np.array([1, 1, 0, 0]); p = np.array([0.9, 0.4, 0.6, 0.1])
    m = ME.compute_metrics(y, p, 0.5)
    assert (m["TP"], m["FN"], m["FP"], m["TN"]) == (1, 1, 1, 1) and m["accuracy"] == 0.5 and 0 <= m["roc_auc"] <= 1

def test_risk_levels():
    assert list(ME.risk_level(np.array([0.1, 0.4, 0.69, 0.7, 0.99]), 0.4, 0.7)) == ["LOW", "MEDIUM", "MEDIUM", "HIGH", "HIGH"]

def test_threshold_not_forced_to_half_and_respects_capacity():
    rng = np.random.default_rng(0); y = rng.integers(0, 2, 5000); p = np.clip(0.5 + (y - 0.5) * 0.3 + rng.normal(0, 0.2, 5000), 0, 1)
    tab = ME.threshold_table(y, p)
    t, full, why = ME.select_threshold(tab, 3, 1, 0.5)
    assert full.loc[full.threshold == t, "flagged_fraction"].iloc[0] <= 0.5

def test_risk_bucket_rate_increases_with_risk():
    rng = np.random.default_rng(1); p = rng.random(20000); y = (rng.random(20000) < p).astype(int)
    assert ME.risk_bucket_report(y, p, 0.4, 0.7).observed_late_rate.is_monotonic_increasing

def test_calibrator_outputs_valid_probabilities():
    rng = np.random.default_rng(2); p = rng.random(4000) * 0.6; y = (rng.random(4000) < p * 1.3).astype(int)
    cal, tab, method = MC.choose_calibration(p, y)
    out = cal.transform(np.array([-0.2, 0.0, 0.5, 1.4]))
    assert ((out >= 0) & (out <= 1)).all() and set(tab.method) == {"none", "sigmoid", "isotonic"}

def test_subgroup_report_runs():
    meta = pd.DataFrame({"g": ["a"] * 100 + ["b"] * 100}); rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 200); p = rng.random(200)
    assert set(ME.subgroup_report(meta, y, p, 0.5, "g", "g").group) == {"a", "b"}
