"""monitoring.py - Phase 13: prediction history, outcome feedback, performance and drift monitoring.

SQLite is used here so the module runs and is testable with the standard library; the same tables for MySQL are in
sql/monitoring_mysql.sql. Everything is INSERT-ONLY: re-scoring or a new model never overwrites an old prediction.
Drift scores raise INVESTIGATION ALERTS only - nothing retrains or deploys automatically.
"""
import datetime as dt
import json, sqlite3
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from model_evaluation import compute_metrics

DDL = """
CREATE TABLE IF NOT EXISTS prediction_history (
  prediction_id INTEGER PRIMARY KEY AUTOINCREMENT, shipment_id TEXT, prediction_stage TEXT NOT NULL, model_version TEXT NOT NULL,
  predicted_probability REAL NOT NULL, predicted_class INTEGER NOT NULL, risk_level TEXT NOT NULL, decision_threshold REAL NOT NULL,
  prediction_timestamp TEXT NOT NULL, feature_snapshot TEXT, prediction_status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS prediction_failures (
  failure_id INTEGER PRIMARY KEY AUTOINCREMENT, shipment_id TEXT, prediction_stage TEXT, error_code TEXT, error_message TEXT, failed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actual_outcomes (
  outcome_id INTEGER PRIMARY KEY AUTOINCREMENT, shipment_id TEXT NOT NULL, scheduled_delivery_ts TEXT, actual_delivery_ts TEXT,
  actual_outcome TEXT NOT NULL, actual_delay_days REAL, delay_reason TEXT, recorded_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_pred_ship ON prediction_history(shipment_id);
CREATE INDEX IF NOT EXISTS ix_out_ship ON actual_outcomes(shipment_id);
"""
def _now(): return dt.datetime.now(dt.timezone.utc).isoformat()

class MonitoringStore:
    def __init__(self, path=":memory:"):
        self.con = sqlite3.connect(path, check_same_thread=False); self.con.executescript(DDL)

    def log_prediction(self, result, features=None):
        cur = self.con.execute(
            "INSERT INTO prediction_history (shipment_id, prediction_stage, model_version, predicted_probability, predicted_class, risk_level,"
            " decision_threshold, prediction_timestamp, feature_snapshot, prediction_status) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (result.get("shipment_id"), result["prediction_stage"], result["model_version"], result["predicted_probability"], result["predicted_class"],
             result["risk_level"], result["decision_threshold"], result["prediction_timestamp"], json.dumps(features, default=str) if features else None,
             result["prediction_status"]))
        self.con.commit(); return cur.lastrowid

    def log_failure(self, shipment_id, stage, code, message):
        self.con.execute("INSERT INTO prediction_failures (shipment_id, prediction_stage, error_code, error_message, failed_at) VALUES (?,?,?,?,?)",
                         (shipment_id, stage, code, message, _now())); self.con.commit()

    def record_outcome(self, shipment_id, scheduled_ts, actual_ts, delay_reason=None):
        """Late iff actual delivery > scheduled delivery. Stored as a NEW row; predictions are never touched."""
        s, a = pd.Timestamp(scheduled_ts), pd.Timestamp(actual_ts)
        outcome = "LATE" if a > s else "ON_TIME"; delay = max((a - s).total_seconds() / 86400, 0.0)
        self.con.execute("INSERT INTO actual_outcomes (shipment_id, scheduled_delivery_ts, actual_delivery_ts, actual_outcome, actual_delay_days, delay_reason, recorded_at)"
                         " VALUES (?,?,?,?,?,?,?)", (shipment_id, str(s), str(a), outcome, delay, delay_reason, _now())); self.con.commit()
        return outcome

    def joined(self):
        return pd.read_sql_query(
            "SELECT p.*, o.actual_outcome, o.actual_delay_days FROM prediction_history p JOIN actual_outcomes o ON o.shipment_id = p.shipment_id "
            "AND o.outcome_id = (SELECT MAX(outcome_id) FROM actual_outcomes WHERE shipment_id = p.shipment_id)", self.con)

    def performance(self, model_version=None, group_key=None):
        d = self.joined()
        if model_version: d = d[d.model_version == model_version]
        if d.empty: return pd.DataFrame()
        def one(x):
            y = (x.actual_outcome == "LATE").astype(int).values; m = compute_metrics(y, x.predicted_probability.values, x.decision_threshold.iloc[0]) if y.min() != y.max() else {}
            return {"n": len(x), "late_rate": y.mean(), **{k: m.get(k) for k in ["precision", "recall", "f1", "roc_auc", "pr_auc", "brier", "FN", "FP"]}}
        if group_key is None:
            return pd.DataFrame([{"model_version": v, **one(g)} for v, g in d.groupby("model_version")])
        d["grp"] = d.feature_snapshot.map(lambda s: json.loads(s).get(group_key) if s else None)
        return pd.DataFrame([{"model_version": v, group_key: k, **one(g)} for (v, k), g in d.groupby(["model_version", "grp"])])

