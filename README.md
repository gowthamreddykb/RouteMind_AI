# RouteMind AI – Enterprise Logistics Control Tower

RouteMind AI is a production-grade Logistics Control Tower and shipment risk intelligence platform featuring genuine machine learning models, dual-stage predictive inference (Order Creation & Warehouse Dock Dispatch), anomaly detection, automated carrier SLA communication, and an interactive AI Operations Copilot.

---

## 📁 Project Architecture & Directory Layout

```
RouteMindAI/
│
├── app.py                            # Flask Application Factory & Blueprints
├── config.py                         # Environment Configurations
├── extensions.py                     # SQLAlchemy & Login Manager Extensions
├── requirements.txt                  # Python Project Dependencies
├── .env                              # Environment Variables
├── .env.example                      # Example Environment Configuration
├── .gitignore                        # Git Ignore Rules
├── README.md                         # Project Architecture & Guide
│
├── instance/
│   └── routemind.db                  # Local SQLite Production Database
│
├── templates/                        # Jinja2 HTML View Templates
│   ├── base.html                     # Global Shell & Navigation
│   ├── login.html                    # User Authentication Screen
│   ├── forgot_password.html          # Password Reset Interface
│   ├── reports.html                  # SLA & Operational Analytics
│   ├── shipment_list.html            # Shipment Registry Table
│   ├── shipment_form.html            # New Shipment Intake Form
│   ├── shipment_detail.html          # Individual Shipment Deep Dive
│   ├── exception_list.html           # Active SLA Breach Exceptions Queue
│   ├── ai_assistant.html             # AI Logistics Copilot Chat
│   ├── users.html                    # User & Personnel Directory
│   ├── user_form.html                # User Creation Form
│   └── admin_settings.html           # Model Governance & Settings
│
├── static/                           # Static Assets
│   ├── css/                          # Modular Stylesheets
│   │   ├── style.css                 # Base Styling
│   │   ├── auth.css                  # Authentication Forms
│   │   ├── dashboard.css             # Control Tower Dashboard Styling
│   │   ├── shipments.css             # Shipment Tables & Cards
│   │   ├── analytics.css             # Charts & Data Visuals
│   │   ├── exceptions.css            # Exception Queue Highlights
│   │   ├── ai_assistant.css          # Chatbot Styling
│   │   ├── forms.css                 # Form Elements
│   │   └── responsive.css            # Mobile & Tablet Breakpoints
│   │
│   ├── js/                           # Frontend Interactive Logic
│   │   ├── main.js                   # Application Bootstrapper
│   │   ├── dashboard.js              # Real-Time Telemetry
│   │   ├── shipment_list.js          # Table Search & Filters
│   │   ├── shipment_form.js          # Intake Form Validation
│   │   ├── shipment_detail.js        # Shipment Timeline Loader
│   │   ├── anomaly.js                # Anomaly Scorer
│   │   ├── clusters.js               # Cluster Visualizations
│   │   ├── exceptions.js             # Resolution Escalator
│   │   ├── ai_assistant.js           # Copilot Chat Handler
│   │   ├── users.js                  # User Management
│   │   └── admin_settings.js         # Settings & Registry Admin
│   │
│   └── images/                       # Brand & Illustration Assets
│       ├── logo.png
│       ├── login_maritime.png
│       ├── ship_illustration.png
│       └── favicon.ico
│
├── src/                              # Core Application Source Code
│   ├── __init__.py
│   │
│   ├── routes/                       # Flask Blueprint Routes
│   │   ├── __init__.py               # Blueprint Registration
│   │   ├── auth_routes.py            # Authentication Endpoints
│   │   ├── report_routes.py          # KPI & Performance Reports
│   │   ├── shipment_routes.py        # Shipment Intake & API
│   │   ├── anomaly_routes.py         # Anomaly Detection API
│   │   ├── cluster_routes.py         # Lane Cluster Visualizer
│   │   ├── exception_routes.py       # Exceptions & Escalations
│   │   ├── ai_assistant_routes.py    # AI Chat Copilot API
│   │   ├── communication_routes.py   # Automated Notice Generator
│   │   ├── user_routes.py            # Personnel Management
│   │   └── admin_routes.py           # Model Governance Admin
│   │
│   ├── models/                       # SQLAlchemy Database ORM Models
│   │   ├── __init__.py
│   │   ├── user_model.py             # User & RBAC Accounts
│   │   ├── customer_model.py         # Customer Profiles
│   │   ├── product_model.py          # Catalog & Pricing
│   │   ├── shipment_model.py         # Shipment Master Records
│   │   ├── shipment_event_model.py   # Lifecycle Tracking Events
│   │   ├── model_registry_model.py   # Machine Learning Registry
│   │   ├── model_score_model.py      # Historical Predictions Log
│   │   ├── risk_factor_model.py      # SHAP Factor Explanations
│   │   ├── exception_model.py        # SLA Exceptions
│   │   ├── exception_action_model.py # Remediation Actions
│   │   ├── communication_model.py    # Outbound Notices Log
│   │   ├── reference_data_model.py   # Lookup Categories & Codes
│   │   └── audit_log_model.py        # Compliance Audit Trail
│   │
│   ├── services/                     # Business Logic Services
│   │   ├── __init__.py
│   │   ├── auth_service.py           # User Authentication Logic
│   │   ├── shipment_service.py       # Order & Shipment CRUD
│   │   ├── report_service.py         # Metric Aggregations
│   │   ├── prediction_service.py     # Dual-Stage Model Inference
│   │   ├── anomaly_service.py        # Isolation Forest Anomaly Engine
│   │   ├── clustering_service.py     # Lane Cluster Engine
│   │   ├── exception_service.py      # Exception Lifecycle
│   │   ├── communication_service.py  # Dispatch Notice Generator
│   │   ├── ai_assistant_service.py   # LLM Copilot Engine
│   │   └── audit_service.py          # Security Audit Service
│   │
│   ├── ml/                           # Dedicated ML Modules
│   │   ├── __init__.py
│   │   ├── order_creation/           # Stage 1: Order Creation Model
│   │   │   ├── preprocessing.py
│   │   │   ├── prediction.py
│   │   │   └── evaluation.py
│   │   ├── dispatch_prediction/      # Stage 2: Warehouse Dispatch Model
│   │   │   ├── preprocessing.py
│   │   │   ├── prediction.py
│   │   │   └── evaluation.py
│   │   ├── delay_estimation/         # Duration Regressor
│   │   │   ├── preprocessing.py
│   │   │   ├── prediction.py
│   │   │   └── evaluation.py
│   │   ├── anomaly_detection/        # Unsupervised Isolation Forest
│   │   │   ├── preprocessing.py
│   │   │   └── detection.py
│   │   ├── clustering/               # KMeans Transit Segmentation
│   │   │   ├── preprocessing.py
│   │   │   └── clustering.py
│   │   └── explainability/           # TreeSHAP Interpretability
│   │       ├── shap_explainer.py
│   │       └── feature_explanations.py
│   │
│   ├── ai/                           # Generative AI & Copilot Engine
│   │   ├── __init__.py
│   │   ├── llm_client.py             # LLM API Client Wrapper
│   │   ├── chatbot.py                # Conversational Controller
│   │   ├── context_builder.py        # Contextual Pipeline Injector
│   │   ├── query_handler.py          # Intent Matcher
│   │   ├── response_formatter.py     # Markdown Output Formatter
│   │   ├── resolution_recommender.py # Delay Remediation Recommender
│   │   ├── communication_generator.py# Carrier SLA Breach Writer
│   │   └── prompt_templates.py       # Domain Logistics Prompts
│   │
│   ├── security/                     # Security & Permissions
│   │   ├── __init__.py
│   │   ├── authentication.py         # Password Hashing
│   │   ├── authorization.py          # Role Decorators
│   │   ├── role_permissions.py       # RBAC Matrix
│   │   └── validators.py             # Input Sanitizers
│   │
│   └── utils/                        # Shared Utilities
│       ├── __init__.py
│       ├── date_utils.py             # Timestamp & SLA Computations
│       ├── file_utils.py             # JSON & File Helpers
│       ├── response_utils.py         # Standardized API Responders
│       └── logging_utils.py          # Structured Logger
│
├── data/                             # Data Assets
│   ├── raw/                          # Raw Historical Datasets
│   ├── interim/                      # Cleaned Intermediate Data
│   ├── processed/                    # Feature-Engineered Sets
│   │   ├── order_creation/
│   │   ├── dispatch_prediction/
│   │   ├── delay_estimation/
│   │   ├── anomaly_detection/
│   │   └── clustering/
│   └── sample/                       # Demo Shipments
│
├── models/                           # Trained Model Serialized Binaries
│   ├── order_creation/               # Model 01 Artifacts
│   │   ├── logistic_regression.pkl
│   │   ├── preprocessing_pipeline.pkl
│   │   └── feature_columns.json
│   ├── dispatch_prediction/          # Model 02 Artifacts
│   │   ├── xgboost_model.json
│   │   ├── preprocessing_pipeline.pkl
│   │   └── feature_columns.json
│   ├── delay_estimation/             # Model 03 Artifacts
│   │   ├── catboost_model.cbm
│   │   └── feature_columns.json
│   ├── anomaly_detection/            # Isolation Forest Artifacts
│   │   ├── isolation_forest.pkl
│   │   └── preprocessing_pipeline.pkl
│   ├── clustering/                   # KMeans Clustering Artifacts
│   │   ├── kmeans_model.pkl
│   │   └── preprocessing_pipeline.pkl
│   └── metadata/                     # Model Lineage & Metrics
│       ├── model_versions.json
│       └── training_metadata.json
│
├── reports/                          # Audit & Evaluation Reports
│   ├── data_analysis/
│   ├── data_quality/
│   ├── model_evaluation/
│   └── visualizations/
│
├── migrations/                       # Database Migrations
│   └── versions/
│
├── tests/                            # Automated Pytest Suite
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_permissions.py
│   ├── test_shipments.py
│   ├── test_predictions.py
│   ├── test_anomalies.py
│   ├── test_exceptions.py
│   ├── test_ai_assistant.py
│   └── test_reports.py
│
├── notebooks/                        # Jupyter Research Notebooks
│   ├── data_exploration.ipynb
│   ├── data_patterns.ipynb
│   ├── order_creation_training.ipynb
│   ├── dispatch_training.ipynb
│   ├── delay_estimation_training.ipynb
│   ├── anomaly_detection.ipynb
│   └── clustering_analysis.ipynb
│
└── docs/                             # Comprehensive Documentation
    ├── requirements.md
    ├── system_architecture.md
    ├── database_schema.md
    ├── ml_documentation.md
    ├── ai_assistant_documentation.md
    └── installation_guide.md
```

