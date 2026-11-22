"""backtesting.py - Phase 5.2: expanding-window time-based backtests (uses ONLY the train+validation period; test stays untouched)."""
import numpy as np
import pandas as pd
import model_training as MT
import model_evaluation as ME

def expanding_backtest(df, params, n_trees, threshold, boundaries):
    """boundaries: list of Timestamps b0<b1<...; fold i trains on rows with date < b_i and evaluates on b_i <= date < b_{i+1}.
    The front end (imputer/encoder) is refitted on each fold's TRAINING rows only; no early stopping (no eval data is used for fitting)."""
    rows = []
    for i in range(len(boundaries) - 1):
        a = df[df["_t"] < boundaries[i]]; b = df[(df["_t"] >= boundaries[i]) & (df["_t"] < boundaries[i + 1])]
        assert not (set(a["Order Id"]) & set(b["Order Id"])), "order crosses backtest partitions"
        front = MT.make_front((), False); Xa = front.fit_transform(a); Xb = front.transform(b)
        m = MT.make_xgb({**params, "n_estimators": int(n_trees)}, early_stopping_rounds=None); m.fit(Xa, a["_y"].values)
        p = m.predict_proba(Xb)[:, 1]; y = b["_y"].values; mt = ME.compute_metrics(y, p, threshold)
        rows.append({"fold": i + 1, "train_until": str(boundaries[i].date()), "eval_window": f"{boundaries[i].date()} .. {boundaries[i + 1].date()}",
                     "train_rows": len(a), "eval_rows": len(b), "late_rate": y.mean(), "threshold": threshold, "precision": mt["precision"], "recall": mt["recall"],
                     "f1": mt["f1"], "roc_auc": mt["roc_auc"], "pr_auc": mt["pr_auc"], "false_negative_rate": mt["FN"] / max(mt["FN"] + mt["TP"], 1),
                     "false_positive_rate": mt["FP"] / max(mt["FP"] + mt["TN"], 1), "alert_fraction": mt["flagged_fraction"],
                     "TN": mt["TN"], "FP": mt["FP"], "FN": mt["FN"], "TP": mt["TP"]})
    return pd.DataFrame(rows)
