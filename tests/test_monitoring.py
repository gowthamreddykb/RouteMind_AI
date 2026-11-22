import json
import numpy as np
import pandas as pd
import monitoring as MON

def _res(sid="S1", p=0.8, v="1.0.0"):
    return {"shipment_id": sid, "prediction_stage": "order_creation", "model_version": v, "predicted_probability": p, "predicted_class": int(p >= 0.4),
            "risk_level": "HIGH", "decision_threshold": 0.4, "prediction_timestamp": "2026-01-01T00:00:00+00:00", "prediction_status": "PREDICTED"}

def test_prediction_record_created_with_snapshot():
    s = MON.MonitoringStore(); pid = s.log_prediction(_res(), {"Shipping Mode": "First Class"})
    row = pd.read_sql_query("select * from prediction_history", s.con).iloc[0]
    assert pid == 1 and row.model_version == "1.0.0" and json.loads(row.feature_snapshot)["Shipping Mode"] == "First Class"

def test_history_is_never_overwritten_on_rescore_or_new_model():
    s = MON.MonitoringStore(); s.log_prediction(_res(p=0.2)); s.log_prediction(_res(p=0.9, v="2.0.0"))
    d = pd.read_sql_query("select * from prediction_history order by prediction_id", s.con)
    assert len(d) == 2 and d.predicted_probability.tolist() == [0.2, 0.9]

def test_outcome_capture_and_delay_calculation():
    s = MON.MonitoringStore()
    assert s.record_outcome("A", "2026-01-05", "2026-01-08") == "LATE" and s.record_outcome("B", "2026-01-05", "2026-01-05") == "ON_TIME"
    o = pd.read_sql_query("select * from actual_outcomes", s.con).set_index("shipment_id")
    assert o.loc["A", "actual_delay_days"] == 3 and o.loc["B", "actual_delay_days"] == 0

def test_performance_calculation_by_model_version_and_group():
    s = MON.MonitoringStore(); rng = np.random.default_rng(0)
    for i in range(200):
        late = i % 2; p = 0.8 if late else 0.2
        s.log_prediction(_res(f"S{i}", p), {"Shipping Mode": "A" if i < 100 else "B"})
        s.record_outcome(f"S{i}", "2026-01-05", "2026-01-07" if late else "2026-01-04")
    perf = s.performance(); assert perf.iloc[0]["recall"] == 1.0 and perf.iloc[0]["precision"] == 1.0 and perf.iloc[0]["n"] == 200
    assert set(s.performance(group_key="Shipping Mode")["Shipping Mode"]) == {"A", "B"}

def test_failure_logging():
    s = MON.MonitoringStore(); s.log_failure("S9", "order_creation", "VALIDATION_ERROR", "missing field")
    assert pd.read_sql_query("select * from prediction_failures", s.con).iloc[0].error_code == "VALIDATION_ERROR"

def test_psi_zero_for_identical_and_large_for_shifted():
    rng = np.random.default_rng(1); a = rng.normal(0, 1, 5000)
    assert MON.psi_numeric(a, a) < 0.001 and MON.psi_numeric(a, a + 2) > 0.25
    ca = pd.Series(["x"] * 500 + ["y"] * 500); assert MON.psi_categorical(ca, ca) < 0.001 and MON.psi_categorical(ca, pd.Series(["z"] * 1000)) > 0.25

def test_drift_report_flags_shift_unseen_and_missing_without_retraining():
    ref = pd.DataFrame({"n": np.random.default_rng(0).normal(0, 1, 3000), "c": ["a", "b", "c"] * 1000})
    live = pd.DataFrame({"n": np.random.default_rng(1).normal(3, 1, 3000), "c": ["a", "z", "z"] * 1000}); live.loc[:299, "n"] = np.nan
    r = MON.drift_report(ref, live, ["n"], ["c"]).set_index("feature")
    assert r.loc["n", "alert"] == "INVESTIGATE" and r.loc["c", "unseen_share_live"] > 0.6 and r.loc["n", "missing_rate_live"] == pytest.approx(0.1)
    assert "never automatic" in r.loc["n", "action"]

import pytest
