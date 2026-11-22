"""model_registry.py - Phase 11 + 14: versioned registry, approval, champion-challenger, rollback.

A model is NEVER promoted automatically: promote() needs a named human approver AND a passing acceptance report.
Roles: production (champion) | candidate (challenger) | previous (rollback target) | archived.
The registry is a JSON file (models/registry.json); the same fields map 1:1 onto the MySQL model_registry table.
"""
import datetime as dt
import json, os, shutil, time
import joblib
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

ACCEPTANCE = {"max_auc_drop": 0.002, "max_prauc_drop": 0.002, "max_brier_increase": 0.002, "max_recall_drop_same_alerts": 0.01,
              "max_worst_group_auc_drop": 0.02, "max_p95_latency_ratio": 2.0}

def _path(models_dir): return os.path.join(models_dir, "registry.json")
def _now(): return dt.datetime.now(dt.timezone.utc).isoformat()

def load(models_dir):
    p = _path(models_dir)
    return json.load(open(p)) if os.path.exists(p) else {"models": []}

def _save(reg, models_dir):
    with open(_path(models_dir), "w") as f:
        json.dump(reg, f, indent=2, default=str)

def register(stage, version, models_dir, role="candidate", approval_status="PENDING_APPROVAL", extra=None):
    """Add (or refresh) the entry for models/<stage>/versions/v<version>. Reads that version's metadata file."""
    vdir = os.path.join(models_dir, stage, "versions", f"v{version}")
    meta = json.load(open(os.path.join(vdir, "model_metadata.json")))
    reg = load(models_dir)
    reg["models"] = [m for m in reg["models"] if not (m["prediction_stage"] == stage and m["model_version"] == version)]
    entry = {"model_id": f"{stage}-v{version}", "model_name": f"RouteMind {stage} {meta.get('algorithm', '')}", "model_version": version,
             "prediction_stage": stage, "dataset_version": {"sha256": meta.get("dataset_sha256"), "rows": meta.get("dataset_rows")},
             "training_date": meta.get("trained_at"), "target_definition_version": meta.get("target_definition_version", "target_v1 (original label, all rows)"),
             "feature_list": meta.get("feature_names_raw"), "preprocessing_version": meta.get("preprocessing_version", version),
             "calibration_method": meta.get("calibration_method"), "calibration_version": version, "decision_threshold": meta.get("decision_threshold"),
             "model_parameters": meta.get("selected_model_params"), "evaluation_metrics": {"validation": meta.get("validation_metrics"), "test": meta.get("test_metrics")},
             "artifact_location": os.path.relpath(os.path.join(vdir, "best_model.joblib"), models_dir).replace("\\", "/"),
             "role": role, "approval_status": approval_status, "approved_by": None, "approved_at": None, "deployed_at": None,
             "registered_at": _now(), **(extra or {})}
    reg["models"].append(entry); _save(reg, models_dir)
    return entry

def get(stage, version, models_dir):
    for m in load(models_dir)["models"]:
        if m["prediction_stage"] == stage and m["model_version"] == version:
            return m
    return None

def production(stage, models_dir):
    for m in load(models_dir)["models"]:
        if m["prediction_stage"] == stage and m["role"] == "production":
            return m
    return None

def _copy_to_current(stage, version, models_dir):
    vdir = os.path.join(models_dir, stage, "versions", f"v{version}")
    for n in ["best_model.joblib", "feature_schema.json", "model_metadata.json"]:
        shutil.copy2(os.path.join(vdir, n), os.path.join(models_dir, stage, n))

def attach_acceptance(stage, version, models_dir, report):
    reg = load(models_dir)
    for m in reg["models"]:
        if m["prediction_stage"] == stage and m["model_version"] == version:
            m["acceptance_report"] = report
    _save(reg, models_dir)

def promote(stage, version, approved_by, models_dir):
    """Human-approved promotion. Raises unless a passing acceptance report is attached and an approver is named."""
    if not approved_by or not str(approved_by).strip():
        raise PermissionError("promotion requires the name of a human approver")
    reg = load(models_dir)
    cand = next((m for m in reg["models"] if m["prediction_stage"] == stage and m["model_version"] == version), None)
    if cand is None:
        raise KeyError(f"{stage} v{version} is not registered")
    if not cand.get("acceptance_report", {}).get("passed"):
        raise PermissionError("promotion refused: no PASSING champion-challenger acceptance report is attached to this candidate")
    for m in reg["models"]:
        if m["prediction_stage"] != stage:
            continue
        if m["role"] == "previous":
            m["role"] = "archived"
        if m["role"] == "production":
            m["role"] = "previous"
    cand.update(role="production", approval_status="APPROVED", approved_by=approved_by, approved_at=_now(), deployed_at=_now())
    _save(reg, models_dir)
    _copy_to_current(stage, version, models_dir)       # keep the legacy 'current' files in sync for older callers
    return cand

