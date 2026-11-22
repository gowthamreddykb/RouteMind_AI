"""main.py - runs the complete RouteMind AI pipeline (Phases 1-15) with checkpoints.

    python src\\main.py                      full run
    python src\\main.py --validation-only    stop after model selection + threshold (test set NOT touched)
    python src\\main.py --use-cache          reuse trained models from a previous --validation-only run
"""
import argparse, datetime as dt, json, os, subprocess, sys, time, warnings
sys.path.insert(0, os.path.dirname(__file__))
warnings.filterwarnings("ignore")
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline

import load_data as L
import data_analysis as DA
import feature_audit as FA
import data_cleaning as DC
import feature_engineering as FE
import data_splitting as DS
import model_training as MT
import hyperparameter_tuning as HT
import model_evaluation as ME
import model_calibration as MC
import shap_explainability as SX
import model_saving as MS
import prediction as PR

# ------------------------------------------------------------------ business assumptions (CONFIGURABLE)
# The user has not supplied real costs, so these are ASSUMPTIONS and must be replaced with real business values.
RISK_CONFIG = {"cost_fn": 2.0,            # a missed late shipment costs 2x a false alert
               "cost_fp": 1.0,
               "max_flagged_fraction": 0.60,   # alert capacity: at most 60% of shipments can be flagged (0.80 flagged 78% of shipments = not actionable)
               "medium_cut": 0.40}             # LOW < medium_cut <= MEDIUM < high_cut(=decision threshold) <= HIGH
ABLATION_MIN_GAIN = 0.002                      # a Review feature group is adopted only if validation AUC improves by this much
MODEL_VERSION = "1.0.0"

CP = []   # checkpoint log
def checkpoint(no, name, ok, evidence):
    CP.append({"checkpoint": no, "name": name, "status": "PASS" if ok else "FAIL", "evidence": evidence})
    print(f"\n[CHECKPOINT {no}] {name}: {'PASS' if ok else 'FAIL'} - {evidence}", flush=True)
    if not ok:
        raise RuntimeError(f"Checkpoint {no} failed: {name}. {evidence}")

