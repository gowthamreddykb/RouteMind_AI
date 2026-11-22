# RouteMind AI - Complete Project Audit Report

## 1. Executive Summary & Codebase Architecture

RouteMind AI is a production-grade Logistics Control Tower system designed to predict late-delivery risks and calculate shipment delay deviations across multi-stage logistics operations.

This audit report documents the structural layout, model inventories, database adapters, dataset isolation boundaries, and inference endpoints across the workspace (`c:\gowtham_mithraz\RouteMind_AI project`) and the modular framework repository (`C:\gowtham_mithraz\RouteMind_AI`).

---

## 2. Source Code Architecture & File Inventory

### Core Modules (`c:\gowtham_mithraz\RouteMind_AI project`)

| File / Module | Purpose | Status | Key Components |
|---|---|---|---|
| `app.py` | Flask REST API Server | Operational | Endpoints for `/health`, `/dashboard`, `/predict/order-creation`, `/predict/dispatch`, `/predict/delay-duration`, `/predict/control-tower`, `/predict/live-event`, `/predict/batch`, `/models/registry`, `/metrics` |
| `prediction_service.py` | Unified Inference Engine | Operational | Dual-model inference, schema validation, thresholding, database persistence hooks |
| `pipeline/run_pipeline.py` | 13-Stage Pipeline Orchestrator | Operational | Full CLI executing Stages 01 through 13 with `--dataset historical` or `--dataset new_excel` |
| `pipeline/stage_01_ingestion.py` | Ingestion & Checksums | Operational | SHA256 integrity, independent raw dataset loading |
| `pipeline/stage_02_cleaning.py` | Data Cleaning & Deduplication | Operational | Target validation, PII removal, missingness summary |
| `pipeline/stage_03_eda.py` | EDA & Imbalance Calculation | Operational | `scale_pos_weight = negative_count / positive_count` (Cell 15) |
| `pipeline/stage_04_feature_engineering.py` | Preprocessor & Features | Operational | ColumnTransformer with SimpleImputer + OneHotEncoder (Cell 2) |
| `pipeline/stage_05_feature_selection.py` | Domain Availability Audit | Operational | Lifecycle availability gates, post-delivery column strip |
| `pipeline/stage_06_data_splitting.py` | Group-Aware Splitting | Operational | Order Id group preservation + stratified test split (Cell 1) |
| `pipeline/stage_07_model_training.py` | Multi-Model Fitting | Operational | Random Forest (Cell 2), XGBoost (Cell 15), Logistic Regression, LightGBM |
| `pipeline/stage_08_hyperparameter_tuning.py` | Hyperparameter Tuning | Operational | Validation grid search on depth, estimators, learning rate |
| `pipeline/stage_09_model_comparison.py` | Model Benchmarking Table | Operational | 6-metric side-by-side table (Cell 18) |
| `pipeline/stage_10_threshold_optimization.py`| Threshold Optimization | Operational | Penalty cost minimization (Cost_FN=2.0, Cost_FP=1.0) |
| `pipeline/stage_11_evaluation.py` | Test Partition Evaluation | Operational | ConfusionMatrixDisplay (Cell 12 & 17), monotonic risk buckets |
| `pipeline/stage_12_explainability.py` | Feature Attribution | Operational | Tree feature importance extraction |
| `pipeline/stage_13_registry_and_export.py`| Registry & Export | Operational | Non-destructive bundle export & registry.json cataloging |
| `pipeline/live_event_manager.py` | Streaming Event Manager | Operational | `add_new_event()` implementation (Cell 6 & 20) |
| `sql/schema.sql` | DDL Schema Definition | Operational | MySQL 8.0+ / SQLite schemas for registry, scores, and events |
| `sql/db_adapter.py` | Database Persistence Adapter | Operational | SQLite / MySQL zero-config persistence adapter |
| `static/control_tower_dashboard.html` | Interactive Web Dashboard | Operational | Live event scoring, KPI cards, model registry view |
| `test_flask_service.py` | Service & API Test Suite | Passed (100%) | Validates all baseline & improved endpoints |
| `test_pipeline_and_db.py` | Pipeline & DB Integration Tests | Passed (7/7) | Validates ingestion, splitting, persistence, and live events |

---

## 3. Dataset Integrity & Isolation Verification

Two distinct raw datasets are preserved in isolated directories:
1. **Historical DataCo CSV**: `data/raw/historical_dataco/DataCoSupplyChainDataset.csv` (180,519 rows x 53 columns, SHA256: `fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6`).
2. **Newly Provided DataCo Excel**: `data/raw/newly_provided_dataset/DataCoSupplyChainDataset_new_dataset.xlsx` (180,519 rows x 67 columns, SHA256: `de5024211b623ac7a887c89d38745cbd1ce72dc793700c8f88fca3ac8b8981ea`).

Columns 0 through 52 of the Excel dataset match the CSV exactly. Columns 53 through 66 contain auxiliary Excel pivot/summary calculations which are automatically stripped by `stage_01_ingestion.py`. Zero data contamination occurs between the two datasets.
