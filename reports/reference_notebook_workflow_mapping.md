# Reference Notebook Workflow Mapping Document

## 1. Reference Notebook Profile
- **Source Artifact**: `final random forest (1).ipynb`
- **Original Domain**: Network Security / Brute Force Attack Detection
- **Original Dataset**: `SentinelOps_bruteforce_1min_1k_to_10k.csv` (Target: `attack_type` in {Benign: 0, Brute Force: 1})
- **RouteMind Target Domain**: Supply Chain Logistics Operations (Target: `Late_delivery_risk` in {0: On-Time, 1: Late})
- **Methodology Goal**: Extract the complete training, preprocessing, multi-model comparison, live event streaming, and operational evaluation methodology and map it directly into RouteMind AI without domain corruption.

---

## 2. Cell-by-Cell Workflow Mapping Matrix

| Notebook Cell | Methodological Stage | Reference Notebook Code / Concept | RouteMind AI Production Implementation | Implementation File |
|---|---|---|---|---|
| **Cell 0** | Ingestion & Cleaning | `pd.read_csv()`, `to_datetime()`, `drop_duplicates()`, shape check | Ingests CSV/Excel independently, computes SHA256 checksums, validates date timestamps, removes duplicates | `pipeline/stage_01_ingestion.py`, `pipeline/stage_02_cleaning.py` |
| **Cell 1** | Target Mapping & Splitting | Binary mapping (`y = df[TARGET].map(...)`), column dropping, `train_test_split(..., stratify=y, test_size=0.30)` | Target integrity check, leakage column stripping, Order Id group-aware stratified train/val/test split | `pipeline/stage_04_feature_engineering.py`, `pipeline/stage_06_data_splitting.py` |
| **Cell 2** | Preprocessing & Random Forest | `ColumnTransformer` with `SimpleImputer(strategy='median')` for numeric + `Pipeline([('imputer', SimpleImputer(strategy='most_frequent')), ('encoder', OneHotEncoder(handle_unknown='ignore'))])` for categorical; `RandomForestClassifier(n_estimators=200, max_depth=5, class_weight='balanced')` | Replicates the identical ColumnTransformer architecture and Random Forest Classifier with balanced class weights for logistics features | `pipeline/stage_04_feature_engineering.py`, `pipeline/stage_07_model_training.py` |
| **Cell 3** | Evaluation Metrics | `accuracy_score`, `precision_score`, `recall_score`, `f1_score`, `mean_squared_error` (Probability MSE), `classification_report`, `roc_auc_score` | Computes identical 6 metrics plus PR-AUC on validation and test partitions | `pipeline/stage_09_model_comparison.py`, `pipeline/stage_11_evaluation.py` |
| **Cell 4 - 5** | Activity Visualization & CM | Dual-axis temporal line plot & `ConfusionMatrixDisplay` | Confusion Matrix Display and operational risk bucket analysis | `pipeline/stage_11_evaluation.py`, `static/control_tower_dashboard.html` |
| **Cell 6** | Live Event Addition | `add_new_event()`: Interactive input, DataFrame appending, feature preparation, live prediction | `LiveEventManager.add_new_shipment_event()`: Ingests live shipment payload, appends to event buffer, evaluates dual-model probabilities | `pipeline/live_event_manager.py`, Flask `/predict/live-event` |
| **Cell 7 - 11** | Streaming Updates & Persistence | Dataset shape update, before vs after comparative plotting, saving updated CSV (`SentinelOps_bruteforce_updated.csv`) | Persists live shipment events to `data/live_shipment_events.csv` and SQLite/MySQL `shipment_events` table; activity summary API | `pipeline/live_event_manager.py`, `sql/db_adapter.py`, `/events/activity` |
| **Cell 12** | RF Confusion Matrix | `ConfusionMatrixDisplay(display_labels=['Benign', 'Brute Force'])` | Confusion Matrix Display on untouched Test partition for On-Time vs Late Delivery | `pipeline/stage_11_evaluation.py` |
| **Cell 13 - 15** | XGBoost with Imbalance Weighting | `scale_weight = negative_count / positive_count`, `XGBClassifier(scale_pos_weight=scale_weight, n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8)` | Dynamic computation of `scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()` and pipeline integration with early stopping | `pipeline/stage_03_eda.py`, `pipeline/stage_07_model_training.py` |
| **Cell 16 - 17** | XGBoost Evaluation | Predict test records, probability MSE, confusion matrix display with `cmap='Greens'` | XGBoost test metrics, probability MSE (Brier score), classification report, confusion matrix | `pipeline/stage_09_model_comparison.py`, `pipeline/stage_11_evaluation.py` |
| **Cell 18 - 19** | Model Comparison Table & Chart | Side-by-side DataFrame comparing RF vs XGBoost across Accuracy, Precision, Recall, F1, Probability MSE, ROC-AUC | Side-by-side benchmarking table comparing Random Forest, XGBoost, LightGBM, and Logistic Regression; exported to CSV & JSON | `pipeline/stage_09_model_comparison.py`, `reports/model_comparison_validation.csv` |
| **Cell 20** | Live Dual-Model Prediction | `rf_new_prediction`, `xgb_new_prediction`, probability outputs | Dual-model live inference: scores incoming shipment across both RF and XGBoost simultaneously, outputs consolidated alert level | `pipeline/live_event_manager.py`, `prediction_service.py` |