---

## 🚀 Quickstart & Execution

```bash
# 1. Navigate to project root
cd C:\gowtham_mithraz\RouteMind_AI

# 2. Activate virtual environment
.\RouteMind_AI_venv\Scripts\activate

# 3. Run the Control Tower server
python app.py
```

The web dashboard is accessible at **`http://127.0.0.1:5000`**.
Default administrator credentials:
- **Username**: `admin`
- **Password**: `admin123`

---

## 🧪 Verification & Test Suite

Run all unit and integration tests across security, services, models, and routes:
```bash
python -m pytest tests/ -v
```
All tests pass with 100% compliance.

---

## 📋 Comprehensive System Documentation (from docs/)

### 1. Requirements Specification (`docs/requirements.md`)

#### Functional Requirements
- **Dual-Stage Machine Learning Risk Inference**:
  - Stage 1: Order Placement Risk Model evaluating scheduled days, payment type, destination region, category, price, and sales.
  - Stage 2: Warehouse Dock Dispatch Risk Model evaluating dock processing duration vs. scheduled lead time to catch bottlenecks before carrier handover.
- **Delay Duration Estimation**: Continuous day estimation to determine actionable late delay magnitude (e.g., +2.0 days late).
- **Explainable AI (SHAP Attribution)**: Top risk factor drivers and directionality displayed per shipment score.
- **Automated Exception Management & Remediation**:
  - Automatic exception flagging for orders exceeding critical risk thresholds (p ≥ 0.40).
  - Remediation workflows: carrier upgrade, priority sleeper team linehaul, alternative hub rerouting.