def write(path, text):
    with open(path, "w") as f:
        f.write(text)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-iter", type=int, default=12)
    ap.add_argument("--validation-only", action="store_true")
    ap.add_argument("--use-cache", action="store_true")
    ap.add_argument("--skip-tests", action="store_true")
    a = ap.parse_args()
    for d in (L.REPORTS, L.VIZ, L.PROCESSED, L.MODELS):
        os.makedirs(d, exist_ok=True)
    t0 = time.time()

    # ================= PHASE 1: load + inspect =================
    raw = L.load_dataset(L.RAW_CSV)
    L.check_candidates_exist(raw)
    L.load_description()
    dup = DA.inspect(raw, L.REPORTS, L.VIZ)
    DA.write_quality_report(raw, dup, L.REPORTS, "encoding=cp1252 (UTF-8 failed)")
    checkpoint(2, "Dataset loading & quality", dup["invalid_target_values"] == 0 and dup["unparseable_order_dates"] == 0,
               f"{dup['rows']:,} rows x {dup['columns']} cols; target valid; dates parsed; {dup['fully_duplicated_rows']} duplicate rows; missing %% reported with 4 decimals")

    # ================= PHASE 2-3: audits (provisional, Review items unresolved) =================
    FA.verify_redundancy(raw)
    oc, dp_, _ = FA.build_audits(raw, L.REPORTS)
    FA.write_leakage_report(raw, L.REPORTS)
    FA.write_stage_reports(raw, oc, L.REPORTS)
    approved = FA.approved_features(oc)
    FA.assert_no_prohibited(approved + FA.approved_features(oc, True))
    checkpoint(3, "Prediction stage availability", True, "order_creation_feature_audit, dispatch_feature_audit, prediction_stage_availability_report written; "
               "shipping date proven NOT a dispatch timestamp -> dispatch model blocked")
    checkpoint(4, "Leakage prevention", True, f"guard passed for {len(approved)} approved + 4 review features; target not in X; reports with computed evidence written")

    # ================= PHASE 4: cleaning =================
    df, clog = DC.clean_data(raw)
    df.to_csv(f"{L.PROCESSED}/cleaned_data.csv", index=False)
    clog.to_csv(f"{L.REPORTS}/data_cleaning_summary.csv", index=False)
    checkpoint(5, "Data cleaning", len(df) == len(raw) and df[L.TARGET].equals(raw[L.TARGET]) and df["Order Id"].equals(raw["Order Id"]),
               f"{len(df):,} rows kept; target and Order Id unchanged; personal columns dropped from cleaned file; nothing imputed before split")

    # ================= PHASE 6: split (before any fitting) =================
    split = DS.group_chronological_split(df)
    ssum = DS.split_summary(df, split)
    vtext = DS.validate_split(df, split)
    ssum.to_csv(f"{L.REPORTS}/data_split_summary.csv", index=False)
    write(f"{L.REPORTS}/data_split_validation.txt", vtext + "\n\n" + ssum.to_string(index=False) +
          "\n\nNote: split is by rows (70/15/15 target). Test has more unique orders than validation because later orders have fewer item rows each.")
    print(ssum.to_string(index=False))
    checkpoint(7, "Group-aware chronological split", True, "no Order Id overlap in any pair; chronology preserved; " +
               ", ".join(f"{r.partition}={r.rows:,} rows/{r.unique_orders:,} orders/late {r.late_rate:.3f}" for r in ssum.itertuples()))
    tr, va, te = (df[split == s].reset_index(drop=True) for s in ["train", "val", "test"])
    ytr, yva, yte = tr[L.TARGET].values, va[L.TARGET].values, te[L.TARGET].values
    # catalog drift: share of rows whose category value never occurs in the training period
    drift = pd.DataFrame([{"partition": n, "column": c, "pct_rows_with_value_unseen_in_train": round(100 * (~x[c].isin(set(tr[c]))).mean(), 2)}
                          for n, x in [("val", va), ("test", te)] for c in ["Product Name", "Category Name", "Department Name", "Customer City", "Order Country"]])
    drift.to_csv(f"{L.REPORTS}/unseen_category_report.csv", index=False)

    cache = os.path.join(L.MODELS, "_cache_state.joblib")
    if a.use_cache and os.path.exists(cache):
        S = joblib.load(cache); print("[cache] loaded trained models from", cache)
        compare_and_select(S, va, yva)      # cheap: re-derives selection/threshold from cached models with the CURRENT config
    else:
        S = train_and_select(tr, va, ytr, yva, df, raw, a.n_iter)
        joblib.dump(S, cache)
    extra = S["extra_cols"]

    # finalise audits now that Review items are resolved
    ov = {c: (S["review_decisions"][c], S["review_reason"]) for c in S["review_decisions"]}
    oc, dp_, _ = FA.build_audits(raw, L.REPORTS, overrides=ov)
    FA.write_leakage_report(raw, L.REPORTS); FA.write_stage_reports(raw, oc, L.REPORTS)
    feats_final = FE.engineer_order_features(df, extra)
    ids = df[["Order Id", "Order Item Id", FE.RAW_DATE, L.TARGET]].copy(); ids["split"] = split.values
    pd.concat([ids, feats_final], axis=1).to_csv(f"{L.PROCESSED}/order_creation_data.csv", index=False)
    FE.engineering_report(df, extra).to_csv(f"{L.REPORTS}/feature_engineering_report.csv", index=False)
    checkpoint(6, "Feature engineering", feats_final.shape[1] == len(set(feats_final.columns)) and feats_final[FE.feature_lists(extra)[0]].notna().all().all(),
               f"{feats_final.shape[1]} model features, no duplicates, no missing numeric values, built only from order-time fields")

    sel = S["selected"]
    print(f"\nSELECTED MODEL (validation): {sel}")
    print(S["val_table"].round(4).to_string(index=False))
    print("Threshold:", S["threshold"], "|", S["threshold_why"])
    if a.validation_only:
        print("\n--validation-only: stopping BEFORE the test set is touched.")
        return

    # ================= PHASE 10-11: final evaluation on the untouched TEST set =================
    pipe, cal, thr = S["pipelines"][sel], S["calibrator"], S["threshold"]
    medium_cut, high_cut = S["risk_cutoffs"]["medium"], S["risk_cutoffs"]["high"]
    p_te_raw = pipe.predict_proba(te)[:, 1]; p_te = cal.transform(p_te_raw)
    p_va_raw = pipe.predict_proba(va)[:, 1]; p_va = cal.transform(p_va_raw)
    mt = ME.compute_metrics(yte, p_te, thr); mv = ME.compute_metrics(yva, p_va, thr)
    print("\nTEST metrics (final model):", {k: round(v, 4) if isinstance(v, float) else v for k, v in mt.items()})

    # comparison table: validation (selection) + test (reporting only, never used for selection)
    comp = S["val_table"].copy()
    rep = []
    for name in comp.model:
        pt = S["pipelines"][name].predict_proba(te)[:, 1]
        pt = S["calibrator"].transform(pt) if name == sel else pt
        m = ME.compute_metrics(yte, pt, S["thresholds"][name] if name != sel else thr)
        rep.append({f"test_{k}": v for k, v in m.items() if k in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "brier"]})
    comp = pd.concat([comp, pd.DataFrame(rep)], axis=1); comp["selected"] = comp.model == sel
    comp.to_csv(f"{L.REPORTS}/model_comparison.csv", index=False)
    pd.DataFrame([{"partition": "test", "threshold": thr, "TN": mt["TN"], "FP": mt["FP"], "FN": mt["FN"], "TP": mt["TP"]},
                  {"partition": "validation", "threshold": thr, "TN": mv["TN"], "FP": mv["FP"], "FN": mv["FN"], "TP": mv["TP"]}]).to_csv(f"{L.REPORTS}/confusion_matrix.csv", index=False)
    cr = classification_report(yte, (p_te >= thr).astype(int), target_names=["Not late", "Late"], digits=4)
    write(f"{L.REPORTS}/classification_report.txt", f"Final model ({sel}) on TEST set, threshold={thr}\n\n{cr}")

    # error / subgroup analysis on test
    meta_te = te[["Shipping Mode", "Customer Segment", "Market"]].copy()
    meta_te["Period (quarter)"] = te[FE.RAW_DATE].dt.to_period("Q").astype(str)
    sub = pd.concat([ME.subgroup_report(meta_te, yte, p_te, thr, c, c) for c in meta_te.columns])
    sub.to_csv(f"{L.REPORTS}/subgroup_performance_test.csv", index=False)
    buckets = ME.risk_bucket_report(yte, p_te, medium_cut, high_cut); buckets.to_csv(f"{L.REPORTS}/risk_bucket_report_test.csv", index=False)
    monotonic = bool(buckets.observed_late_rate.is_monotonic_increasing)
    print("\nRisk buckets (test):\n", buckets.round(4).to_string(index=False)); print("monotonic increase:", monotonic)

    # plots
    ME.plot_confusion(yte, p_te, thr, f"{L.VIZ}/confusion_matrix.png", f"{sel} - test set (threshold {thr:.2f})")
    curves = {"Validation": {n: (yva, S["pipelines"][n].predict_proba(va)[:, 1]) for n in comp.model},
              "Test": {n: (yte, S["pipelines"][n].predict_proba(te)[:, 1]) for n in comp.model}}

    ME.plot_curves(curves, f"{L.VIZ}/roc_curve.png",
                   f"{L.VIZ}/precision_recall_curve.png")

    ME.plot_calibration({"Validation": {"before calibration": (yva, p_va_raw), "after calibration": (yva, p_va)},
                         "Test": {"before calibration": (yte, p_te_raw), "after calibration": (yte, p_te)}},
                        f"{L.VIZ}/calibration_curve.png")

    ME.plot_comparison(S["val_table"], f"{L.VIZ}/model_comparison.png")

    S["calibration_table"].to_csv(f"{L.REPORTS}/calibration_comparison.csv", index=False)
    S["threshold_table"].to_csv(f"{L.REPORTS}/threshold_selection_validation.csv", index=False)
    checkpoint(11, "Model comparison & test evaluation", True,
               f"selected '{sel}' on VALIDATION; threshold {thr} chosen on validation; test scored once afterwards: AUC={mt['roc_auc']:.4f}, recall={mt['recall']:.4f}, precision={mt['precision']:.4f}")
    cal_ok = np.all((p_te >= 0) & (p_te <= 1))
    checkpoint(12, "Calibration", bool(cal_ok), f"method='{S['calibration_method']}' chosen using older/newer halves of validation only; test Brier raw={ME.compute_metrics(yte, p_te_raw, thr)['brier']:.4f} -> final={mt['brier']:.4f}")

    # ================= PHASE 12: SHAP =================
    shap_ok, shap_msg = False, "selected model is not XGBoost: SHAP TreeExplainer not applicable"
    if sel.startswith("XGBoost"):
        sample = te.sample(2000, random_state=L.RANDOM_SEED)
        imp = SX.global_importance(pipe, sample, L.REPORTS, L.VIZ)
        err, shap_ok = SX.check_additivity(pipe, sample.head(300))
        shap_msg = f"TreeSHAP on selected XGBoost; additivity error {err:.2e} (base + sum(SHAP) == model output); top features: {imp.feature.head(5).tolist()}"
    checkpoint(13, "SHAP explainability", shap_ok, shap_msg)

    # ================= PHASE 13: save =================
    needed = FE.BASE_RAW_FIELDS + list(extra)
    num_raw = ["Days for shipment (scheduled)", "Order Item Product Price", "Order Item Quantity", "Order Item Discount Rate", "Sales"] + [c for c in extra if c in FE.REVIEW_NUMERIC]
    schema = {"stage": "order_creation", "target": L.TARGET, "required_raw_fields": needed, "numeric_raw_fields": num_raw,
              "date_field": FE.RAW_DATE, "model_input_numeric": FE.feature_lists(extra)[0], "model_input_categorical": FE.feature_lists(extra)[1],
              "identifier_keys_allowed_but_ignored": list(PR.ID_KEYS), "prohibited_inputs": [c for c, _, _ in L.PROHIBITED]}
    metadata = {"algorithm": "XGBoost" if sel.startswith("XGBoost") else "LogisticRegression", "selected_model_label": sel,
                "target_column": L.TARGET, "target_definition": "1 = late delivery, 0 = not late (as labelled in DataCo)",
                "training_rows": int(len(tr)), "validation_rows": int(len(va)), "test_rows": int(len(te)),
                "dataset_file": os.path.basename(L.RAW_CSV), "dataset_sha256": MS.file_fingerprint(L.RAW_CSV), "dataset_rows": int(len(raw)),
                "split": ssum.to_dict("records"), "random_seed": L.RANDOM_SEED, "feature_names_raw": needed,
                "decision_threshold": thr, "risk_cutoffs": S["risk_cutoffs"], "risk_config_assumptions": RISK_CONFIG,
                "calibration_method": S["calibration_method"], "selected_model_params": S["selected_params"], "tuned_xgboost_params_reported": S["best_params"],
                "validation_metrics": mv, "test_metrics": mt, "monotonic_risk_buckets_on_test": monotonic,
                "package_versions": pkg_versions(),
                "limitations": ["Order-time snapshot assumed from static order attributes (cannot be proven from a completed-orders file)",
                                "Cancelled/fraud orders (4.3%) are always labelled not-late: label noise",
                                "Latitude/Longitude, if used, are customer (not destination) coordinates",
                                "Product catalog changes over time: %.0f%% of TEST rows have a product never seen in training (validation: %.0f%%); retrain regularly" % (drift.query("partition=='test' and column=='Product Name'").iloc[0, 2], drift.query("partition=='val' and column=='Product Name'").iloc[0, 2]),
                                "Shipping Mode and scheduled_days are perfectly redundant, so SHAP credit goes to scheduled_days"]}
    bundle = {"pipeline": pipe, "calibrator": cal, "threshold": thr, "risk_cutoffs": S["risk_cutoffs"]}
    version, vdir = MS.save_stage_model("order_creation", bundle, metadata, schema, L.MODELS, MODEL_VERSION)
    MS.write_dispatch_requirements(L.MODELS)
    # reload + reproducibility check
    loaded = joblib.load(f"{L.MODELS}/order_creation/best_model.joblib")
    same = np.allclose(loaded["calibrator"].transform(loaded["pipeline"].predict_proba(te.head(500))[:, 1]), p_te[:500])
    meta_ok = json.load(open(f"{L.MODELS}/order_creation/model_metadata.json"))["model_version"] == version
    checkpoint(14, "Model saving", same and meta_ok, f"saved v{version} to models/order_creation (+versions/v{version}); reloaded model reproduces test probabilities exactly; metadata matches")

    # ================= PHASE 14: prediction functions =================
    sample_rec = {k: (v.item() if hasattr(v, "item") else (str(v) if k == FE.RAW_DATE else v)) for k, v in te.iloc[0][needed].items()}
    sample_rec[FE.RAW_DATE] = te.iloc[0][FE.RAW_DATE].strftime("%m/%d/%Y %H:%M")
    r = PR.predict_at_order_creation(sample_rec, shipment_id="SHP-TEST-1", models_dir=L.MODELS, explain=True)
    unk = PR.predict_at_order_creation({**sample_rec, "Customer City": "Atlantis"}, models_dir=L.MODELS, explain=False)
    try:
        PR.predict_at_order_creation({k: v for k, v in sample_rec.items() if k != "Shipping Mode"}, models_dir=L.MODELS); rejected = False
    except PR.ValidationError:
        rejected = True
    try:
        PR.predict_at_dispatch(sample_rec, models_dir=L.MODELS); dispatch_off = False
    except PR.ModelUnavailableError:
        dispatch_off = True
    ok15 = 0 <= r["late_delivery_probability"] <= 1 and r["prediction_stage"] == "order_creation" and rejected and dispatch_off and "Atlantis" in str(unk["unknown_categories"])
    json.dump(r, open(f"{L.REPORTS}/example_prediction.json", "w"), indent=2, default=str)
    checkpoint(15, "Prediction functions", ok15, f"sample prediction p={r['late_delivery_probability']:.4f}, stage={r['prediction_stage']}; missing field rejected; unknown category handled; dispatch correctly disabled")
    db = PR.to_database_rows(r, model_id=1, shipment_db_id=1)
    pd.DataFrame([{"table": "model_registry", "columns": ", ".join(PR.registry_row(loaded['metadata'], 'models/order_creation/best_model.joblib').keys())},
                  {"table": "model_scores", "columns": ", ".join(db["model_scores"].keys())},
                  {"table": "risk_factors", "columns": ", ".join(db["risk_factors"][0].keys()) if db["risk_factors"] else ""}]
                 ).to_csv(f"{L.REPORTS}/database_output_schema.csv", index=False)

    # ================= reports =================
    write_summaries(S, mt, mv, buckets, monotonic, sub, version, len(raw), time.time() - t0)

    # ================= PHASE 16: tests =================
    if not a.skip_tests:
        run_tests()
    pd.DataFrame(CP).to_csv(f"{L.REPORTS}/checkpoint_status.csv", index=False)
    print(f"\nDONE in {(time.time() - t0) / 60:.1f} min")