# ------------------------------------------------------------------ drift
def psi_numeric(ref, live, bins=10):
    ref, live = pd.Series(ref).dropna().values, pd.Series(live).dropna().values
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3: return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    a = np.histogram(ref, edges)[0] / len(ref); b = np.histogram(live, edges)[0] / max(len(live), 1)
    a, b = np.clip(a, 1e-4, None), np.clip(b, 1e-4, None)
    return float(np.sum((b - a) * np.log(b / a)))

def psi_categorical(ref, live):
    ref, live = pd.Series(ref).fillna("Unknown").astype(str), pd.Series(live).fillna("Unknown").astype(str)
    known = set(ref); live = live.where(live.isin(known), "__UNSEEN__")
    cats = sorted(known | {"__UNSEEN__"}); a = ref.value_counts(normalize=True).reindex(cats).fillna(0); b = live.value_counts(normalize=True).reindex(cats).fillna(0)
    a, b = np.clip(a.values, 1e-4, None), np.clip(b.values, 1e-4, None)
    return float(np.sum((b - a) * np.log(b / a)))

def level(psi): return "INVESTIGATE" if psi >= 0.25 else ("WATCH" if psi >= 0.10 else "OK")

def drift_report(ref, live, numeric, categorical, ref_pred=None, live_pred=None):
    rows = []
    for c in numeric:
        p = psi_numeric(ref[c], live[c]); ks = ks_2samp(ref[c].dropna(), live[c].dropna())
        rows.append({"feature": c, "type": "numeric", "psi": p, "ks_stat": ks.statistic, "ks_pvalue": ks.pvalue, "missing_rate_ref": ref[c].isna().mean(),
                     "missing_rate_live": live[c].isna().mean(), "unseen_share_live": np.nan, "alert": level(p)})
    for c in categorical:
        p = psi_categorical(ref[c], live[c]); unseen = float((~live[c].fillna("Unknown").astype(str).isin(set(ref[c].fillna("Unknown").astype(str)))).mean())
        rows.append({"feature": c, "type": "categorical", "psi": p, "ks_stat": np.nan, "ks_pvalue": np.nan, "missing_rate_ref": ref[c].isna().mean(),
                     "missing_rate_live": live[c].isna().mean(), "unseen_share_live": unseen, "alert": level(p)})
    if ref_pred is not None and live_pred is not None:
        p = psi_numeric(ref_pred, live_pred); ks = ks_2samp(ref_pred, live_pred)
        rows.append({"feature": "PREDICTED_PROBABILITY", "type": "prediction", "psi": p, "ks_stat": ks.statistic, "ks_pvalue": ks.pvalue,
                     "missing_rate_ref": 0.0, "missing_rate_live": 0.0, "unseen_share_live": np.nan, "alert": level(p)})
    out = pd.DataFrame(rows)
    out["action"] = np.where(out.alert == "INVESTIGATE", "Investigate data/model; retraining needs controlled approval (never automatic)", "")
    return out