def rollback(stage, models_dir, by):
    """Make the 'previous' model production again; the rolled-back model keeps its record (never deleted)."""
    reg = load(models_dir)
    cur = next((m for m in reg["models"] if m["prediction_stage"] == stage and m["role"] == "production"), None)
    prev = next((m for m in reg["models"] if m["prediction_stage"] == stage and m["role"] == "previous"), None)
    if prev is None:
        raise LookupError("no previous model to roll back to")
    if cur:
        cur.update(role="archived", approval_status="ROLLED_BACK", rolled_back_by=by, rolled_back_at=_now())
    prev.update(role="production", deployed_at=_now(), restored_by=by)
    _save(reg, models_dir)
    _copy_to_current(stage, prev["model_version"], models_dir)
    return prev

# ------------------------------------------------------------------ champion vs challenger
def _probs(bundle, raw):
    return bundle["calibrator"].transform(bundle["pipeline"].predict_proba(raw)[:, 1])

def _recall_at_alert_rate(y, p, rate):
    thr = np.quantile(p, 1 - rate); return float(((p >= thr) & (y == 1)).sum() / max((y == 1).sum(), 1))

def _p95_latency_ms(bundle, raw, n=150):
    ts = []
    for i in range(n):
        t = time.perf_counter(); bundle["pipeline"].predict_proba(raw.iloc[[i]]); ts.append((time.perf_counter() - t) * 1000)
    return float(np.percentile(ts, 95))

def champion_challenger(champion, challenger, raw, y, group_col="Shipping Mode", criteria=None):
    """Both models are scored on the SAME labelled rows. Returns a report dict with per-criterion pass/fail."""
    c = {**ACCEPTANCE, **(criteria or {})}
    pc, pn = _probs(champion, raw), _probs(challenger, raw)
    alert_rate = float((pc >= champion["threshold"]).mean())
    m = lambda p: {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p), "brier": brier_score_loss(y, p),
                   "recall_at_champion_alert_rate": _recall_at_alert_rate(y, p, alert_rate)}
    mc, mn = m(pc), m(pn)
    worst = {}
    for name, p in (("champion", pc), ("challenger", pn)):
        aucs = [roc_auc_score(y[raw[group_col].values == g], p[raw[group_col].values == g]) for g in np.unique(raw[group_col].values)
                if len(set(y[raw[group_col].values == g])) == 2 and (raw[group_col].values == g).sum() >= 200]
        worst[name] = float(min(aucs))
    lc, ln = _p95_latency_ms(champion, raw), _p95_latency_ms(challenger, raw)
    checks = {"roc_auc_not_worse": mn["roc_auc"] >= mc["roc_auc"] - c["max_auc_drop"],
              "pr_auc_not_worse": mn["pr_auc"] >= mc["pr_auc"] - c["max_prauc_drop"],
              "brier_not_worse": mn["brier"] <= mc["brier"] + c["max_brier_increase"],
              "recall_same_alert_rate_not_worse": mn["recall_at_champion_alert_rate"] >= mc["recall_at_champion_alert_rate"] - c["max_recall_drop_same_alerts"],
              "worst_subgroup_auc_not_worse": worst["challenger"] >= worst["champion"] - c["max_worst_group_auc_drop"],
              "latency_p95_within_limit": ln <= c["max_p95_latency_ratio"] * lc}
    return {"passed": bool(all(checks.values())), "checks": checks, "champion": {**mc, "worst_subgroup_auc": worst["champion"], "p95_latency_ms": lc},
            "challenger": {**mn, "worst_subgroup_auc": worst["challenger"], "p95_latency_ms": ln}, "criteria": c,
            "evaluated_rows": int(len(y)), "alert_rate_used": alert_rate, "evaluated_at": _now(),
            "note": "Evaluated on VALIDATION-period eligible rows (the final test period stays untouched)."}

if __name__ == "__main__":      # python src\model_registry.py list | promote <version> <approver> | rollback <approver>
    import sys
    from load_data import MODELS
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    try:
        if cmd == "list":
            for m in load(MODELS)["models"]:
                print(f"{m['model_id']:<24} role={m['role']:<11} approval={m['approval_status']:<40} acceptance_passed={m.get('acceptance_report', {}).get('passed')}")
        elif cmd == "promote":
            print("PROMOTED:", promote("order_creation", sys.argv[2], sys.argv[3], MODELS)["model_id"])
        elif cmd == "rollback":
            print("ROLLED BACK to:", rollback("order_creation", MODELS, sys.argv[2])["model_id"])
        else:
            print("usage: model_registry.py list | promote <version> <approver name> | rollback <approver name>")
    except (PermissionError, KeyError, LookupError, IndexError) as e:
        print("REFUSED:", e); sys.exit(1)
