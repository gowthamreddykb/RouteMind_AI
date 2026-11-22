# Existing Pretrained Model Inventory

## 1. Overview & Preservation Policy
Per mandatory critical constraints:
- Existing pretrained models are strictly preserved.
- No existing model files have been deleted, overwritten, or retrained automatically.
- All artifact paths, metadata, thresholds, and performance metrics are documented below.

---

## 2. Pretrained Model Catalog

### Baseline Models (`models/model_01/`, `model_02/`, `model_03/`)

| Model ID | Lifecycle Stage | Algorithm | Artifact Location | Decision Threshold | Test Performance | Key Features |
|---|---|---|---|---|---|---|
| `model_01` | Order Placement | Logistic Regression (`l2`, `liblinear`) | `models/model_01/logistic_regression_model.joblib` | 0.50 | Accuracy: 69.29%<br>Recall: 68.8%<br>ROC-AUC: 0.741 | Days for shipment (scheduled), Type, Order Region, Order Item Quantity, Sales |
| `model_02` | Carrier Dispatch | XGBoost Classifier (`max_depth=4`, `lr=0.05`) | `models/model_02/xgboost_model.joblib` | 0.50 | Accuracy: 70.83%<br>Recall: 58.6%<br>ROC-AUC: 0.762 | Shipping Mode, Days for shipment (scheduled), Order Region, Order Status, Quantity |
| `model_03` | Transit / Routing | CatBoost Regressor (RMSE Loss) | `models/model_03/catboost_model.cbm` | N/A (Regression) | RMSE: 1.02 days<br>MAE: 0.78 days | Shipping Mode, Scheduled Days, Order Region, Product Category |

---

### Improved Models (`models/model_01_improved/`, `model_02_improved/`, `model_03_improved/`)

| Model ID | Lifecycle Stage | Algorithm | Artifact Location | Decision Threshold | Test Performance | Improvements Implemented |
|---|---|---|---|---|---|---|
| `model_01_improved` | Order Placement | LightGBM Classifier (`num_leaves=31`, `lr=0.03`) | `models/model_01_improved/best_model.joblib` | 0.35 | Accuracy: 71.45%<br>Recall: 76.2%<br>ROC-AUC: 0.782 | Enhanced customer/order features, price, discount rate, operational threshold |
| `model_02_improved` | Carrier Dispatch | Tuned XGBoost (`max_depth=5`, `scale_pos_weight`) | `models/model_02_improved/xgboost_model_improved.joblib` | 0.40 | Accuracy: 72.80%<br>Recall: 79.4%<br>ROC-AUC: 0.791 | Warehouse elapsed processing days, balanced dispatch threshold |
| `model_03_improved` | Transit / Routing | Random Forest Regressor / Tuned CatBoost | `models/model_03_improved/best_regressor.joblib` | N/A (Regression) | RMSE: 0.94 days<br>MAE: 0.69 days | Quantile loss, geographic interaction terms, route priority |

---

### Reference Methodology Pipeline Model (`models/order_creation_reference_pipeline/`)

| Model ID | Lifecycle Stage | Algorithm | Artifact Location | Decision Threshold | Test Performance | Reference Origin |
|---|---|---|---|---|---|---|
| `routemind_order_creation_random_forest` | Order Placement | Random Forest Classifier (`class_weight='balanced'`) | `models/order_creation_reference_pipeline/routemind_order_creation_random_forest.joblib` | 0.33 | Validation Accuracy: 68.06%<br>Late Recall: 96.9%<br>Val ROC-AUC: 0.7236 | Notebook Cell 2 ColumnTransformer + Balanced Random Forest; Cost-optimal threshold |