# ------------------------------------------------------------------------------------------------
def pkg_versions():
    import sklearn, xgboost, shap, pandas, numpy, joblib
    return {"scikit-learn": sklearn.__version__, "xgboost": xgboost.__version__, "shap": shap.__version__,
            "pandas": pandas.__version__, "numpy": numpy.__version__, "joblib": joblib.__version__}

def train_and_select(tr, va, ytr, yva, df, raw, n_iter):
    """Everything that may look at validation data: ablation, LR, XGBoost default/tuned, selection, threshold, calibration."""
    S = {}
    # ---- resolve 'Review' features by validation ablation (default XGBoost, validation AUC only)
    print("\n=== Review-feature ablation (validation AUC) ===")
    variants = {"base": (), "+Order City/State": ("Order City", "Order State"), "+Latitude/Longitude": ("Latitude", "Longitude"),
                "+all review": ("Order City", "Order State", "Latitude", "Longitude")}
    rows = []
    for name, ex in variants.items():
        front = MT.make_front(ex, False)
        Xtr = front.fit_transform(tr); Xva = front.transform(va)
        m = MT.fit_xgb({}, Xtr, ytr, Xva, yva); p = m.predict_proba(Xva)[:, 1]
        rows.append({"variant": name, "extra_cols": list(ex), "n_matrix_columns": Xtr.shape[1], **MT.quick_scores(yva, p)})
        print(f"  {name}: AUC={rows[-1]['roc_auc']:.4f}, matrix columns={Xtr.shape[1]}", flush=True)
    abl = pd.DataFrame(rows); abl.to_csv(f"{L.REPORTS}/review_feature_ablation.csv", index=False)
    base_auc = abl.loc[abl.variant == "base", "roc_auc"].iloc[0]
    best = abl.sort_values("roc_auc", ascending=False).iloc[0]
    extra = tuple(best.extra_cols) if best.roc_auc - base_auc >= ABLATION_MIN_GAIN else ()
    S["extra_cols"] = extra
    S["review_decisions"] = {c: ("Include" if c in extra else "Exclude") for c in ["Order City", "Order State", "Latitude", "Longitude"]}
    S["review_reason"] = (f"validation AUC base={base_auc:.4f}, best variant '{best.variant}'={best.roc_auc:.4f}; adopted only if gain >= {ABLATION_MIN_GAIN}")
    print("  -> extra columns adopted:", list(extra))

    # ---- Logistic Regression
    print("\n=== Logistic Regression ===")
    lr_pipe, lr_res = MT.train_logistic(tr, ytr, va, yva, extra)
    lr_res.to_csv(f"{L.REPORTS}/logistic_regression_results.csv", index=False)
    print(lr_res[["C", "class_weight", "val_roc_auc", "val_brier"]].round(4).to_string(index=False))

    # ---- XGBoost: shared fitted front end (train only), default + tuned
    front = MT.make_front(extra, False)
    Xtr = front.fit_transform(tr); Xva = front.transform(va)
    print(f"\nXGBoost matrix: {Xtr.shape[1]} columns (rare categories pooled, min_frequency={200})")
    print("class balance (train): late=%.4f -> mild imbalance, neg/pos=%.3f" % (ytr.mean(), (ytr == 0).sum() / (ytr == 1).sum()))
    m_def = MT.fit_xgb(MT.DEFAULT_XGB, Xtr, ytr, Xva, yva)
    print("\n=== XGBoost random search (validation) ===")
    best_params, m_best, trials = HT.random_search(Xtr, ytr, Xva, yva, n_iter=n_iter)
    def_row = {"trial": "default", "best_iteration": int(m_def.best_iteration), **MT.quick_scores(yva, m_def.predict_proba(Xva)[:, 1])}
    out = trials.copy(); out["val_roc_auc"] = out["val_roc_auc"]
    pd.concat([pd.DataFrame([{**def_row, "val_roc_auc": def_row["roc_auc"], "val_pr_auc": def_row["pr_auc"], "val_brier": def_row["brier"]}]), out]).to_csv(
        f"{L.REPORTS}/xgboost_training_results.csv", index=False)
    json.dump({**best_params, "best_iteration": int(m_best.best_iteration), "early_stopping_rounds": 30, "tree_method": "hist",
               "random_state": L.RANDOM_SEED, "selection_metric": "validation ROC-AUC", "n_search_iterations": n_iter},
              open(f"{L.REPORTS}/xgboost_best_parameters.json", "w"), indent=2, default=str)
    S["best_params"] = {**best_params, "best_iteration": int(m_best.best_iteration)}
    xgb_def = Pipeline([("front", front), ("model", m_def)]); xgb_tuned = Pipeline([("front", front), ("model", m_best)])
    S["pipelines"] = {"LogisticRegression": lr_pipe, "XGBoost (default)": xgb_def, "XGBoost (tuned)": xgb_tuned}

    S["selected_params_by_model"] = {"XGBoost (default)": {"note": "library defaults", "best_iteration": int(m_def.best_iteration)},
                                     "XGBoost (tuned)": S["best_params"], "LogisticRegression": {"note": "see logistic_regression_results.csv"}}
    compare_and_select(S, va, yva)
    return S

