"""final_report.py - writes reports/improvement/final_improvement_report.txt from the ACTUAL result files (no hand-typed metrics)."""
import json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from load_data import REPORTS, MODELS
OUT = os.path.join(REPORTS, "improvement")

STATUS = [  # (checkpoint, status, evidence)
 ("1.1-1.3 Audit, workflow, preserve baseline", "PASS", "ml_project_audit_*.csv/txt; baseline backed up; baseline artifact hash test passes"),
 ("2.1 Target definition", "PASS (duration-based) / BLOCKED (timestamp-based)", "target_definition_report.txt; DataCo has no delivery timestamps or time zones"),
 ("2.2 Data quality", "PASS", "data_cleaning_summary.csv, data_quality_report.txt"),
 ("2.3 Provenance", "PASS", "feature_provenance_matrix.csv, prediction_stage_availability_report.csv"),
 ("3.1 Order-creation leakage", "PASS", "leakage tests; leakage_audit_report.csv"),
 ("3.2 Dispatch", "BLOCKED - model NOT_TRAINED", "models/dispatch/dispatch_requirements.json"),
 ("3.3 Leakage tests", "PASS", "tests/test_leakage.py, test_historical_features.py, test_data_splitting.py, test_preprocessing.py"),
 ("4.1 Feature engineering", "PASS", "improve_feature_ablation.csv: history features evaluated, none reached +0.002 AUC, not adopted; carrier history BLOCKED (no carrier column)"),
 ("5.1 Split", "PASS", "same group-aware chronological split; no Order Id overlap"),
 ("5.2 Backtests", "PASS", "backtest_results.csv (5 expanding folds, test period untouched)"),
 ("6.1-6.3 Models, tuning, imbalance", "PASS", "model_comparison_validation.csv, hyperparameter_trials.csv, time_aware_cv_top3.csv, class_imbalance_experiment.csv"),
 ("7.1-7.2 Threshold + business cost", "PASS", "threshold_grid_validation.csv, threshold_operating_points_validation.csv, business_cost_sensitivity_validation.csv"),
 ("7.3 Experimental targets", "NOT MET (reported honestly)", "performance_ceiling_analysis.txt shows targets unreachable with order-time data"),
 ("8.1-8.3 Subgroups, Standard Class, unseen", "PASS", "subgroup_performance_test.csv, standard_class_investigation.txt, unseen_category_performance_test.csv"),
 ("9.1-9.2 Calibration", "PASS", "calibration_comparison.csv; method 'none' chosen by rule; probabilities tested in [0,1]"),
 ("10.1-10.3 SHAP, FN, FP", "PASS", "shap_feature_importance.csv, false_negative_report.csv, false_positive_report.csv (+ _patterns)"),
 ("11 Registry", "PASS", "models/registry.json; candidate/production/previous roles; rollback tested"),
 ("12.1-12.3 Inference API + performance", "PASS", "prediction.py, flask_example.py, inference_benchmark.json (1-CPU sandbox numbers)"),
 ("13.1-13.3 Monitoring", "PASS (replay on held-out data, not live traffic)", "monitoring.py, drift_report_replay.csv, monitoring_performance_replay.csv"),
 ("14.1 Champion-challenger", "PASS", "champion_challenger_report.json; candidate NOT promoted"),
 ("14.2 Retraining", "PARTIAL", "improve.py re-runnable on a new CSV and registers a CANDIDATE; no ingestion from live MySQL data yet"),
 ("15 Automated tests", "PASS", "see test_results.txt"),
]

def main():
    f = pd.read_csv(f"{OUT}/final_model_comparison_test.csv"); s = json.load(open(f"{OUT}/improvement_summary.json"))
    cc = json.load(open(f"{OUT}/champion_challenger_report.json")); bench = json.load(open(f"{OUT}/inference_benchmark.json"))
    ops = pd.read_csv(f"{OUT}/threshold_operating_points_validation.csv"); bt = pd.read_csv(f"{OUT}/backtest_results.csv")
    L = ["FINAL IMPROVEMENT REPORT - RouteMind AI order-creation model", "=" * 78,
         f"Candidate: v{s['version']} ({s['selected']}), threshold {s['threshold']}, calibration '{s['calibration']}', status: CANDIDATE - NOT promoted (needs human approval).",
         "Dispatch model: BLOCKED (NOT_TRAINED).  The two-stage system is NOT complete.", "",
         "FINAL TEST COMPARISON (same untouched test period; rows 1b-4 use eligible deliveries only)",
         f[["model", "threshold", "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "brier", "log_loss", "FP", "FN", "TN", "TP", "alert_percentage"]].round(4).to_string(index=False), "",
         "READ THIS: ROC-AUC improved by only ~0.003. The recall gain comes from alerting more Standard Class shipments (late ~40% of the time), not better discrimination.", "",
         "VALIDATION OPERATING POINTS (what the business can choose between)", ops.round(4).to_string(index=False), "",
         "BACKTESTS (train+validation period only)", bt[["fold", "eval_window", "precision", "recall", "f1", "roc_auc", "pr_auc", "false_negative_rate", "false_positive_rate"]].round(4).to_string(index=False), "",
         f"Standard Class: in-class AUC final={s['standard_class']['auc_inside_standard_final']:.3f}, dedicated model={s['standard_class']['auc_inside_standard_dedicated']:.3f}; {s['fn']:,} false negatives (all Standard Class).",
         f"SHAP additivity error {s['shap_additivity_error']:.2e} (verified); risk buckets monotonic on test: {s['monotonic_buckets']}.", f"Challenger algorithm: {s['challenger_note']}", "",
         "CHAMPION-CHALLENGER (validation rows): passed=%s" % cc["passed"], *[f"  {k}: {v}" for k, v in cc["checks"].items()], "",
         "INFERENCE BENCHMARK (this sandbox, 1 CPU - re-measure on the target server)"]
    for k, v in bench.items():
        L.append(f"  {k}: single p50/p95 no-SHAP {v['single_no_shap']['p50_ms']:.1f}/{v['single_no_shap']['p95_ms']:.1f} ms; with SHAP {v['single_with_shap']['p50_ms']:.1f}/{v['single_with_shap']['p95_ms']:.1f} ms; "
                 f"batch1000 {v['batch1000_no_shap']['throughput_per_s']:.0f}/s (no SHAP), {v['batch1000_with_shap']['throughput_per_s']:.0f}/s (SHAP); load {v['model_load_ms']:.0f} ms")
    L += ["", "ASSUMPTIONS TO REPLACE WITH REAL BUSINESS VALUES: false-negative cost 3x false-positive cost; alert capacity 70% of shipments (src/improve.py RISK_CONFIG).", "",
          "CHECKPOINT STATUS", pd.DataFrame(STATUS, columns=["checkpoint", "status", "evidence"]).to_string(index=False)]
    open(f"{OUT}/final_improvement_report.txt", "w").write("\n".join(L)); print("\n".join(L[:22]))

if __name__ == "__main__":
    main()
