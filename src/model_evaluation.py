"""model_evaluation.py - Phase 10: metrics, threshold selection, subgroup/error analysis, plots."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
                             average_precision_score, brier_score_loss, confusion_matrix, classification_report,
                             roc_curve, precision_recall_curve, log_loss)

def compute_metrics(y, p, thr):
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"threshold": round(float(thr), 4), "accuracy": accuracy_score(y, pred),
            "precision": precision_score(y, pred, zero_division=0), "recall": recall_score(y, pred),
            "f1": f1_score(y, pred), "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "brier": brier_score_loss(y, p), "log_loss": log_loss(y, np.clip(p, 1e-6, 1 - 1e-6)),
            "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp), "flagged_fraction": float(pred.mean())}

def threshold_table(y, p, grid=None):
    grid = np.round(np.arange(0.05, 0.96, 0.01), 2) if grid is None else grid
    return pd.DataFrame([compute_metrics(y, p, t) for t in grid])

def select_threshold(tab, cost_fn, cost_fp, max_flagged_fraction):
    """Minimise expected cost = cost_fn*FN + cost_fp*FP on VALIDATION, subject to an alert-capacity cap.
    cost_fn, cost_fp and the cap are business assumptions (configurable)."""
    t = tab.copy()
    t["expected_cost_per_order"] = (cost_fn * t.FN + cost_fp * t.FP) / (t.TN + t.FP + t.FN + t.TP)
    ok = t[t.flagged_fraction <= max_flagged_fraction]
    feasible = len(ok) > 0
    pick = (ok if feasible else t).sort_values(["expected_cost_per_order", "threshold"]).iloc[0]
    why = (f"Minimum expected cost (FN cost={cost_fn}, FP cost={cost_fp}) among thresholds that flag at most "
           f"{max_flagged_fraction:.0%} of shipments (alert capacity). " if feasible else
           "No threshold satisfied the capacity cap; chose minimum cost overall. ")
    return float(pick.threshold), t, why

def risk_level(p, medium_cut, high_cut):
    return np.where(p >= high_cut, "HIGH", np.where(p >= medium_cut, "MEDIUM", "LOW"))

def risk_bucket_report(y, p, medium_cut, high_cut):
    lv = pd.Series(risk_level(p, medium_cut, high_cut))
    d = pd.DataFrame({"risk": lv, "y": np.asarray(y)}).groupby("risk").y.agg(["size", "sum", "mean"])
    d = d.reindex(["LOW", "MEDIUM", "HIGH"]).rename(columns={"size": "shipments", "sum": "late_shipments", "mean": "observed_late_rate"})
    d["share_of_shipments"] = d["shipments"] / d["shipments"].sum()
    return d.reset_index()

def subgroup_report(meta, y, p, thr, col, label):
    rows = []
    d = meta.copy(); d["y"] = np.asarray(y); d["p"] = p; d["pred"] = (p >= thr).astype(int)
    for g, x in d.groupby(col):
        if len(x) < 50:
            continue
        fn = ((x.pred == 0) & (x.y == 1)).sum(); fp = ((x.pred == 1) & (x.y == 0)).sum()
        rows.append({"grouping": label, "group": str(g), "rows": len(x), "late_rate": x.y.mean(),
                     "accuracy": (x.pred == x.y).mean(), "recall": x[x.y == 1].pred.mean() if (x.y == 1).any() else np.nan,
                     "precision": x[x.pred == 1].y.mean() if (x.pred == 1).any() else np.nan,
                     "roc_auc": roc_auc_score(x.y, x.p) if x.y.nunique() == 2 else np.nan,
                     "false_negatives": int(fn), "false_positives": int(fp)})
    return pd.DataFrame(rows)

# ------------------------------------------------------------------ plots
def plot_confusion(y, p, thr, path, title):
    cm = confusion_matrix(y, (p >= thr).astype(int), labels=[0, 1])
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", color="black", fontsize=12)
    ax.set_xticks([0, 1], ["Pred not late", "Pred late"]); ax.set_yticks([0, 1], ["Actual not late", "Actual late"])
    ax.set_title(title, fontsize=10); plt.tight_layout(); plt.savefig(path, dpi=120); plt.close()

def plot_curves(curves, path_roc, path_pr):
    """curves = {panel_title: {model_name: (y, p)}}"""
    for kind, path in [("roc", path_roc), ("pr", path_pr)]:
        fig, axes = plt.subplots(1, len(curves), figsize=(5.5 * len(curves), 4.5))
        axes = np.atleast_1d(axes)
        for ax, (title, models) in zip(axes, curves.items()):
            for name, (y, p) in models.items():
                if kind == "roc":
                    f, t, _ = roc_curve(y, p); ax.plot(f, t, label=f"{name} (AUC={roc_auc_score(y, p):.3f})")
                else:
                    pr, rc, _ = precision_recall_curve(y, p); ax.plot(rc, pr, label=f"{name} (AP={average_precision_score(y, p):.3f})")
            if kind == "roc":
                ax.plot([0, 1], [0, 1], "k--", lw=0.8); ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
            else:
                ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
            ax.set_title(title); ax.legend(fontsize=8)
        plt.tight_layout(); plt.savefig(path, dpi=120); plt.close()

def plot_calibration(panels, path):
    """panels = {title: {label: (y, p)}}"""
    fig, axes = plt.subplots(1, len(panels), figsize=(5.5 * len(panels), 4.5)); axes = np.atleast_1d(axes)
    for ax, (title, series) in zip(axes, panels.items()):
        for lab, (y, p) in series.items():
            fr, mp = calibration_curve(y, p, n_bins=10, strategy="quantile")
            ax.plot(mp, fr, marker="o", label=f"{lab} (Brier={brier_score_loss(y, p):.4f})")
        ax.plot([0, 1], [0, 1], "k--", lw=0.8); ax.set_xlabel("Mean predicted probability"); ax.set_ylabel("Observed late rate")
        ax.set_title(title); ax.legend(fontsize=8)
    plt.tight_layout(); plt.savefig(path, dpi=120); plt.close()

def plot_comparison(df, path):
    m = df.set_index("model")[["roc_auc", "pr_auc", "f1", "recall", "precision"]]
    ax = m.plot(kind="bar", figsize=(8, 4.5), rot=0); ax.set_ylim(0, 1); ax.set_title("Model comparison (validation set)")
    plt.tight_layout(); plt.savefig(path, dpi=120); plt.close()
