"""improve.py - Phases 2-10 and 16 of the improvement programme (training side; no live inference here).

Stages (each writes its own reports):  data -> target validation -> history features -> ablation -> imbalance ->
tuning (+time-aware CV) -> backtests -> selection/threshold/calibration -> final test -> error analysis -> save CANDIDATE.
The v1.0.0 baseline files are never modified.  Run:  python src\\improve.py [--stage-only data|ablation]
"""
import json, os, sys, time, warnings
sys.path.insert(0, os.path.dirname(__file__))
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import load_data as L
import data_cleaning as DC
import data_splitting as DS
import feature_engineering as FE
import historical_features as HF
import model_training as MT
import model_evaluation as ME
import target_validation as TV

RISK_CONFIG = {"cost_fn": 3.0,               # ASSUMPTION: a missed late shipment costs 3x a false alert
               "cost_fp": 1.0,
               "max_flagged_fraction": 0.70,  # ASSUMPTION: operations can investigate at most 70% of shipments
               "medium_cut": 0.40}
MIN_GAIN = 0.002                              # a feature group is adopted only if validation AUC improves by this much

def build_data():
    """Clean -> classify outcomes -> keep the SAME chronological/group split boundaries as baseline v1.0.0 -> eligible rows only."""
    raw = L.load_dataset(L.RAW_CSV)
    df, _ = DC.clean_data(raw)
    outcome = TV.classify_outcomes(df)
    split = DS.group_chronological_split(df)            # identical boundaries to the baseline (computed on all rows)
    df["_t"] = df[FE.RAW_DATE]
    df["_event_t"] = df[FE.RAW_DATE] + pd.to_timedelta(df["Days for shipping (real)"].clip(lower=0.5), unit="D")   # when the outcome becomes known
    df["_y"] = df[L.TARGET]
    df["_outcome"] = outcome.values; df["_split"] = split.values
    return raw, df

def add_history(tr, va, te, key_groups=None):
    """Attach time-aware historical-rate columns. train: past train events; val: past train+val events;
    test: frozen snapshot = train+val events only (no test labels are ever used as history)."""
    keys = {k: v for g, d in (key_groups or HF.KEY_GROUPS).items() for k, v in d.items()}
    ev = lambda d: d.assign(_t=d["_event_t"])
    q = lambda d: d.assign(_t=d["_t"])
    f_tr = HF.time_aware_features(ev(tr), q(tr), keys)
    both = pd.concat([tr, va])
    f_va = HF.time_aware_features(ev(both), q(va), keys)
    f_te = HF.time_aware_features(ev(both), q(te), keys)
    return pd.concat([tr, f_tr], axis=1), pd.concat([va, f_va], axis=1), pd.concat([te, f_te], axis=1), keys

def fit_eval(tr, va, ytr, yva, hist_cols=(), params=None, extra=()):
    front = MT.make_front(extra, False, hist_cols)
    Xtr = front.fit_transform(tr); Xva = front.transform(va)
    m = MT.fit_xgb(params or {}, Xtr, ytr, Xva, yva)
    p = m.predict_proba(Xva)[:, 1]
    return front, m, p, Xtr, Xva

def ablation(tr, va, ytr, yva, keys):
    rows = []
    variants = {"base (23 order-time features)": []}
    for g, d in HF.KEY_GROUPS.items():
        variants[f"+ history: {g}"] = HF.feature_names(d)
    variants["+ history: route+product+market"] = sum((HF.feature_names(HF.KEY_GROUPS[g]) for g in ["route", "product", "market"]), [])
    for name, hc in variants.items():
        t = time.time(); _, m, p, Xtr, _ = fit_eval(tr, va, ytr, yva, hc)
        rows.append({"variant": name, "hist_cols": hc, "matrix_columns": Xtr.shape[1], **MT.quick_scores(yva, p), "seconds": round(time.time() - t, 1)})
        print(f"  {name}: val AUC={rows[-1]['roc_auc']:.4f} PR-AUC={rows[-1]['pr_auc']:.4f} Brier={rows[-1]['brier']:.4f}", flush=True)
    return pd.DataFrame(rows)

