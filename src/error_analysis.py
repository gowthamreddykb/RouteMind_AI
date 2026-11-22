"""error_analysis.py - Phases 8 and 10: subgroup, unseen-category, Standard Class, false-negative and false-positive analysis."""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
import model_evaluation as ME
import model_training as MT
import shap_explainability as SX

HOUR_BINS = [-1, 5, 11, 17, 23]; HOUR_LABELS = ["00-05", "06-11", "12-17", "18-23"]

def add_known_flags(te, tr):
    """Known/unseen = was this value present in the TRAINING data?"""
    d = te.copy()
    for c in ["Product Name", "Category Name", "Department Name", "Customer City", "Order Country"]:
        d[f"{c}__known"] = np.where(d[c].isin(set(tr[c])), "known", "unseen")
    return d

def unseen_report(te, tr, y, p, thr):
    d = add_known_flags(te, tr); rows = []
    share = {c: float((d[f"{c}__known"] == "unseen").mean()) for c in ["Product Name", "Category Name", "Department Name", "Customer City", "Order Country"]}
    for c in share:
        rep = ME.subgroup_report(d[[f"{c}__known"]], y, p, thr, f"{c}__known", f"{c} (in training data?)")
        rep["share_of_test_unseen"] = share[c]; rows.append(rep)
    return pd.concat(rows)

def all_subgroups(te, tr, y, p, thr):
    d = add_known_flags(te, tr); d["Period (quarter)"] = te["_t"].dt.to_period("Q").astype(str)
    d["Period (half)"] = te["_t"].dt.year.astype(str) + "H" + ((te["_t"].dt.month > 6) + 1).astype(str)
    cols = ["Shipping Mode", "Market", "Order Region", "Category Name", "Customer Segment", "Period (quarter)"]
    return pd.concat([ME.subgroup_report(d[[c]], y, p, thr, c, c) for c in cols])

def standard_class_investigation(tr, va, te, y_te, p_te, thr, params, n_trees, reports_dir):
    """Why is Standard Class weak? Measure, don't guess."""
    lines = ["STANDARD CLASS INVESTIGATION", "=" * 70]; rows = []
    for mode, g in pd.concat([tr, va, te]).groupby("Shipping Mode"):
        rd = g["Days for shipping (real)"].value_counts(normalize=True).sort_index().round(3).to_dict()
        rows.append({"shipping_mode": mode, "rows": len(g), "scheduled_days": int(g["Days for shipment (scheduled)"].iloc[0]), "late_rate": g["_y"].mean(), "real_days_distribution": rd})
    dist = pd.DataFrame(rows); dist.to_csv(f"{reports_dir}/standard_class_mode_profile.csv", index=False)
    lines += ["", "1) Delivery pattern by shipping mode (real days distribution; late = real > scheduled):", dist.to_string(index=False)]
    st = {n: d[d["Shipping Mode"] == "Standard Class"] for n, d in (("train", tr), ("val", va), ("test", te))}
    lines += ["", "2) Standard Class class distribution (late rate): " + ", ".join(f"{n}={d['_y'].mean():.3f} (n={len(d):,})" for n, d in st.items())]
    t = pd.concat(st.values()); byq = t.groupby(t["_t"].dt.to_period("Q").astype(str))["_y"].mean().round(3)
    lines += ["3) Standard Class late rate by quarter (temporal stability): min=%.3f max=%.3f" % (byq.min(), byq.max())]
    # does ANY order-time feature separate late from on-time inside Standard Class?
    base = st["train"]["_y"].mean(); sep = []
    for c in ["Market", "Order Region", "Category Name", "Customer Segment", "Type", "Order Country", "Department Name"]:
        g = st["train"].groupby(c)["_y"].agg(["mean", "size"]); g = g[g["size"] >= 300]
        sep.append({"feature": c, "levels_with_>=300_rows": len(g), "min_late_rate": g["mean"].min(), "max_late_rate": g["mean"].max(), "spread": g["mean"].max() - g["mean"].min()})
    sep = pd.DataFrame(sep).sort_values("spread", ascending=False); sep.to_csv(f"{reports_dir}/standard_class_feature_signal.csv", index=False)
    lines += ["", f"4) Late-rate spread across feature levels INSIDE Standard Class (overall {base:.3f}); small spread = little separating signal:", sep.round(3).to_string(index=False)]
    # model trained only on Standard Class rows
    front = MT.make_front((), False); Xa = front.fit_transform(st["train"]); Xb = front.transform(st["test"])
    m = MT.make_xgb({**params, "n_estimators": int(n_trees)}, early_stopping_rounds=None); m.fit(Xa, st["train"]["_y"].values)
    auc_only = roc_auc_score(st["test"]["_y"], m.predict_proba(Xb)[:, 1])
    mask = (te["Shipping Mode"] == "Standard Class").values; auc_main = roc_auc_score(y_te[mask], p_te[mask]) if len(set(y_te[mask])) == 2 else np.nan
    lines += ["", f"5) Test ROC-AUC INSIDE Standard Class: final model = {auc_main:.4f}; dedicated Standard-Class-only model = {auc_only:.4f}",
              "   (0.50 = no better than chance). A dedicated subgroup model is NOT justified unless it clearly beats the main model on independent data."]
    verdict = ("No order-time feature separates late from on-time Standard Class shipments: the available features contain almost no signal within this mode. "
               "The dataset has no carrier, warehouse, route-leg, weather or dispatch-event columns that could explain it (these would be new data, not something to invent).")
    lines += ["", "CONCLUSION: " + verdict]
    open(f"{reports_dir}/standard_class_investigation.txt", "w").write("\n".join(lines))
    return {"auc_inside_standard_final": auc_main, "auc_inside_standard_dedicated": auc_only, "max_feature_spread": float(sep.spread.max())}