- **Automated Carrier & Customer SLA Notices**: Dynamic template notice generation with one-click dispatch logging.
- **Interactive AI Logistics Operations Copilot**: Built-in chat assistant evaluating live maritime shipments, dangerous goods (DG), reefer cargo, and risk mitigation plans.
- **Role-Based Access Control (RBAC)**: Secure access tiers for Administrator (`admin`), Operations Manager (`manager`), and Operations Analyst / Dispatcher (`dispatcher`).

#### Non-Functional Requirements
- **Low-Latency Inference**: Sub-50ms inference latency for single-order prediction scoring.
- **Data Integrity & Group Isolation**: Group-aware stratified train/test validation preserving order grouping without temporal or target leakage.
- **Relational Persistence**: ACID-compliant SQLite and MySQL persistence using SQLAlchemy ORM.
- **100% Automated Test Pass Rate**: Full regression suite verifying models, routes, permissions, and database operations.

---

### 2. System Architecture (`docs/system_architecture.md`)

```
[ Client Browser / Web UI (Bootstrap 5.3 + Tailwind + Chart.js) ]
                             │
                             ▼
[ Flask Application Factory (app.py) ]
    ├── Security: Flask-Login, Session Management, RBAC, Password Hashing
    ├── Database: SQLite / MySQL SQLAlchemy ORM (14 Models)
    ├── Blueprints Layer:
    │     ├── auth_bp (/auth)
    │     ├── shipment_bp (/shipments)
    │     ├── report_bp (/reports)
    │     ├── anomaly_bp (/anomalies)
    │     ├── cluster_bp (/clusters)
    │     ├── exception_bp (/exceptions)
    │     ├── ai_bp (/ai/assistant)
    │     ├── comm_bp (/ai/communications)
    │     ├── user_bp (/users)
    │     └── admin_bp (/admin)
    └── Services & Inference Engine:
          ├── PredictionService (Dual-Stage Scoring + SHAP Attribution)
          ├── ShipmentService (CRUD, Telemetry Events, Risk Level Updates)
          ├── ExceptionService (SLA Breach Escalations & Action Plans)
          ├── AIAssistantService (Maritime Operations Copilot)
          ├── CommunicationService (Automated Dispatch Notices)
          └── AnomalyService & ClusteringService (Isolation Forest & KMeans)
```

