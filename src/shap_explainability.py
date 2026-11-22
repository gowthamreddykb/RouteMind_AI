"""shap_explainability.py - Phase 12: SHAP for the selected XGBoost model.

SHAP values are in LOG-ODDS of the (uncalibrated) XGBoost model. They describe how the MODEL used each feature.
They do not prove real-world causation. One-hot columns are summed back to the original feature
(e.g. all 'Shipping Mode_*' columns -> 'Shipping Mode') so explanations are readable for the Flask app.
"""
import numpy as np
import pandas as pd
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from feature_engineering import feature_lists

def _parts(pipeline):
    """Return (feature_step, prep, model, extra_cols) from a fitted [front -> model] or [features, prep, model] pipeline."""
    steps = dict(pipeline.named_steps)
    front = steps["front"] if "front" in steps else pipeline[:-1]
    model = pipeline.steps[-1][1]
    return front.named_steps["features"], front.named_steps["prep"], model

def transformed_names(prep):
    return [n.split("__", 1)[1] for n in prep.get_feature_names_out()]

def column_to_feature(prep, numeric, categorical):
    """Map every transformed column to its original model feature."""
    mapping = []
    for n in transformed_names(prep):
        if n in numeric:
            mapping.append(n)
        else:
            owner = [c for c in sorted(categorical, key=len, reverse=True) if n.startswith(c + "_")]
            mapping.append(owner[0] if owner else n)
    return mapping

def augment(pipeline, raw_df):
    """Apply the pipeline's optional history step (adds historical-rate columns from the saved snapshot)."""
    h = pipeline.named_steps.get("history") if hasattr(pipeline, "named_steps") else None
    return h.transform(raw_df) if h is not None else raw_df

def shap_matrix(pipeline, raw_df):
    """Exact TreeSHAP on the XGBoost model. Returns (X_dense, shap_values, base_value, feature_table)."""
    feat_step, prep, model = _parts(pipeline)
    feats = feat_step.transform(augment(pipeline, raw_df))
    X = prep.transform(feats)
    X = X.toarray() if hasattr(X, "toarray") else np.asarray(X)
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X)
    sv = sv[1] if isinstance(sv, list) else sv
    base = float(np.ravel(explainer.expected_value)[-1])
    return X, np.asarray(sv), base, feats

def check_additivity(pipeline, raw_df, atol=1e-3):
    """Verifies base + sum(SHAP) == the model's own raw (log-odds) output, i.e. SHAP matches THIS model."""
    X, sv, base, _ = shap_matrix(pipeline, raw_df)
    _, _, model = _parts(pipeline)
    margin = model.predict(X, output_margin=True)
    err = float(np.max(np.abs(base + sv.sum(axis=1) - margin)))
    return err, err < atol

def global_importance(pipeline, raw_sample, reports_dir, viz_dir, max_display=20):
    feat_step, prep, model = _parts(pipeline)
    num, cat = _lists(feat_step)
    X, sv, base, feats = shap_matrix(pipeline, raw_sample)
    names = transformed_names(prep)
    owner = column_to_feature(prep, num, cat)
    abs_t = pd.DataFrame({"transformed_feature": names, "original_feature": owner, "mean_abs_shap": np.abs(sv).mean(axis=0)})
    by_orig = (pd.DataFrame(np.abs(sv), columns=owner).T.groupby(level=0).sum().T.mean()   # sum |.| over one-hot columns
               .sort_values(ascending=False).rename("mean_abs_shap").reset_index().rename(columns={"index": "feature"}))
    # signed aggregation (so one-hot contributions can cancel) is what an individual explanation shows:
    signed = pd.DataFrame(sv, columns=owner).T.groupby(level=0).sum().T
    by_orig["mean_abs_shap_aggregated"] = by_orig["feature"].map(signed.abs().mean())
    by_orig = by_orig.sort_values("mean_abs_shap_aggregated", ascending=False)
    by_orig.to_csv(f"{reports_dir}/shap_feature_importance.csv", index=False)
    abs_t.sort_values("mean_abs_shap", ascending=False).to_csv(f"{reports_dir}/shap_feature_importance_transformed.csv", index=False)
    # plots
    shap.summary_plot(sv, X, feature_names=names, max_display=max_display, show=False)
    plt.title("SHAP summary (log-odds of late delivery)", fontsize=10); plt.tight_layout()
    plt.savefig(f"{viz_dir}/shap_summary.png", dpi=120, bbox_inches="tight"); plt.close()
    top = by_orig.head(max_display).iloc[::-1]
    plt.figure(figsize=(7, 5)); plt.barh(top["feature"], top["mean_abs_shap_aggregated"], color="#3B7DDD")
    plt.xlabel("mean |SHAP| (original feature, one-hot columns summed)"); plt.title("Global feature importance (SHAP)")
    plt.tight_layout(); plt.savefig(f"{viz_dir}/shap_bar.png", dpi=120); plt.close()
    return by_orig

def _extra_cols(feat_step):
    return feat_step.kw_args.get("extra_cols", [])

def _lists(feat_step):
    return feature_lists(feat_step.kw_args.get("extra_cols", []), feat_step.kw_args.get("hist_cols", []))

def explain_rows(pipeline, raw_df, top_k=3):
    """For every row: actual SHAP contributions per ORIGINAL feature, sorted by size.
    Returns a list (one per row) of dicts {features: [...top_k...], positive: [...], negative: [...], base_value}."""
    feat_step, prep, model = _parts(pipeline)
    num, cat = _lists(feat_step)
    X, sv, base, feats = shap_matrix(pipeline, raw_df)
    owner = column_to_feature(prep, num, cat)
    signed = pd.DataFrame(sv, columns=owner).T.groupby(level=0).sum().T
    out = []
    for i in range(len(raw_df)):
        row = signed.iloc[i]
        items = []
        for f in row.index:
            val = feats.iloc[i][f]
            val = None if (isinstance(val, float) and np.isnan(val)) else (val.item() if hasattr(val, "item") else val)
            items.append({"feature": f, "feature_value": val, "shap_contribution": float(row[f]),
                          "direction": "increases_risk" if row[f] > 0 else "decreases_risk"})
        items.sort(key=lambda d: abs(d["shap_contribution"]), reverse=True)
        out.append({"top_features": items[:top_k],
                    "top_positive": [d for d in sorted(items, key=lambda d: -d["shap_contribution"]) if d["shap_contribution"] > 0][:top_k],
                    "top_negative": [d for d in sorted(items, key=lambda d: d["shap_contribution"]) if d["shap_contribution"] < 0][:top_k],
                    "base_value": base})
    return out
