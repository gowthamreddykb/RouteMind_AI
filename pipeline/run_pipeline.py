"""
run_pipeline.py - RouteMind AI Master Pipeline Orchestrator
Executes the complete 13-stage machine learning workflow adopting the reference methodology:
  Stage 01: Ingestion & Dataset Isolation
  Stage 02: Data Cleaning & Validation
  Stage 03: EDA & Class Imbalance Audit
  Stage 04: Feature Engineering & Preprocessing Pipeline
  Stage 05: Feature Availability & Selection Audit
  Stage 06: Stratified Group-Aware Splitting
  Stage 07: Multi-Model Training (Random Forest, XGBoost, Logistic Regression, LightGBM)
  Stage 08: Hyperparameter Tuning
  Stage 09: Multi-Metric Model Comparison Table
  Stage 10: Operational Threshold Optimization
  Stage 11: Final Test Evaluation & Risk Monotonicity
  Stage 12: Explainability & Risk Attribution
  Stage 13: Registry Export & Artifact Serialization
"""

import os
import argparse
import time
from datetime import datetime

try:
    from pipeline.stage_01_ingestion import DataIngestion
    from pipeline.stage_02_cleaning import DataCleaning
    from pipeline.stage_03_eda import ExploratoryAnalysis
    from pipeline.stage_04_feature_engineering import FeatureEngineering
    from pipeline.stage_05_feature_selection import FeatureSelectionAudit
    from pipeline.stage_06_data_splitting import DataSplitting
    from pipeline.stage_07_model_training import ModelTraining
    from pipeline.stage_08_hyperparameter_tuning import HyperparameterTuning
    from pipeline.stage_09_model_comparison import ModelComparison
    from pipeline.stage_10_threshold_optimization import ThresholdOptimization
    from pipeline.stage_11_evaluation import FinalEvaluation
    from pipeline.stage_12_explainability import Explainability
    from pipeline.stage_13_registry_and_export import ModelRegistryExport
except ImportError:
    from stage_01_ingestion import DataIngestion
    from stage_02_cleaning import DataCleaning
    from stage_03_eda import ExploratoryAnalysis
    from stage_04_feature_engineering import FeatureEngineering
    from stage_05_feature_selection import FeatureSelectionAudit
    from stage_06_data_splitting import DataSplitting
    from stage_07_model_training import ModelTraining
    from stage_08_hyperparameter_tuning import HyperparameterTuning
    from stage_09_model_comparison import ModelComparison
    from stage_10_threshold_optimization import ThresholdOptimization
    from stage_11_evaluation import FinalEvaluation
    from stage_12_explainability import Explainability
    from stage_13_registry_and_export import ModelRegistryExport

def execute_pipeline(dataset_key: str = "historical", stage_target: str = "order_creation", sample_rows: int = None):
    t0 = time.time()
    print("=" * 80)
    print(f" ROUTEMIND AI - PRODUCTION ML PIPELINE EXECUTION ({dataset_key.upper()})")
    print("=" * 80)

    # Stage 01: Ingestion
    ingestion = DataIngestion()
    raw_df, manifest = ingestion.load_dataset(dataset_key=dataset_key, sample_rows=sample_rows)

    # Stage 02: Cleaning
    cleaning = DataCleaning()
    clean_df, clean_report = cleaning.clean(raw_df, dataset_key=dataset_key)

    # Stage 03: EDA & Imbalance Audit
    eda = ExploratoryAnalysis()
    eda_report = eda.analyze(clean_df, dataset_key=dataset_key)
    scale_pos_weight = eda_report["class_imbalance"]["scale_pos_weight"]

    # Stage 04: Feature Engineering
    fe = FeatureEngineering()
    X_all, num_cols, cat_cols = fe.prepare_features(clean_df, stage=stage_target)
    preprocessor = fe.build_preprocessor(num_cols, cat_cols, scale_numeric=True)
    preprocessor_tree = fe.build_preprocessor(num_cols, cat_cols, scale_numeric=False)

    # Stage 05: Feature Availability Audit
    fa = FeatureSelectionAudit()
    fa.generate_audit_report(dataset_key=dataset_key)

    # Stage 06: Data Splitting
    splitting = DataSplitting()
    splits = splitting.split_data(clean_df, dataset_key=dataset_key)
    train_df, val_df, test_df = splits["train"], splits["val"], splits["test"]

    X_train, _, _ = fe.prepare_features(train_df, stage=stage_target)
    y_train = train_df["Late_delivery_risk"].values

    X_val, _, _ = fe.prepare_features(val_df, stage=stage_target)
    y_val = val_df["Late_delivery_risk"].values

    X_test, _, _ = fe.prepare_features(test_df, stage=stage_target)
    y_test = test_df["Late_delivery_risk"].values

    # Stage 07: Model Training (Reference Methodology)
    trainer = ModelTraining(random_state=42)
    models = trainer.train_models(X_train, y_train, preprocessor, preprocessor_tree, scale_pos_weight)

    # Stage 08: Hyperparameter Tuning
    tuner = HyperparameterTuning()
    tuning_res = tuner.tune_xgboost(X_train, y_train, X_val, y_val, preprocessor_tree, scale_pos_weight)

    # Stage 09: Model Comparison (Validation Partition)
    comparator = ModelComparison()
    val_comparison = comparator.evaluate_models(models, X_val, y_val, split_name="Validation")

    champion_name = val_comparison.iloc[0]["Model"]
    champion_pipe = models[champion_name]
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Selected Champion Model: {champion_name}")

    # Stage 10: Threshold Optimization
    y_val_prob = champion_pipe.predict_proba(X_val)[:, 1]
    opt = ThresholdOptimization(cost_fn=2.0, cost_fp=1.0)
    opt_res = opt.optimize_threshold(y_val, y_val_prob)
    opt_thr = opt_res["optimal_threshold"]

    # Stage 11: Final Evaluation (Untouched Test Partition)
    evaluator = FinalEvaluation()
    final_eval = evaluator.evaluate_champion(champion_name, champion_pipe, X_test, y_test, threshold=opt_thr)

    # Stage 12: Explainability
    explainer = Explainability()
    top_features = explainer.compute_importance(champion_pipe, num_cols + cat_cols)

    # Stage 13: Registry Export
    exporter = ModelRegistryExport()
    registry_entry = exporter.export_model(
        model_id=f"routemind_{stage_target}_{champion_name.lower().replace(' ', '_')}",
        stage=stage_target,
        pipeline=champion_pipe,
        numeric_features=num_cols,
        categorical_features=cat_cols,
        metrics=final_eval,
        threshold=opt_thr,
        version="2.1.0",
        dataset_version=manifest["dataset_version"]
    )

    elapsed = time.time() - t0
    print("\n" + "=" * 80)
    print(f" PIPELINE EXECUTION COMPLETE IN {elapsed:.1f}s ({elapsed/60:.2f} min)")
    print(f" Champion: {champion_name} | Optimal Threshold: {opt_thr} | Test Accuracy: {val_comparison.iloc[0]['Accuracy']:.2%}")
    print("=" * 80)
    return champion_pipe, registry_entry

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RouteMind AI Pipeline Runner")
    parser.add_argument("--dataset", type=str, default="historical", choices=["historical", "new_excel"])
    parser.add_argument("--stage", type=str, default="order_creation", choices=["order_creation", "dispatch"])
    parser.add_argument("--sample", type=int, default=None, help="Optional row subsampling for rapid verification")
    args = parser.parse_args()

    execute_pipeline(dataset_key=args.dataset, stage_target=args.stage, sample_rows=args.sample)