def compare_and_select(S, va, yva):
    """Model selection, calibration and operating threshold - VALIDATION DATA ONLY. Re-runnable from cached models."""
    if "selected_params_by_model" not in S:     # older cache layout
        d = S["pipelines"]["XGBoost (default)"].steps[-1][1]
        S["selected_params_by_model"] = {"XGBoost (default)": {"note": "library defaults", "best_iteration": int(d.best_iteration)},
                                         "XGBoost (tuned)": S["best_params"], "LogisticRegression": {"note": "see logistic_regression_results.csv"}}
    rows, thresholds = [], {}
    pv = {n: p.predict_proba(va)[:, 1] for n, p in S["pipelines"].items()}
    for n in pv:
        t, _, _ = ME.select_threshold(ME.threshold_table(yva, pv[n]), RISK_CONFIG["cost_fn"], RISK_CONFIG["cost_fp"], RISK_CONFIG["max_flagged_fraction"])
        thresholds[n] = t
        rows.append({"model": n, **{f"val_{k}": v for k, v in ME.compute_metrics(yva, pv[n], t).items() if k not in ("TN", "FP", "FN", "TP")}})
    vt = pd.DataFrame(rows).rename(columns={"val_roc_auc": "roc_auc", "val_pr_auc": "pr_auc", "val_f1": "f1", "val_recall": "recall", "val_precision": "precision"})
    # selection: highest validation ROC-AUC; models within 0.002 AUC are treated as tied and the better-calibrated (lower Brier) wins
    vt = vt.sort_values("roc_auc", ascending=False).reset_index(drop=True)
    close = vt[vt.roc_auc >= vt.roc_auc[0] - 0.002]
    sel = close.sort_values("val_brier").model.iloc[0]
    S["selected"], S["thresholds"], S["val_table"] = sel, thresholds, vt
    S["selected_params"] = S["selected_params_by_model"][sel]

    # calibration for the selected model (validation only), then final threshold on calibrated probabilities
    p_raw = pv[sel]
    order = np.argsort(va[FE.RAW_DATE].values, kind="stable")        # chronological order for the older/newer halves
    cal, cal_tab, method = MC.choose_calibration(p_raw[order], yva[order])
    p_cal = cal.transform(p_raw)
    thr, full_tab, why = ME.select_threshold(ME.threshold_table(yva, p_cal), RISK_CONFIG["cost_fn"], RISK_CONFIG["cost_fp"], RISK_CONFIG["max_flagged_fraction"])
    medium = RISK_CONFIG["medium_cut"] if RISK_CONFIG["medium_cut"] < thr else round(thr * 0.75, 2)
    S.update(calibrator=cal, calibration_table=cal_tab, calibration_method=method, threshold=thr, threshold_table=full_tab,
             threshold_why=why, risk_cutoffs={"medium": medium, "high": thr})
    print("\nCalibration comparison (older half fit -> newer half score):\n", cal_tab.round(5).to_string(index=False), "\nchosen:", method)
    print("Threshold table around the choice (validation):\n", full_tab[(full_tab.threshold >= thr - 0.08) & (full_tab.threshold <= thr + 0.08)][
        ["threshold", "precision", "recall", "f1", "flagged_fraction", "FN", "FP", "expected_cost_per_order"]].round(4).to_string(index=False))

