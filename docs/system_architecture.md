# RouteMind AI - System Architecture

```
[ Client Browser / Web UI ]
            │
            ▼
[ Flask Application Factory (app.py) ]
    ├── Blueprints: auth, shipments, reports, anomalies, clusters, exceptions, ai, admin
    ├── Security: Flask-Login, RBAC, CSRF, Password Hashing
    ├── Database: SQLite / MySQL SQLAlchemy ORM (14 Models)
    └── Services Layer:
            ├── PredictionService (Model 01 + Model 02)
            ├── ShipmentService & ExceptionService
            ├── AIAssistantService & CommunicationService
            └── AnomalyService & ClusteringService
```