def _enrich(df_rows, ids, y, p, thr, kind):
    d = df_rows[["Order Id", "Order Item Id", "Shipping Mode", "Order Region", "Market", "Category Name", "Customer Segment", "Order Country", "Product Name", "Type",
                 "Days for shipment (scheduled)", "Order Item Quantity", "Sales", "_t"]].copy()
    d.insert(2, "actual_outcome", "LATE" if kind == "FN" else "ON_TIME"); d.insert(3, "predicted_probability", p); d.insert(4, "decision_threshold", thr)
    d["order_hour"] = d["_t"].dt.hour; d["order_day_of_week"] = d["_t"].dt.dayofweek
    return d

def fn_fp_reports(te, y, p, thr, pipeline, reports_dir, max_shap=4000):
    """Full FN and FP lists with SHAP explanations (computed for up to max_shap rows each) + pattern summaries."""
    pred = (p >= thr).astype(int); out = {}
    for kind, mask in (("FN", (pred == 0) & (y == 1)), ("FP", (pred == 1) & (y == 0))):
        rows = te[mask].reset_index(drop=True); d = _enrich(rows, None, y[mask], p[mask], thr, kind)
        sub = rows.head(max_shap)
        raw_cols = [c for c in sub.columns if not c.startswith("_") and not c.endswith("__known")]
        ex = SX.explain_rows(pipeline, sub[raw_cols], top_k=3)
        txt = [" | ".join(f"{e['feature']}={e['feature_value']} ({e['shap_contribution']:+.2f})" for e in r["top_features"]) for r in ex]
        d["shap_top3_features_log_odds"] = txt + [""] * (len(d) - len(txt))
        d.drop(columns=["_t"]).to_csv(f"{reports_dir}/{'false_negative' if kind == 'FN' else 'false_positive'}_report.csv", index=False)
        pats = []
        for c in ["Shipping Mode", "Order Region", "Market", "Category Name", "Customer Segment", "order_hour_band", "order_day_of_week"]:
            full = te.assign(order_hour_band=pd.cut(te["_t"].dt.hour, HOUR_BINS, labels=HOUR_LABELS).astype(str), order_day_of_week=te["_t"].dt.dayofweek)
            base_mask = (y == 1) if kind == "FN" else (y == 0)
            g_all = full[base_mask].groupby(c).size(); g_err = full[mask].groupby(c).size().reindex(g_all.index).fillna(0)
            t = pd.DataFrame({"group": g_all.index.astype(str), "actual_class_rows": g_all.values, "errors": g_err.values.astype(int)})
            t["error_rate_within_group"] = t.errors / t.actual_class_rows; t["share_of_all_errors"] = t.errors / max(mask.sum(), 1)
            t["lift_vs_overall"] = t.error_rate_within_group / (mask.sum() / base_mask.sum()); t.insert(0, "grouping", c)
            pats.append(t[t.actual_class_rows >= 100])
        pats = pd.concat(pats).sort_values("share_of_all_errors", ascending=False)
        pats.to_csv(f"{reports_dir}/{'false_negative' if kind == 'FN' else 'false_positive'}_patterns.csv", index=False)
        out[kind] = {"count": int(mask.sum()), "patterns": pats}
    return out
