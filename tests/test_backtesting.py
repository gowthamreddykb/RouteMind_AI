import pandas as pd
import backtesting as BT
import target_validation as TV
import load_data as L

def test_expanding_backtest_is_leak_safe_and_expanding(cleaned, raw):
    d = cleaned[TV.eligible_mask(TV.classify_outcomes(cleaned))].copy()
    d["_t"] = d["order date (DateOrders)"]; d["_y"] = d[L.TARGET]
    d = d[d["_t"] < "2015-09-01"]
    bnd = [pd.Timestamp(x) for x in ["2015-05-01", "2015-06-15", "2015-08-01"]]
    res = BT.expanding_backtest(d, {"max_depth": 3}, 20, 0.4, bnd)
    assert len(res) == 2 and res.train_rows.is_monotonic_increasing
    assert (res.eval_rows > 0).all() and res[["precision", "recall", "roc_auc", "pr_auc", "false_negative_rate", "false_positive_rate"]].notna().all().all()
    assert (res.TN + res.FP + res.FN + res.TP == res.eval_rows).all()
