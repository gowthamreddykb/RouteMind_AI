# RouteMind AI - Requirements Specification

## 1. Functional Requirements
- Dual-stage machine learning inference (Order Creation & Warehouse Dock Dispatch).
- Real-time SLA risk scoring, probability calibration, and SHAP explainability.
- Warehouse bottleneck detection (Order-to-Ship duration vs scheduled window).
- Exception management workflow and automated carrier communication generation.
- Role-based access control (Admin, Dispatcher, Analyst, Viewer).

## 2. Non-Functional Requirements
- Sub-50ms inference latency for single-order scoring.
- Leak-free chronological validation splits.
- 100% test pass rate with strict reproducible pipelines.