PARAM_KEYS = ["n_estimators", "max_depth", "learning_rate", "min_child_weight", "subsample", "colsample_bytree",
              "gamma", "reg_alpha", "reg_lambda", "scale_pos_weight"]

def time_cv(tr, params, n_trees, folds=3):
    """Expanding-window CV INSIDE the training period (front end refit on each fold's training part; no early stopping)."""
    t = tr["_t"]; q = t.quantile([0.5, 0.67, 0.83, 1.0]).values; res = []
    for i in range(folds):
        a = tr[t <= q[i]]; b = tr[(t > q[i]) & (t <= q[i + 1])]
        assert not (set(a["Order Id"]) & set(b["Order Id"]))
        front = MT.make_front((), False); Xa = front.fit_transform(a); Xb = front.transform(b)
        m = MT.make_xgb({**params, "n_estimators": int(n_trees)}, early_stopping_rounds=None); m.fit(Xa, a["_y"].values)
        p = m.predict_proba(Xb)[:, 1]; res.append(MT.quick_scores(b["_y"].values, p)["roc_auc"])
    return res

def optimise(tr, va, n_iter=10):
    """Imbalance experiment, random search (validation) + time-aware CV on the top 3, LR, HGB challenger."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    import hyperparameter_tuning as HT
    ytr, yva = tr["_y"].values, va["_y"].values
    S = {}
    front = MT.make_front((), False); Xtr = front.fit_transform(tr); Xva = front.transform(va)
    ratio = float((ytr == 0).sum() / (ytr == 1).sum()); S["neg_pos_ratio"] = ratio
    print(f"eligible train: late={ytr.mean():.4f}, neg/pos={ratio:.3f}", flush=True)

    print("\n=== Class-imbalance experiment (default XGBoost, validation) ===", flush=True)
    rows = []
    for spw in [round(ratio, 3), 1.0, 1.25, 1.5]:
        m = MT.fit_xgb({"scale_pos_weight": spw}, Xtr, ytr, Xva, yva); p = m.predict_proba(Xva)[:, 1]
        t, _, _ = ME.select_threshold(ME.threshold_table(yva, p), RISK_CONFIG["cost_fn"], RISK_CONFIG["cost_fp"], RISK_CONFIG["max_flagged_fraction"])
        mt = ME.compute_metrics(yva, p, t)
        rows.append({"scale_pos_weight": spw, "val_roc_auc": mt["roc_auc"], "val_pr_auc": mt["pr_auc"], "val_brier": mt["brier"], "val_log_loss": mt["log_loss"],
                     "threshold": t, "precision": mt["precision"], "recall": mt["recall"], "alert_fraction": mt["flagged_fraction"], "best_iteration": int(m.best_iteration)})
        print(f"  spw={spw}: AUC={mt['roc_auc']:.4f} PR-AUC={mt['pr_auc']:.4f} Brier={mt['brier']:.4f} thr={t} P={mt['precision']:.3f} R={mt['recall']:.3f} alerts={mt['flagged_fraction']:.2f}", flush=True)
    S["imbalance"] = pd.DataFrame(rows)

    m_def = MT.fit_xgb({}, Xtr, ytr, Xva, yva)
    print("\n=== XGBoost random search (validation) ===", flush=True)
    best_params, m_best, trials = HT.random_search(Xtr, ytr, Xva, yva, n_iter=n_iter, extra_spw=(1.25, 1.5))
    top = trials.sort_values("val_roc_auc", ascending=False).head(3)
    print("\n=== Time-aware CV (3 expanding folds inside train period) for top-3 trials ===", flush=True)
    cv = []
    for _, r in top.iterrows():
        params = {k: (int(r[k]) if k in ("max_depth", "n_estimators") else float(r[k])) for k in PARAM_KEYS}
        scores = time_cv(tr, params, max(20, int(r["best_iteration"]) * 1.1))
        cv.append({"trial": int(r["trial"]), "val_roc_auc": r["val_roc_auc"], "cv_fold_aucs": scores, "cv_mean_auc": float(np.mean(scores)), "cv_std": float(np.std(scores)),
                   "composite": (r["val_roc_auc"] + float(np.mean(scores))) / 2, "params": params, "best_iteration": int(r["best_iteration"])})
        print(f"  trial {int(r['trial'])}: val={r['val_roc_auc']:.4f}  cv={np.round(scores, 4)}  mean={np.mean(scores):.4f}", flush=True)
    cvdf = pd.DataFrame(cv).sort_values("composite", ascending=False)
    win = cvdf.iloc[0]
    S["trials"], S["cv"] = trials, cvdf
    # refit the winning config (so the fitted model matches the chosen row exactly)
    m_tuned = MT.fit_xgb(win["params"], Xtr, ytr, Xva, yva)
    S["tuned_params"] = {**win["params"], "best_iteration": int(m_tuned.best_iteration)}

    print("\n=== Logistic Regression & HistGradientBoosting challenger ===", flush=True)
    lr_pipe, lr_res = MT.train_logistic(tr, ytr, va, yva, ())
    hgb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_depth=6, l2_regularization=1.0, random_state=L.RANDOM_SEED)
    hgb.fit(Xtr.toarray().astype(np.float32), ytr)
    S["lr_results"] = lr_res; S["front"] = front; S["lr_pipe"] = lr_pipe; S["hgb"] = hgb
    S["m_default"], S["m_tuned"] = m_def, m_tuned
    pv = {"LogisticRegression": lr_pipe.predict_proba(va)[:, 1], "XGBoost (baseline config, eligible data)": m_def.predict_proba(Xva)[:, 1],
          "XGBoost (tuned)": m_tuned.predict_proba(Xva)[:, 1], "HistGradientBoosting (challenger)": hgb.predict_proba(Xva.toarray().astype(np.float32))[:, 1]}
    S["val_probs"] = pv
    for k, v in pv.items():
        print(f"  {k}: val AUC={MT.quick_scores(yva, v)['roc_auc']:.4f}  Brier={MT.quick_scores(yva, v)['brier']:.4f}", flush=True)
    return S

def ceiling_analysis(tr, te, out_dir):
    """What is the best any order-time model could do on this data? Same Day cut-off rule is exploited perfectly, First Class is always late,
    and Second/Standard Class are scored with their TRAINING late rates (their outcome is unrelated to every feature: see Standard Class report)."""
    from sklearn.metrics import roc_auc_score
    rate = tr.groupby("Shipping Mode")["_y"].mean(); y = te["_y"].values
    p = te["Shipping Mode"].map(rate).astype(float).values.copy()
    sd = (te["Shipping Mode"] == "Same Day").values; p[sd] = np.where(te["_t"].dt.hour.values[sd] >= 12, 0.99, 0.01)
    only_mode = te["Shipping Mode"].map(rate).astype(float).values
    n = len(y); late = y.sum(); std = (te["Shipping Mode"] == "Standard Class").values
    rows = [("mode base rate only", roc_auc_score(y, only_mode)), ("mode rate + perfect Same Day hour rule (ceiling for order-time features)", roc_auc_score(y, p))]
    # recall/precision reachable if Standard Class is alerted or not
    late_std, late_other = y[std].sum(), y[~std].sum()
    lines = ["PERFORMANCE CEILING ANALYSIS (test period, eligible rows)", "=" * 70, *[f"  AUC {a:.4f}  <- {b}" for b, a in [(r[0], r[1]) for r in rows]],
             "", f"Late shipments in test: {int(late):,}.  Standard Class: {int(late_std):,} ({late_std / late:.1%}) at a late rate of {y[std].mean():.3f}; all other modes: {int(late_other):,}.",
             f"Alerting ONLY non-Standard modes:  recall <= {late_other / late:.3f}, precision ~ {y[~std].mean():.3f}, alerts {(~std).mean():.1%} of shipments.",
             f"Alerting everything:                recall = 1.000, precision = {y.mean():.3f}, alerts 100%.",
             f"Any extra Standard Class alert adds shipments that are late only {y[std].mean():.1%} of the time (no feature can tell which ones).",
             "", "Therefore: recall 85-90% together with precision 75-85% is NOT reachable with the data columns available at order creation;",
             "reaching recall 0.85 requires alerting a large share of Standard Class shipments, which pushes precision towards ~0.62 (see threshold operating points).",
             "More signal would need NEW information (carrier, warehouse/dispatch events, weather, congestion) - not present in DataCo."]
    open(f"{out_dir}/performance_ceiling_analysis.txt", "w").write("\n".join(lines)); print("\n".join(lines))
    return dict(rows)

OUT = os.path.join(L.REPORTS, "improvement"); VOUT = os.path.join(L.VIZ, "improvement")

def to_records(df, extra=()):
    out = []
    for _, r in df.iterrows():
        d = {c: (r[c].item() if hasattr(r[c], "item") else r[c]) for c in FE.BASE_RAW_FIELDS + list(extra)}
        d[FE.RAW_DATE] = r[FE.RAW_DATE].strftime("%m/%d/%Y %H:%M"); out.append(d)
    return out

def operating_points(y, p, base_thr):
    """Named operating points on VALIDATION data (the trade-off the business can choose from)."""
    t = ME.threshold_table(y, p); t["fnr"] = t.FN / (t.FN + t.TP)
    pick = lambda mask, key, asc: (t[mask].sort_values(key, ascending=asc).iloc[0] if mask.any() else None)
    rows = [("max F1", t.sort_values("f1", ascending=False).iloc[0]),
            ("recall >= 0.85 (highest precision)", pick(t.recall >= 0.85, "precision", False)),
            ("recall >= 0.90 (highest precision)", pick(t.recall >= 0.90, "precision", False)),
            ("precision >= 0.75 (highest recall)", pick(t.precision >= 0.75, "recall", False)),
            ("precision >= 0.85 (highest recall)", pick(t.precision >= 0.85, "recall", False)),
            ("baseline threshold 0.40", t[np.isclose(t.threshold, base_thr)].iloc[0])]
    return pd.DataFrame([{"operating_point": n, **{k: r[k] for k in ["threshold", "precision", "recall", "f1", "flagged_fraction", "FN", "FP"]}} if r is not None
                         else {"operating_point": n + "  -> NOT ACHIEVABLE on validation"} for n, r in rows])

def threshold_grid(y, p):
    g = ME.threshold_table(y, p, grid=np.round(np.arange(0.20, 0.601, 0.05), 2))
    g["false_positive_rate"] = g.FP / (g.FP + g.TN); g["false_negative_rate"] = g.FN / (g.FN + g.TP)
    g["predicted_late_shipments"] = g.TP + g.FP; g["missed_late_shipments"] = g.FN; g["alert_percentage"] = g.flagged_fraction * 100
    return g[["threshold", "precision", "recall", "f1", "false_positive_rate", "false_negative_rate", "predicted_late_shipments", "missed_late_shipments", "alert_percentage", "TP", "FP", "FN", "TN"]]

def cost_sensitivity(y, p):
    rows = []
    for ratio in (1, 2, 3, 5):
        for cap in (0.5, 0.6, 0.7, 0.8, 1.0):
            thr, tab, _ = ME.select_threshold(ME.threshold_table(y, p), float(ratio), 1.0, cap)
            r = tab[np.isclose(tab.threshold, thr)].iloc[0]
            rows.append({"cost_fn_to_fp_ratio": ratio, "alert_capacity": cap, "threshold": thr, "precision": r.precision, "recall": r.recall, "alert_fraction": r.flagged_fraction})
    return pd.DataFrame(rows)

def finalize(S, raw, df, tr, va, te):
    import joblib
    from sklearn.pipeline import Pipeline
    import model_calibration as MC, backtesting as BT, error_analysis as EA, shap_explainability as SX, model_saving as MS
    import model_registry as MR, monitoring as MON, inference_benchmark as IB, prediction as PR
    os.makedirs(OUT, exist_ok=True); os.makedirs(VOUT, exist_ok=True)
    ytr, yva, yte = tr["_y"].values, va["_y"].values, te["_y"].values
    front = S["front"]
    pipes = {"XGBoost (baseline config, eligible data)": Pipeline([("front", front), ("model", S["m_default"])]),
             "XGBoost (tuned)": Pipeline([("front", front), ("model", S["m_tuned"])]), "LogisticRegression": S["lr_pipe"]}
    pv = S["val_probs"]
    # ---------- model selection (VALIDATION only). XGBoost stays primary; challengers must win by >= 0.005 AUC to even be recommended.
    xs = {k: MT.quick_scores(yva, pv[k]) for k in ["XGBoost (baseline config, eligible data)", "XGBoost (tuned)"]}
    tuned_ok = xs["XGBoost (tuned)"]["roc_auc"] > xs["XGBoost (baseline config, eligible data)"]["roc_auc"] + 0.001 or \
        (abs(xs["XGBoost (tuned)"]["roc_auc"] - xs["XGBoost (baseline config, eligible data)"]["roc_auc"]) <= 0.001 and xs["XGBoost (tuned)"]["brier"] < xs["XGBoost (baseline config, eligible data)"]["brier"])
    sel = "XGBoost (tuned)" if tuned_ok else "XGBoost (baseline config, eligible data)"
    sel_model = S["m_tuned"] if tuned_ok else S["m_default"]
    sel_params = S["tuned_params"] if tuned_ok else {"note": "library defaults", "best_iteration": int(S["m_default"].best_iteration)}
    comp = pd.DataFrame([{"model": k, **MT.quick_scores(yva, v)} for k, v in pv.items()]).sort_values("roc_auc", ascending=False)
    best_other = comp[~comp.model.str.startswith("XGBoost")].iloc[0]
    challenger_note = (f"{best_other.model} (val AUC {best_other.roc_auc:.4f}) vs selected XGBoost ({xs[sel]['roc_auc']:.4f}): "
                       + ("exceeds +0.005 -> recommend investigation, NOT auto-adopted" if best_other.roc_auc >= xs[sel]["roc_auc"] + 0.005 else "no meaningful advantage; XGBoost kept"))
    print("SELECTED:", sel, "|", challenger_note, flush=True)
    comp.to_csv(f"{OUT}/model_comparison_validation.csv", index=False)
    pipe = pipes[sel]; p_va_raw = pv[sel]
    # ---------- calibration (validation only)
    order = np.argsort(va["_t"].values, kind="stable")
    cal, cal_tab, method = MC.choose_calibration(p_va_raw[order], yva[order]); cal_tab.to_csv(f"{OUT}/calibration_comparison.csv", index=False)
    p_va = cal.transform(p_va_raw)
    # ---------- thresholds (validation only)
    grid = threshold_grid(yva, p_va); grid.to_csv(f"{OUT}/threshold_grid_validation.csv", index=False)
    ops = operating_points(yva, p_va, 0.40); ops.to_csv(f"{OUT}/threshold_operating_points_validation.csv", index=False)
    cost = cost_sensitivity(yva, p_va); cost.to_csv(f"{OUT}/business_cost_sensitivity_validation.csv", index=False)
    thr, fine, why = ME.select_threshold(ME.threshold_table(yva, p_va), RISK_CONFIG["cost_fn"], RISK_CONFIG["cost_fp"], RISK_CONFIG["max_flagged_fraction"])
    fine.to_csv(f"{OUT}/threshold_selection_fine_validation.csv", index=False)
    medium = RISK_CONFIG["medium_cut"] if RISK_CONFIG["medium_cut"] < thr else round(thr * 0.75, 2)
    cut = {"medium": medium, "high": thr}
    print("threshold", thr, why, "\n", ops.round(4).to_string(index=False), flush=True)
    # ---------- TEST: scored once, after model/threshold/calibration are fixed
    p_te_raw = pipe.predict_proba(te)[:, 1]; p_te = cal.transform(p_te_raw)
    t_raw, _, _ = ME.select_threshold(ME.threshold_table(yva, p_va_raw), RISK_CONFIG["cost_fn"], RISK_CONFIG["cost_fp"], RISK_CONFIG["max_flagged_fraction"])
    champ = joblib.load(f"{L.MODELS}/order_creation/versions/v1.0.0/best_model.joblib")
    base_all = df[df["_split"] == "test"].reset_index(drop=True)
    pb_all = champ["calibrator"].transform(champ["pipeline"].predict_proba(base_all)[:, 1]); pb_el = champ["calibrator"].transform(champ["pipeline"].predict_proba(te)[:, 1])
    rows = [("1a Existing baseline v1.0.0 - ALL test rows (as originally reported)", ME.compute_metrics(base_all["_y"].values, pb_all, champ["threshold"])),
            ("1b Existing baseline v1.0.0 - eligible test rows", ME.compute_metrics(yte, pb_el, champ["threshold"])),
            ("2 Optimized XGBoost, uncalibrated (own validation threshold)", ME.compute_metrics(yte, p_te_raw, t_raw)),
            ("3 Calibrated optimized XGBoost @ baseline threshold 0.40", ME.compute_metrics(yte, p_te, 0.40)),
            ("4 FINAL selected: calibrated + validated operating threshold", ME.compute_metrics(yte, p_te, thr))]
    final = pd.DataFrame([{"model": n, **m} for n, m in rows]); final["alert_percentage"] = final.flagged_fraction * 100
    print(final[["model", "threshold", "precision", "recall", "f1", "roc_auc", "pr_auc", "brier", "FN", "FP", "alert_percentage"]].round(4).to_string(index=False), flush=True)
    mt = rows[-1][1]; mv = ME.compute_metrics(yva, p_va, thr)
    # reporting-only: other algorithms on test (never used for selection)
    rep = []
    for k in ["LogisticRegression", "XGBoost (baseline config, eligible data)", "XGBoost (tuned)"]:
        pk = pipes[k].predict_proba(te)[:, 1]; rep.append({"model": k, **{f"test_{a}": b for a, b in ME.compute_metrics(yte, pk, 0.40).items() if a in ["precision", "recall", "f1", "roc_auc", "pr_auc", "brier"]}})
    pd.DataFrame(rep).to_csv(f"{OUT}/other_models_test_reporting_only.csv", index=False)
    # ---------- plots + calibration reliability + risk buckets
    ME.plot_confusion(yte, p_te, thr, f"{VOUT}/confusion_matrix.png", f"Final model - test (threshold {thr:.2f})")
    ME.plot_curves({"Test": {"v1.0.0 baseline (eligible rows)": (yte, pb_el), "Optimized (calibrated)": (yte, p_te)}},
                   f"{VOUT}/roc_curve.png",
                   f"{VOUT}/precision_recall_curve.png")
    ME.plot_calibration({"Validation": {"before": (yva, p_va_raw), "after": (yva, p_va)}, "Test": {"before": (yte, p_te_raw), "after": (yte, p_te)}},
                        f"{VOUT}/calibration_curve.png")
    bk = ME.risk_bucket_report(yte, p_te, medium, thr); bk.to_csv(f"{OUT}/risk_bucket_reliability_test.csv", index=False)
    # ---------- subgroup / unseen / Standard Class
    sub = EA.all_subgroups(te, tr, yte, p_te, thr); sub.to_csv(f"{OUT}/subgroup_performance_test.csv", index=False)
    uns = EA.unseen_report(te, tr, yte, p_te, thr); uns.to_csv(f"{OUT}/unseen_category_performance_test.csv", index=False)
    sc = EA.standard_class_investigation(tr, va, te, yte, p_te, thr, {k: v for k, v in S["tuned_params"].items() if k in PARAM_KEYS}, S["tuned_params"]["best_iteration"], OUT)
    fp = EA.fn_fp_reports(te, yte, p_te, thr, pipe, OUT)
    # ---------- backtests (train+validation period only)
    pre = pd.concat([tr, va]); bnd = [pd.Timestamp(x) for x in ["2016-01-01", "2016-04-01", "2016-07-01", "2016-10-01", "2017-01-01", "2017-04-01"]]
    bt1 = BT.expanding_backtest(pre, {k: v for k, v in (S["tuned_params"] if tuned_ok else {}).items() if k in PARAM_KEYS}, (S["tuned_params"]["best_iteration"] if tuned_ok else int(S["m_default"].best_iteration)), thr, bnd)
    bt1.insert(0, "model", sel); bt1.to_csv(f"{OUT}/backtest_results.csv", index=False); print(bt1[["fold", "eval_window", "precision", "recall", "f1", "roc_auc", "pr_auc"]].round(4).to_string(index=False), flush=True)
    # ---------- SHAP (selected XGBoost)
    sample = te.sample(2000, random_state=L.RANDOM_SEED)
    imp = SX.global_importance(pipe, sample, OUT, VOUT); err, ok_shap = SX.check_additivity(pipe, sample.head(300))
    # ---------- save CANDIDATE (production/current files untouched)
    num_raw = ["Days for shipment (scheduled)", "Order Item Product Price", "Order Item Quantity", "Order Item Discount Rate", "Sales"]
    schema = {"stage": "order_creation", "target": L.TARGET, "required_raw_fields": FE.BASE_RAW_FIELDS, "numeric_raw_fields": num_raw, "date_field": FE.RAW_DATE,
              "model_input_numeric": FE.feature_lists()[0], "model_input_categorical": FE.feature_lists()[1], "identifier_keys_allowed_but_ignored": list(PR.ID_KEYS),
              "prohibited_inputs": [c for c, _, _ in L.PROHIBITED]}
    meta = {"algorithm": "XGBoost", "selected_model_label": sel, "target_column": L.TARGET, "target_definition_version": TV.TARGET_VERSION,
            "target_definition": "1 = late (real days > scheduled days); trained/evaluated on ON_TIME+LATE rows only (cancelled/fraud excluded)",
            "training_rows": int(len(tr)), "validation_rows": int(len(va)), "test_rows": int(len(te)), "dataset_file": os.path.basename(L.RAW_CSV),
            "dataset_sha256": MS.file_fingerprint(L.RAW_CSV), "dataset_rows": int(len(raw)), "random_seed": L.RANDOM_SEED, "feature_names_raw": FE.BASE_RAW_FIELDS,
            "decision_threshold": thr, "risk_cutoffs": cut, "risk_config_assumptions": RISK_CONFIG, "calibration_method": method, "selected_model_params": sel_params,
            "validation_metrics": mv, "test_metrics": mt, "historical_features": "evaluated, NOT adopted (see improve_feature_ablation.csv)",
            "challenger_algorithm_note": challenger_note, "limitations": ["Cancelled/fraud orders are out of scope for this model (not scored as late/on-time)",
            "Latitude/Longitude, order city/state and historical-rate features were evaluated and not adopted", "No carrier/warehouse data exists in DataCo"]}
    version, vdir = MS.save_stage_model("order_creation", {"pipeline": pipe, "calibrator": cal, "threshold": thr, "risk_cutoffs": cut}, meta, schema, L.MODELS, "2.0.0", set_current=False)
    # ---------- registry + champion-challenger (NO promotion)
    if MR.get("order_creation", "1.0.0", L.MODELS) is None:
        MR.register("order_creation", "1.0.0", L.MODELS, role="production", approval_status="BASELINE_PRE_REGISTRY (human approval not recorded)")
    MR.register("order_creation", version, L.MODELS, role="candidate", approval_status="PENDING_APPROVAL")
    cand = joblib.load(f"{vdir}/best_model.joblib")
    cc = MR.champion_challenger(champ, cand, va, yva); MR.attach_acceptance("order_creation", version, L.MODELS, cc)
    json.dump(cc, open(f"{OUT}/champion_challenger_report.json", "w"), indent=2, default=str)
    print("champion-challenger passed:", cc["passed"], cc["checks"], flush=True)
    # ---------- monitoring replay (held-out period, NOT live traffic) + benchmark
    dbp = f"{OUT}/monitoring_demo.sqlite"
    if os.path.exists(dbp): os.remove(dbp)
    store = MON.MonitoringStore(dbp); samp = te.sample(1500, random_state=1); recs = to_records(samp)
    for r, (_, row) in zip(recs, samp.iterrows()):
        sid = f"SHP{int(row['Order Item Id'])}"; res = PR.predict_order_creation_api(r, shipment_id=sid, store=store, models_dir=L.MODELS, explain=False, version=version)
        sched = row["_t"] + pd.Timedelta(days=int(row["Days for shipment (scheduled)"])); act = row["_t"] + pd.Timedelta(days=float(row["Days for shipping (real)"]))
        store.record_outcome(sid, sched, act)
    # snapshot of the features used for grouping in performance report
    perf = store.performance(); perf.to_csv(f"{OUT}/monitoring_performance_replay.csv", index=False)
    num, cat = FE.feature_lists(); fe_tr, fe_te = FE.engineer_order_features(tr), FE.engineer_order_features(te)
    drift = MON.drift_report(fe_tr, fe_te, num, cat, ref_pred=cal.transform(pipe.predict_proba(va)[:, 1]), live_pred=p_te)
    drift.to_csv(f"{OUT}/drift_report_replay.csv", index=False)
    bench_recs = to_records(te.head(300))
    bench = {"champion_v1.0.0": IB.benchmark(bench_recs, L.MODELS, version="1.0.0"), "candidate_v2.0.0": IB.benchmark(bench_recs, L.MODELS, version=version)}
    json.dump(bench, open(f"{OUT}/inference_benchmark.json", "w"), indent=2, default=str)
    final.to_csv(f"{OUT}/final_model_comparison_test.csv", index=False)
    json.dump({"selected": sel, "version": version, "threshold": thr, "threshold_reason": why, "risk_cutoffs": cut, "calibration": method, "standard_class": sc,
               "fn": fp["FN"]["count"], "fp": fp["FP"]["count"], "shap_additivity_error": err, "shap_ok": bool(ok_shap), "challenger_note": challenger_note,
               "acceptance_passed": cc["passed"], "monotonic_buckets": bool(bk.observed_late_rate.is_monotonic_increasing), "top_shap": imp.feature.head(6).tolist()},
              open(f"{OUT}/improvement_summary.json", "w"), indent=2, default=str)
    return final, cc, bench

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    raw, df = build_data()
    summ, a_all, a_el = TV.target_report(raw, df["_outcome"], L.REPORTS)
    print(summ.to_string(index=False)); print("label agreement all/eligible:", a_all, a_el)
    el = df[df["_outcome"].isin(["ON_TIME", "LATE"])]
    tr, va, te = (el[el["_split"] == s].reset_index(drop=True) for s in ["train", "val", "test"])
    print({k: len(v) for k, v in zip(["train", "val", "test"], [tr, va, te])}, "late rates", [round(x._y.mean(), 4) for x in (tr, va, te)])
    tr, va, te, keys = add_history(tr, va, te)
    print("history columns:", [c for c in tr.columns if c.startswith("hist_")][:6], "...")
    if stage in ("all", "ablation"):
        print("\n=== Ablation on VALIDATION (default XGBoost, eligible rows) ===")
        ab = ablation(tr, va, tr["_y"].values, va["_y"].values, keys)
        ab.to_csv(f"{L.REPORTS}/improve_feature_ablation.csv", index=False)
    if stage in ("all", "optimise"):
        import joblib
        S = optimise(tr, va)
        joblib.dump(S, "/tmp/improve_state.joblib")
        print("state saved")
    if stage == "ceiling":
        os.makedirs(OUT, exist_ok=True); ceiling_analysis(tr, te, OUT)
    if stage in ("finalize",):
        import joblib
        S = joblib.load("/tmp/improve_state.joblib")
        finalize(S, raw, df, tr, va, te)
