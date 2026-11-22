import numpy as np
import pandas as pd
import pytest
import historical_features as H

KEYS = {"mode": ["Shipping Mode"]}
def _ev(): return pd.DataFrame({"Shipping Mode": ["S"] * 3, "_t": pd.to_datetime(["2016-01-05", "2016-01-10", "2016-01-20"]), "_y": [1, 0, 1]})
def _q(dates): return pd.DataFrame({"Shipping Mode": ["S"] * len(dates), "_t": pd.to_datetime(dates)})

def test_only_past_delivered_outcomes_are_counted():
    f = H.time_aware_features(_ev(), _q(["2016-01-01", "2016-01-06", "2016-01-15", "2016-02-01"]), KEYS, prior_m=1e-6)
    assert np.expm1(f["hist_mode_n"]).round().tolist() == [0, 1, 2, 3]
    assert f["hist_mode_rate"].round(3).tolist() == [0.5, 1.0, 0.5, 0.667]

def test_future_outcome_never_changes_earlier_features():
    q = _q(["2016-01-06"]); a = H.time_aware_features(_ev(), q, KEYS)
    ev2 = _ev(); ev2.loc[2, "_y"] = 0                                   # change an outcome that is in the FUTURE of the query
    b = H.time_aware_features(ev2, q, KEYS)
    pd.testing.assert_frame_equal(a, b)

def test_row_never_sees_its_own_outcome():
    d = pd.DataFrame({"Shipping Mode": ["S", "S"], "_order": pd.to_datetime(["2016-01-01", "2016-01-02"]), "_y": [1, 1]})
    ev = d.assign(_t=d["_order"] + pd.Timedelta(days=3)); q = d.assign(_t=d["_order"])
    f = H.time_aware_features(ev, q, KEYS)
    assert (f["hist_mode_n"] == 0).all()                                # each order's own outcome arrives after it was placed

def test_fallback_without_history_and_smoothing():
    f = H.time_aware_features(_ev(), _q(["2015-01-01"]), KEYS)
    assert f["hist_mode_rate"].iloc[0] == H.FALLBACK_RATE and f["hist_mode_n"].iloc[0] == 0      # no history at all -> fallback rate
    # key S has 1 late order; key T has 9 on-time orders -> global past rate = 0.1; S's raw rate (1.0) is shrunk towards it
    ev = pd.concat([pd.DataFrame({"Shipping Mode": ["S"], "_t": pd.to_datetime(["2016-01-05"]), "_y": [1]}),
                    pd.DataFrame({"Shipping Mode": ["T"] * 9, "_t": pd.to_datetime([f"2016-01-0{i}" for i in range(1, 10)][:4] * 2 + ["2016-01-03"]), "_y": [0] * 9})])
    ev.loc[ev["Shipping Mode"] == "T", "_t"] = pd.to_datetime(["2016-01-01"] * 9)
    g = H.time_aware_features(ev, _q(["2016-01-06"]), KEYS)
    assert 0.1 < g["hist_mode_rate"].iloc[0] < 0.2 and g["hist_mode_n"].iloc[0] == pytest.approx(np.log1p(1))

def test_snapshot_matches_time_aware_at_a_late_query_time():
    snap = H.HistorySnapshot(_ev(), KEYS); q = _q(["2030-01-01"])
    pd.testing.assert_frame_equal(snap.features(q), H.time_aware_features(_ev(), q, KEYS))

def test_augmenter_passes_through_precomputed_columns_and_looks_up_new_rows():
    snap = H.HistorySnapshot(_ev(), KEYS); aug = H.HistoryAugmenter(snap)
    new = pd.DataFrame({"Shipping Mode": ["S", "Unknown Mode"]}); out = aug.transform(new)
    assert {"hist_mode_rate", "hist_mode_n"} <= set(out.columns) and out["hist_mode_n"].iloc[1] == 0
    pre = out.copy(); pre["hist_mode_rate"] = 0.123
    assert aug.transform(pre)["hist_mode_rate"].eq(0.123).all()