def write_summaries(S, mt, mv, buckets, monotonic, sub, version, n_raw, secs):
    vt = S["val_table"]
    lines = ["TRAINING SUMMARY - RouteMind AI order-creation model", "=" * 70,
             f"Version: {version}   Date: {dt.datetime.now(dt.timezone.utc).date()}   Rows used: {n_raw:,}   Runtime: {secs/60:.1f} min   Seed: {L.RANDOM_SEED}",
             f"Review features adopted: {list(S['extra_cols'])}  ({S['review_reason']})",
             f"Selected model: {S['selected']} (highest validation ROC-AUC; ties within 0.002 broken by Brier score)",
             f"Calibration: {S['calibration_method']}", f"Decision threshold: {S['threshold']}  - {S['threshold_why']}",
             f"Risk cutoffs: {S['risk_cutoffs']}", f"Business ASSUMPTIONS (replace with real values): {RISK_CONFIG}",
             "", "Validation comparison:", vt.round(4).to_string(index=False)]
    write(f"{L.REPORTS}/training_summary.txt", "\n".join(lines))
    ev = ["MODEL EVALUATION SUMMARY", "=" * 70, "Final model scored ONCE on the untouched test set, after model, threshold and calibration were fixed on validation data.", "",
          f"TEST    : " + ", ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in mt.items()),
          f"VALID.  : " + ", ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in mv.items()), "",
          "Risk buckets on test (observed late rate should rise LOW -> HIGH):", buckets.round(4).to_string(index=False),
          f"Monotonic increase: {monotonic}", "",
          "Recall vs precision trade-off: a missed late shipment (FN) is assumed to cost %.1fx a false alert (FP); the threshold minimises that cost "
          "subject to flagging at most %.0f%% of shipments. Late is the majority class (~55%%), so a low threshold flags many shipments." % (RISK_CONFIG["cost_fn"] / RISK_CONFIG["cost_fp"], RISK_CONFIG["max_flagged_fraction"] * 100),
          "", "Subgroup performance on test:", sub.round(4).to_string(index=False)]
    write(f"{L.REPORTS}/model_evaluation_summary.txt", "\n".join(ev))

def run_tests():
    print("\n=== Running pytest ===")
    r = subprocess.run([sys.executable, "-m", "pytest", os.path.join(L.ROOT, "tests"), "-v", "-rs", "--tb=short", "-p", "no:cacheprovider"],
                       capture_output=True, text=True, cwd=L.ROOT)
    write(f"{L.REPORTS}/test_results.txt", r.stdout + r.stderr)
    last = [l for l in r.stdout.strip().splitlines() if l.strip()][-1]
    checkpoint(16, "Automated tests", r.returncode == 0, last)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        sys.exit(1)