---

### 3. Database Schema Specification (`docs/database_schema.md`)

All models inherit from `extensions.db.Model` using SQLAlchemy ORM:

| Table Name | Primary Keys & Foreign Keys | Key Attributes & Description |
|---|---|---|
| `users` | `id` (PK) | `username`, `email`, `password_hash`, `role`, `is_active`, `created_at` |
| `customers` | `id` (PK) | `first_name`, `last_name`, `segment`, `city`, `state`, `country` |
| `products` | `id` (PK) | `product_name`, `category_name`, `department_name`, `product_price` |
| `shipments` | `id` (PK), `customer_id` (FK), `product_id` (FK) | `shipment_number`, `order_date`, `scheduled_days`, `shipping_mode`, `sales`, `quantity`, `destination_region`, `order_creation_prob`, `dispatch_prob`, `risk_level`, `dock_clearance_status` |
| `shipment_events` | `id` (PK), `shipment_id` (FK) | `event_type`, `warehouse_processing_time`, `notes`, `timestamp` |
| `model_registry` | `id` (PK) | `model_name`, `version`, `stage`, `algorithm`, `accuracy`, `roc_auc`, `decision_threshold`, `approval_status` |
| `model_scores` | `id` (PK), `shipment_id` (FK) | `stage`, `predicted_probability`, `predicted_class`, `risk_level`, `created_at` |
| `risk_factors` | `id` (PK), `score_id` (FK) | `feature_name`, `feature_value`, `contribution_value`, `direction` |
| `shipment_exceptions` | `id` (PK), `shipment_id` (FK) | `exception_type`, `severity`, `status`, `assigned_to`, `created_at` |
| `exception_actions` | `id` (PK), `exception_id` (FK) | `action_taken`, `action_by`, `action_notes`, `timestamp` |
| `communication_logs` | `id` (PK), `shipment_id` (FK) | `recipient`, `channel`, `message_body`, `sent_at` |
| `audit_logs` | `id` (PK), `user_id` (FK) | `action`, `entity`, `entity_id`, `details`, `timestamp` |
| `reference_data` | `id` (PK) | `category`, `code`, `name`, `sort_order`, `is_active` |

---

### 4. Machine Learning Models Specification (`docs/ml_documentation.md`)

#### Model 01: Order Placement Delay Risk
- **Stage**: Order Placement / Initial Booking
- **Algorithm**: Logistic Regression Baseline & XGBoost / LightGBM Classifier
- **Input Features (8)**: `Days for shipment (scheduled)`, `Type`, `Shipping Mode`, `Order Region`, `Market`, `Category Name`, `Order Item Product Price`, `Sales`
- **Optimal Decision Threshold**: 0.40 (Asymmetric cost optimization)
- **Performance**: Accuracy: 69.29% | ROC-AUC: 0.7720

#### Model 02: Warehouse Dock Dispatch Risk
- **Stage**: Carrier Handover / Warehouse Dock Departure
- **Algorithm**: XGBoost Classifier with Early Stopping
- **Input Features (7)**: `Days for shipment (scheduled)`, `Order-to-Ship Time`, `Shipping Mode`, `Order Region`, `Market`, `Department Name`, `Customer Segment`
- **Optimal Decision Threshold**: 0.39
- **Performance**: Accuracy: 97.52% | ROC-AUC: 0.9985

#### Model 03: Delay Duration Regressor
- **Stage**: Transit / Routing Estimation
- **Architecture**: Two-Stage Gating Hurdle Architecture (CatBoost Native C++ Regressor)
- **Target**: Continuous shipping duration (real) and derived net delay deviation (days relative to schedule)
- **Action Plan Triggers**:
  - `+1 Day`: Informational alert; monitor regional dock.
  - `+2 Days`: Moderate risk; flag customer support and prioritize sorting.
  - `+3+ Days`: Critical risk; trigger priority sleeper team linehaul or air freight reroute.

---

### 5. Interactive AI Operations Copilot (`docs/ai_assistant_documentation.md`)

- Built-in maritime operations copilot interface accessible on every page drawer and dedicated `/ai/assistant` view.
- Evaluates real-time shipment risk probabilities, dangerous goods cargo (DG), refrigerated container (reefer) status, and port congestion indices.
- Dispatches automated SLA recovery suggestions directly to dispatchers and operations managers.
