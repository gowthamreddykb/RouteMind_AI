"""historical_features.py - leakage-safe historical late-delivery rates (Phase 4).

RULES (enforced and unit-tested):
 * An order's outcome is only 'known' once it has been DELIVERED: event_time = order time + actual duration.
 * A query row at order time t only sees events with event_time <= t (past records only). Its own outcome can
   never be included because its own event_time > its own order time.
 * Rates are smoothed towards the global past rate with prior strength PRIOR_M; the count is exposed as a feature so
   the model can see thin history (cold start). With no history at all the fallback rate is 0.5.
 * Training rows use time-aware features; production uses a frozen SNAPSHOT of all labelled history (refresh on retrain).
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from feature_engineering import normalize_text

PRIOR_M = 20.0
FALLBACK_RATE = 0.5

# name -> raw columns forming the key. 'carrier' / 'warehouse' history is BLOCKED: DataCo has no carrier or warehouse column.
KEY_GROUPS = {
    "route":    {"mode": ["Shipping Mode"], "region": ["Order Region"], "route": ["Shipping Mode", "Order Region"],
                 "country_mode": ["Shipping Mode", "Order Country"]},
    "product":  {"category": ["Category Name"], "product": ["Product Name"], "mode_category": ["Shipping Mode", "Category Name"]},
    "market":   {"market": ["Market"], "segment": ["Customer Segment"]},
    "customer": {"customer": ["Customer Id"]},
}

def feature_names(keys):
    return [f"hist_{k}_{s}" for k in keys for s in ("rate", "n")]

def key_series(df, cols):
    s = None
    for c in cols:
        v = df[c].astype(str) if c == "Customer Id" else normalize_text(df[c]).astype(str)
        s = v if s is None else s + "|" + v
    return s.values

def _past_counts(ev_key, ev_t, ev_y, q_key, q_t):
    """For each query: (n, s) = number of events and number of late events with the same key and event_time <= query time."""
    n = np.zeros(len(q_t)); s = np.zeros(len(q_t))
    ev = pd.DataFrame({"k": ev_key, "t": ev_t, "y": ev_y}).sort_values(["k", "t"], kind="stable")
    groups = {k: (g["t"].values, np.cumsum(g["y"].values)) for k, g in ev.groupby("k", sort=False)}
    qdf = pd.DataFrame({"k": q_key, "pos": np.arange(len(q_t))})
    for k, g in qdf.groupby("k", sort=False):
        if k not in groups:
            continue
        t_sorted, cum = groups[k]
        pos = g["pos"].values
        idx = np.searchsorted(t_sorted, q_t[pos], side="right")          # events with event_time <= query time
        n[pos] = idx
        s[pos] = np.where(idx > 0, cum[np.maximum(idx - 1, 0)], 0.0)
    return n, s

def _to_ns(x):
    return pd.to_datetime(x).values.astype("datetime64[ns]").astype("int64")

def time_aware_features(events, queries, keys, prior_m=PRIOR_M):
    """events: DataFrame with key columns + '_t' (delivery time) + '_y' (1 = late).
    queries: DataFrame with key columns + '_t' (order time). Returns DataFrame (index = queries.index)."""
    ev_t, q_t, ev_y = _to_ns(events["_t"]), _to_ns(queries["_t"]), events["_y"].values.astype(float)
    ng, sg = _past_counts(np.zeros(len(ev_t), dtype=int), ev_t, ev_y, np.zeros(len(q_t), dtype=int), q_t)
    g = np.where(ng > 0, sg / np.maximum(ng, 1), FALLBACK_RATE)
    out = {}
    for name, cols in keys.items():
        n, s = _past_counts(key_series(events, cols), ev_t, ev_y, key_series(queries, cols), q_t)
        out[f"hist_{name}_rate"] = (s + prior_m * g) / (n + prior_m)
        out[f"hist_{name}_n"] = np.log1p(n)
    return pd.DataFrame(out, index=queries.index)

class HistorySnapshot:
    """Frozen counts of all labelled history up to the snapshot time (used for live scoring)."""
    def __init__(self, events, keys, prior_m=PRIOR_M):
        self.keys, self.prior_m = dict(keys), prior_m
        y = events["_y"].values.astype(float)
        self.n_all, self.s_all = float(len(y)), float(y.sum())
        self.tables = {}
        for name, cols in self.keys.items():
            d = pd.DataFrame({"k": key_series(events, cols), "y": y}).groupby("k")["y"].agg(["size", "sum"])
            self.tables[name] = {k: (float(r["size"]), float(r["sum"])) for k, r in d.iterrows()}
        self.snapshot_time = str(pd.to_datetime(events["_t"]).max())
    def raw_fields(self):
        return sorted({c for cols in self.keys.values() for c in cols})
    def features(self, df):
        g = self.s_all / self.n_all if self.n_all else FALLBACK_RATE
        out = {}
        for name, cols in self.keys.items():
            ks = key_series(df, cols); tab = self.tables[name]
            n = np.array([tab.get(k, (0.0, 0.0))[0] for k in ks]); s = np.array([tab.get(k, (0.0, 0.0))[1] for k in ks])
            out[f"hist_{name}_rate"] = (s + self.prior_m * g) / (n + self.prior_m)
            out[f"hist_{name}_n"] = np.log1p(n)
        return pd.DataFrame(out, index=df.index)

class HistoryAugmenter(BaseEstimator, TransformerMixin):
    """Pipeline step. If the historical columns are already present (training/evaluation, where they were computed
    time-aware) they pass through unchanged; for live raw orders they are looked up from the frozen snapshot."""
    def __init__(self, snapshot=None):
        self.snapshot = snapshot
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        cols = feature_names(self.snapshot.keys)
        if all(c in X.columns for c in cols):
            return X
        out = X.copy(); f = self.snapshot.features(X)
        for c in cols:
            out[c] = f[c].values
        return out
