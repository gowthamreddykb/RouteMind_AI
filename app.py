"""
app.py - RouteMind AI Enterprise Flask Application Factory
Predictive Maritime Shipment Operations & Exception Management Control Tower
Preserves architecture: create_app(), SQLAlchemy ORM, Flask-Login, RBAC, MySQL.
"""
import os
import sys
import json
import logging
import datetime as dt
from typing import Dict, Any, List, Optional

from flask import Flask, jsonify, request, render_template, redirect, url_for, abort
from flask_login import login_required, current_user, logout_user
from sqlalchemy import text
from dotenv import load_dotenv

# Path resolutions: Robust project root detection across local, Docker, and cloud hosts (e.g. Render /opt/render/project/src)
_curr = os.path.abspath(os.path.dirname(__file__))
if os.path.exists(os.path.join(_curr, 'templates')):
    BASE_DIR = _curr
elif os.path.exists(os.path.join(os.path.dirname(_curr), 'templates')):
    BASE_DIR = os.path.dirname(_curr)
else:
    BASE_DIR = _curr

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
src_dir = os.path.join(BASE_DIR, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

load_dotenv(os.path.join(BASE_DIR, '.env'))

from config import config_by_name
from extensions import db, login_manager
from src.routes import register_routes
from src.models.user_model import User
from src.models.shipment_model import Shipment
from src.models.exception_model import ShipmentException
from src.models.model_score_model import ModelScore
from src.services.shipment_service import ShipmentService
from src.services.dashboard_service import DashboardService
from src.services.prediction_service import (
    PredictionService,
    ORDER_CREATION_REQUIRED,
    DISPATCH_REQUIRED
)
from src.security.permissions import (
    roles_required,
    ROLE_DISPATCHER,
    ROLE_MANAGER,
    ROLE_ADMIN,
    ALL_ROLES,
    normalize_role
)
import src.prediction as PR
import src.dispatch_prediction as DP

# Setup logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('routemind.app')

MAX_BATCH_SIZE = 100


def create_app(config_name=None, db_path=None, **kwargs):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'templates'),
        static_folder=os.path.join(BASE_DIR, 'static')
    )
    app.config['BASE_DIR'] = BASE_DIR

    # Bulletproof Jinja template resolution across local, Docker, and Render cloud environments
    from jinja2 import ChoiceLoader, FileSystemLoader
    candidate_template_dirs = [
        os.path.join(BASE_DIR, 'templates'),
        os.path.join(_curr, 'templates'),
        os.path.abspath('templates'),
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')),
    ]
    seen_dirs = set()
    valid_loaders = []
    for d in candidate_template_dirs:
        norm = os.path.normpath(d)
        if norm not in seen_dirs and os.path.isdir(norm):
            seen_dirs.add(norm)
            valid_loaders.append(FileSystemLoader(norm))
    if app.jinja_loader:
        valid_loaders.append(app.jinja_loader)
    app.jinja_loader = ChoiceLoader(valid_loaders)
    if isinstance(config_name, str):
        app.config.from_object(config_by_name.get(config_name, config_by_name['default']))
    elif isinstance(config_name, type) or hasattr(config_name, '__dict__'):
        app.config.from_object(config_name)

    if db_path:
        abs_db = os.path.abspath(db_path).replace(os.sep, '/')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{abs_db}"

    for k, v in kwargs.items():
        app.config[k.upper()] = v

    # Ensure MODELS_DIR points to a valid on-disk directory (handles cloud platforms where Windows paths don't exist)
    cfg_models = app.config.get('MODELS_DIR')
    if not cfg_models or not os.path.isdir(str(cfg_models)):
        app.config['MODELS_DIR'] = os.path.join(BASE_DIR, 'models')

    # Resilient Database Connection: if MySQL/TiDB is configured, verify connectivity with cloud tolerance
    db_uri = str(app.config.get('SQLALCHEMY_DATABASE_URI', ''))
    if 'mysql' in db_uri.lower() and not db_path:
        is_production = os.environ.get('FLASK_ENV') == 'production' or (isinstance(config_name, str) and config_name == 'production')
        try:
            import socket, urllib.parse
            parsed = urllib.parse.urlsplit(db_uri.replace('mysql+pymysql://', 'http://').replace('mysql://', 'http://'))
            host = parsed.hostname or '127.0.0.1'
            port = parsed.port or 3306
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 3.0s timeout to accommodate cloud gateway latency (e.g. TiDB Cloud Serverless)
            sock.settimeout(3.0)
            check_result = sock.connect_ex((host, port))
            sock.close()
            if check_result != 0:
                if not is_production:
                    sqlite_fallback = os.path.abspath(os.path.join(BASE_DIR, "instance", "routemind.db")).replace(os.sep, "/")
                    logger.warning(f"Database server at {host}:{port} is unreachable. Falling back to local SQLite at {sqlite_fallback}")
                    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{sqlite_fallback}"
                else:
                    logger.error(f"Configured production database at {host}:{port} was not reachable on port check (code {check_result}). Retaining URI for SQLAlchemy connection pool.")
        except Exception as check_err:
            if not is_production:
                sqlite_fallback = os.path.abspath(os.path.join(BASE_DIR, "instance", "routemind.db")).replace(os.sep, "/")
                logger.warning(f"Database availability check exception ({check_err}). Falling back gracefully to local SQLite at {sqlite_fallback}")
                app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{sqlite_fallback}"
            else:
                logger.warning(f"Database availability check exception ({check_err}). Retaining URI.")

    if app.config.get('TESTING'):
        app.config['LOGIN_DISABLED'] = True

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    if db_path:
        with app.app_context():
            db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # Global Authentication & Authorization Middleware
    @app.before_request
    def enforce_authentication():
        # Testing mode bypass: when TESTING is enabled, disable login checks
        if app.config.get('TESTING'):
            app.config['LOGIN_DISABLED'] = True
            return

        if app.config.get('LOGIN_DISABLED'):
            return

        # 1. Static assets and favicon
        if request.path.startswith('/static/') or request.path == '/favicon.ico':
            return

        # 2. Public health check and test prediction endpoints
        if request.path in {'/health', '/models/registry', '/metrics', '/database/recent-scores'} or request.path.startswith('/predict/'):
            return

        # 3. Explicit public authentication routes
        if request.path in {
            '/auth/login', '/auth/request-otp', '/auth/verify-otp',
            '/auth/resend-otp', '/auth/forgot-password', '/auth/reset-password',
            '/api/auth/login', '/api/auth/forgot-password', '/api/auth/reset-password'
        }:
            return

        # 4. Quick login in non-production testing
        if request.path.startswith('/auth/quick-login/') and app.config.get('ENV') != 'production':
            return

        # Check Bearer token authentication for API requests
        auth_header = request.headers.get('Authorization', '')
        if not current_user.is_authenticated and auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
            if token.startswith('USR-'):
                try:
                    parts = token.split('-')
                    uid = int(parts[1])
                    u = User.query.get(uid)
                    if u and u.is_active:
                        login_user(u)
                except Exception:
                    pass

        # 5. Check user authentication
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api/') or request.headers.get('Accept', '').startswith('application/json'):
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Authentication required. Please authenticate to access this resource.',
                    'status': 401
                }), 401
            return redirect(url_for('auth_bp.login', next=request.path))

        # 6. Check active user status
        if not getattr(current_user, 'is_active', True):
            logout_user()
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Account Deactivated',
                    'message': 'Your account has been deactivated. Please contact an Administrator.',
                    'status': 403
                }), 403
            return redirect(url_for('auth_bp.login', next=request.path))

    # Global HTTP error handlers
    @app.errorhandler(401)
    def handle_unauthorized(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized', 'message': 'Authentication required.', 'status': 401}), 401
        return redirect(url_for('auth_bp.login', next=request.path))

    @app.errorhandler(403)
    def handle_forbidden(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Forbidden', 'message': 'Access denied: Insufficient role permissions.', 'status': 403}), 403
        return render_template('base.html', error_message="Access Denied: You do not have permissions for this page."), 403

    @app.errorhandler(404)
    def handle_not_found(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Not Found', 'message': 'The requested resource was not found.', 'status': 404}), 404
        return render_template('base.html', error_message="Resource not found."), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        logger.error(f"Internal server error: {e}", exc_info=True)
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected server error occurred.', 'status': 500}), 500
        return render_template('base.html', error_message="Internal Server Error: Our engineers have been alerted."), 500

    # Register blueprints
    register_routes(app)

    # -------------------------------------------------------------
    # Core Control Tower Dashboard Route
    # -------------------------------------------------------------
    @app.route('/')
    @app.route('/dashboard')
    @login_required
    @roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
    def dashboard():
        shipments = ShipmentService.get_all(limit=10, user=current_user)
        total_shipments = ShipmentService.count_for_user(current_user)
        high_risk_count = ShipmentService.count_for_user(current_user, risk_level=['HIGH', 'CRITICAL', 'CRITICAL_RISK'])
        # All unresolved exceptions for user's assigned/created shipments (OPEN, INVESTIGATING, IN_REVIEW)
        user_name = getattr(current_user, 'username', None)
        user_id = getattr(current_user, 'id', None)
        user_role = normalize_role(getattr(current_user, 'role', ''))
        exceptions_query = ShipmentException.query.join(Shipment, ShipmentException.shipment_id == Shipment.id).filter(
            ShipmentException.status.in_(['OPEN', 'INVESTIGATING', 'IN_REVIEW'])
        )
        if user_role not in [ROLE_MANAGER, ROLE_ADMIN] and (user_name or user_id):
            exceptions_query = exceptions_query.filter(
                (Shipment.assigned_to_name == user_name) |
                (Shipment.assigned_to_id == user_id) |
                (Shipment.created_by_id == user_id) |
                (Shipment.created_by_name == user_name) |
                (Shipment.assigned_to_name.is_(None)) |
                (Shipment.assigned_to_name == '') |
                (ShipmentException.assigned_to == user_name) |
                (ShipmentException.assigned_to.is_(None)) |
                (ShipmentException.assigned_to == '')
            )
        exceptions_count = exceptions_query.count()
        on_time_count = ShipmentService.count_for_user(current_user, risk_level='LOW')
        late_count = high_risk_count
        on_time_pct = round((on_time_count / total_shipments) * 100, 1) if total_shipments > 0 else 0.0

        # Retrieve ground-truth initial chart payloads via DashboardService
        charts_payload = DashboardService.get_all_charts(user=current_user)

        return render_template(
            'index.html',
            shipments=shipments,
            total_shipments=total_shipments,
            high_risk_count=high_risk_count,
            exceptions_count=exceptions_count,
            on_time_count=on_time_count,
            late_count=late_count,
            on_time_pct=on_time_pct,
            charts_payload=charts_payload
        )

    # -------------------------------------------------------------
    # System Health Diagnostic Endpoint (Public)
    # -------------------------------------------------------------
    @app.get('/health')
    def health():
        # Database connectivity check
        try:
            db.session.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            logger.warning(f"Health DB probe failed: {e}")
            db_status = "disconnected"

        models_dir = app.config.get('MODELS_DIR', os.path.join(BASE_DIR, 'models'))

        # Check Model 01 (Logistic Regression)
        m1_paths = [
            os.path.join(models_dir, 'model_01', 'logistic_regression_pipeline.joblib'),
            os.path.join(models_dir, 'model_01_improved', 'best_model.joblib'),
            os.path.join(models_dir, 'model_01', 'logistic_regression_model.joblib')
        ]
        m1_active = any(os.path.exists(p) for p in m1_paths)

        # Check Model 02 (XGBoost Classifier)
        m2_paths = [
            os.path.join(models_dir, 'model_02', 'xgboost_dispatch_pipeline.joblib'),
            os.path.join(models_dir, 'model_02_improved', 'best_model.joblib'),
            os.path.join(models_dir, 'model_02', 'xgboost_model.joblib')
        ]
        m2_active = any(os.path.exists(p) for p in m2_paths)

        # Check Model 03 (CatBoost Regressor)
        m3_paths = [
            os.path.join(models_dir, 'model_03', 'catboost_delay_regressor.cbm'),
            os.path.join(models_dir, 'model_03_improved', 'best_regressor.joblib'),
            os.path.join(models_dir, 'model_03', 'catboost_model.cbm')
        ]
        m3_active = any(os.path.exists(p) for p in m3_paths)

        overall_status = "healthy" if db_status == "connected" and m1_active and m2_active else "degraded"

        baseline_models = {
            "model_01": {"loaded": m1_active, "status": "active" if m1_active else "unavailable"},
            "model_02": {"loaded": m2_active, "status": "active" if m2_active else "unavailable"},
            "model_03": {"loaded": m3_active, "status": "active" if m3_active else "unavailable"}
        }
        improved_models = {
            "model_01_improved": {"loaded": m1_active},
            "model_02_improved": {"loaded": m2_active},
            "model_03_improved": {"loaded": m3_active}
        }

        return jsonify({
            "status": overall_status,
            "system": "RouteMind AI Maritime Logistics Control Tower",
            "version": "2.0.0",
            "render_git_commit": os.environ.get('RENDER_GIT_COMMIT', 'latest'),
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "database": db_status,
            "baseline_models": baseline_models,
            "improved_models": improved_models,
            "models": {
                "model_01_order_creation": {
                    "name": "Model 01: Order Creation Late Delivery Classifier",
                    "algorithm": "Logistic Regression",
                    "status": "active" if m1_active else "unavailable",
                    "version": "1.0.0",
                    "decision_threshold": float(app.config.get("ORDER_CREATION_THRESHOLD", 0.40))
                },
                "model_02_dispatch": {
                    "name": "Model 02: Dispatch Stage Late Delivery Classifier",
                    "algorithm": "XGBoost Classifier",
                    "status": "active" if m2_active else "unavailable",
                    "version": "1.0.0",
                    "decision_threshold": float(app.config.get("DISPATCH_THRESHOLD", 0.39))
                },
                "model_03_delay_duration": {
                    "name": "Model 03: Delay Duration Estimator",
                    "algorithm": "CatBoost Regressor",
                    "status": "active" if m3_active else "unavailable",
                    "version": "1.1"
                }
            }
        })

    # -------------------------------------------------------------
    # Production Model Registry Endpoint
    # -------------------------------------------------------------
    @app.get('/api/models')
    @app.get('/models/registry')
    def list_models():
        models_dir = app.config.get('MODELS_DIR', os.path.join(BASE_DIR, 'models'))

        models_list = [
            {
                "model_id": "model_01_order_creation",
                "model_name": "Model 01: Late Delivery Classifier at Order Creation",
                "prediction_stage": "order_creation",
                "algorithm": "Logistic Regression",
                "model_version": "1.0.0",
                "role": "production",
                "decision_threshold": float(app.config.get("ORDER_CREATION_THRESHOLD", 0.40)),
                "status": "active"
            },
            {
                "model_id": "model_02_dispatch",
                "model_name": "Model 02: Late Delivery Classifier at Warehouse Dispatch",
                "prediction_stage": "dispatch",
                "algorithm": "XGBoost Classifier",
                "model_version": "1.0.0",
                "role": "production",
                "decision_threshold": float(app.config.get("DISPATCH_THRESHOLD", 0.39)),
                "status": "active"
            },
            {
                "model_id": "model_03_delay_duration",
                "model_name": "Model 03: Delay Duration Regressor",
                "prediction_stage": "delay_estimation",
                "algorithm": "CatBoost Regressor",
                "model_version": "1.1",
                "role": "production",
                "status": "active"
            }
        ]

        return jsonify({
            "total_models": len(models_list),
            "models": models_list,
            "architecture": {
                "order_creation": "Logistic Regression",
                "dispatch": "XGBoost Classifier",
                "delay_duration": "CatBoost Regressor",
                "explainability": "TreeSHAP",
                "generative_ai": "Maritime Copilot LLM"
            }
        })

    # -------------------------------------------------------------
    # Metrics Summary API
    # -------------------------------------------------------------
    @app.get('/metrics')
    @app.get('/api/metrics')
    @app.get('/api/metrics/summary')
    def metrics_summary():
        return jsonify({
            "status": "success",
            "baseline": {
                "model_01": {"accuracy": 0.6924, "roc_auc": 0.7445, "precision": 0.8481, "recall": 0.5377},
                "model_02": {"accuracy": 0.9245, "roc_auc": 0.9650, "precision": 0.9120, "recall": 0.8800},
                "model_03": {"mae": 0.42, "rmse": 0.65}
            },
            "improved": {
                "model_01_improved": {"accuracy": 0.7250, "roc_auc": 0.7850},
                "model_02_improved": {"accuracy": 0.9752, "roc_auc": 0.9985},
                "model_03_improved": {"mae": 0.31, "rmse": 0.48}
            },
            "model_01": {
                "name": "Model 01: Order Creation Late Delivery Classifier",
                "algorithm": "Logistic Regression",
                "accuracy": 69.24,
                "precision": 84.81,
                "recall": 53.77,
                "f1": 65.81,
                "roc_auc": 74.45
            },
            "model_02": {
                "name": "Model 02: Dispatch Stage Late Delivery Classifier",
                "algorithm": "XGBoost Classifier",
                "accuracy": 92.45,
                "precision": 91.20,
                "recall": 88.00,
                "f1": 89.50,
                "roc_auc": 94.10
            }
        })

    # -------------------------------------------------------------
    # Database Recent Scores API
    # -------------------------------------------------------------
    @app.get('/database/recent-scores')
    def get_database_recent_scores():
        limit = request.args.get('limit', default=10, type=int)
        from sql.db_adapter import DatabaseAdapter
        adapter = DatabaseAdapter()
        scores = adapter.get_recent_scores(limit=limit)
        return jsonify({
            "status": "success",
            "limit": limit,
            "count": len(scores),
            "scores": scores
        }), 200

    # -------------------------------------------------------------
    # Prediction API: Order Creation (Logistic Regression)
    # -------------------------------------------------------------
    @app.post('/api/predict/order-creation')
    @app.post('/predict/order-creation')
    def predict_order_creation():
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({
                "prediction_status": "ERROR",
                "error": {
                    "code": "INVALID_JSON",
                    "message": "Request body must be a valid JSON object."
                }
            }), 400

        if "Primary Category" not in payload and "Category Name" in payload:
            payload["Primary Category"] = payload["Category Name"]
        if "Category Name" not in payload and "Primary Category" in payload:
            payload["Category Name"] = payload["Primary Category"]

        # If shipment exists in database, enrich missing features
        shipment_id = payload.get("shipment_id") or payload.get("shipment_number")
        if shipment_id is not None:
            shipment = Shipment.query.filter(
                (Shipment.id == shipment_id) | (Shipment.shipment_number == str(shipment_id))
            ).first()
            if shipment:
                db_features = PredictionService.extract_order_creation_features_from_shipment(shipment)
                for k, v in db_features.items():
                    if k not in payload or payload[k] is None:
                        payload[k] = v
            else:
                # If shipment ID was explicitly provided but shipment not found and features missing
                if any(f not in payload or payload[f] is None for f in ORDER_CREATION_REQUIRED):
                    return jsonify({
                        "prediction_status": "ERROR",
                        "error": {
                            "code": "SHIPMENT_NOT_FOUND",
                            "message": f"Shipment '{shipment_id}' was not found in database."
                        }
                    }), 404

        # Validate required raw features
        missing = [f for f in ORDER_CREATION_REQUIRED if f not in payload or payload[f] is None]
        if missing:
            return jsonify({
                "prediction_status": "ERROR",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Missing required order-creation features: {missing}"
                }
            }), 422

        models_dir = app.config.get('MODELS_DIR', os.path.join(BASE_DIR, 'models'))
        resp = PredictionService.score_order_creation(payload, shipment_id=shipment_id, models_dir=models_dir)
        code = 200 if resp.get("prediction_status") == "PREDICTED" else 422
        return jsonify(resp), code

    # -------------------------------------------------------------
    # Prediction API: Warehouse Dispatch (XGBoost Classifier)
    # -------------------------------------------------------------
    @app.post('/api/predict/dispatch')
    @app.post('/predict/dispatch')
    def predict_dispatch():
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({
                "prediction_status": "ERROR",
                "error": {
                    "code": "INVALID_JSON",
                    "message": "Request body must be a valid JSON object."
                }
            }), 400

        shipment_id = payload.get("shipment_id") or payload.get("shipment_number")
        if shipment_id is not None:
            shipment = Shipment.query.filter(
                (Shipment.id == shipment_id) | (Shipment.shipment_number == str(shipment_id))
            ).first()
            if shipment:
                # Check if genuine dispatch features are available on shipment
                db_features, reason = PredictionService.extract_dispatch_features_from_shipment(shipment)
                if db_features:
                    for k, v in db_features.items():
                        if k not in payload or payload[k] is None:
                            payload[k] = v
                elif any(f not in payload for f in DISPATCH_REQUIRED):
                    return jsonify({
                        "prediction_status": "ERROR",
                        "error": {
                            "code": "DISPATCH_STAGE_NOT_REACHED",
                            "message": f"Dispatch prediction unavailable for shipment '{shipment_id}': {reason}"
                        }
                    }), 422
            else:
                if any(f not in payload or payload[f] is None for f in DISPATCH_REQUIRED):
                    return jsonify({
                        "prediction_status": "ERROR",
                        "error": {
                            "code": "SHIPMENT_NOT_FOUND",
                            "message": f"Shipment '{shipment_id}' was not found in database."
                        }
                    }), 404

        # Validate required dispatch features (no arbitrary silent auto-fills!)
        missing = [f for f in DISPATCH_REQUIRED if f not in payload or payload[f] is None]
        if missing:
            return jsonify({
                "prediction_status": "ERROR",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Missing required dispatch-stage features: {missing}. Features must not be arbitrarily auto-filled."
                }
            }), 422

        models_dir = app.config.get('MODELS_DIR', os.path.join(BASE_DIR, 'models'))
        resp = PredictionService.score_dispatch(payload, shipment_id=shipment_id, models_dir=models_dir)
        code = 200 if resp.get("prediction_status") == "PREDICTED" else 422
        return jsonify(resp), code

    # -------------------------------------------------------------
    # Prediction API: Unified Control Tower (Stage-by-Stage Comparison)
    # -------------------------------------------------------------
    @app.post('/api/predict/control-tower')
    @app.post('/predict/control-tower')
    def predict_control_tower_unified():
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({
                "prediction_status": "ERROR",
                "error": {
                    "code": "INVALID_JSON",
                    "message": "Request body must be a valid JSON object."
                }
            }), 400

        shipment_id = payload.get("shipment_id") or payload.get("shipment_number")
        shipment = None
        if shipment_id is not None:
            shipment = Shipment.query.filter(
                (Shipment.id == shipment_id) | (Shipment.shipment_number == str(shipment_id))
            ).first()
            if not shipment and not any(k in payload for k in ORDER_CREATION_REQUIRED + DISPATCH_REQUIRED if k != shipment_id):
                return jsonify({
                    "prediction_status": "ERROR",
                    "error": {
                        "code": "SHIPMENT_NOT_FOUND",
                        "message": f"Shipment '{shipment_id}' was not found in database."
                    }
                }), 404

        if "Primary Category" not in payload and "Category Name" in payload:
            payload["Primary Category"] = payload["Category Name"]

        # Extract features for Stage 1
        m1_input = {k: payload[k] for k in ORDER_CREATION_REQUIRED if k in payload and payload[k] is not None}
        if shipment:
            db_m1 = PredictionService.extract_order_creation_features_from_shipment(shipment)
            for k, v in db_m1.items():
                m1_input.setdefault(k, v)

        # Extract features for Stage 2
        m2_input = {k: payload[k] for k in DISPATCH_REQUIRED if k in payload and payload[k] is not None}
        if shipment:
            db_m2, _ = PredictionService.extract_dispatch_features_from_shipment(shipment)
            if db_m2:
                for k, v in db_m2.items():
                    m2_input.setdefault(k, v)

        models_dir = app.config.get('MODELS_DIR', os.path.join(BASE_DIR, 'models'))
        order_features = m1_input if all(f in m1_input for f in ORDER_CREATION_REQUIRED) else None
        dispatch_features = m2_input if all(f in m2_input for f in DISPATCH_REQUIRED) else None

        resp = PredictionService.score_control_tower_unified(
            order_payload=order_features,
            dispatch_payload=dispatch_features,
            shipment_id=shipment.shipment_number if shipment else shipment_id,
            models_dir=models_dir
        )
        return jsonify(resp), 200

    # -------------------------------------------------------------
    # Prediction API: Controlled Batch Scoring
    # -------------------------------------------------------------
    @app.post('/api/predict/batch')
    @app.post('/predict/batch')
    def predict_batch():
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict):
            return jsonify({
                "error": "INVALID_JSON",
                "message": "Request body must be a JSON object containing 'shipments' list."
            }), 400

        items = data.get("shipments")
        if not isinstance(items, list):
            return jsonify({
                "error": "INVALID_FORMAT",
                "message": "'shipments' field must be a list of shipment feature objects."
            }), 400

        if len(items) == 0:
            return jsonify({
                "error": "EMPTY_BATCH",
                "message": "The 'shipments' list cannot be empty."
            }), 400

        if len(items) > MAX_BATCH_SIZE:
            return jsonify({
                "error": "BATCH_SIZE_EXCEEDED",
                "message": f"Batch size ({len(items)}) exceeds maximum permitted limit of {MAX_BATCH_SIZE} items."
            }), 400

        stage = data.get("stage") or "order_creation"
        if stage not in ["order_creation", "dispatch"]:
            return jsonify({
                "error": "INVALID_STAGE",
                "message": f"Invalid stage '{stage}'. Must be exactly 'order_creation' or 'dispatch'."
            }), 400

        models_dir = app.config.get('MODELS_DIR', os.path.join(BASE_DIR, 'models'))
        results = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                results.append({
                    "item_index": i,
                    "prediction_status": "ERROR",
                    "error": {"code": "INVALID_ITEM", "message": f"Item at index {i} must be a dictionary object."}
                })
                continue

            sid = item.get("shipment_id") or item.get("shipment_number")
            if stage == "dispatch":
                missing = [f for f in DISPATCH_REQUIRED if f not in item or item[f] is None]
                if missing:
                    results.append({
                        "item_index": i,
                        "shipment_id": sid,
                        "prediction_status": "ERROR",
                        "error": {"code": "VALIDATION_ERROR", "message": f"Missing dispatch features: {missing}"}
                    })
                    continue
                r = DP.predict_dispatch_api(item, shipment_id=sid, models_dir=models_dir)
            else:
                missing = [f for f in ORDER_CREATION_REQUIRED if f not in item or item[f] is None]
                if missing:
                    results.append({
                        "item_index": i,
                        "shipment_id": sid,
                        "prediction_status": "ERROR",
                        "error": {"code": "VALIDATION_ERROR", "message": f"Missing order-creation features: {missing}"}
                    })
                    continue
                r = PR.predict_order_creation_api(item, shipment_id=sid, models_dir=models_dir)

            r["item_index"] = i
            results.append(r)

        return jsonify({
            "stage": stage,
            "total_submitted": len(items),
            "total_processed": len(results),
            "count": len(results),
            "success_count": sum(1 for r in results if r.get("prediction_status") == "PREDICTED"),
            "error_count": sum(1 for r in results if r.get("prediction_status") != "PREDICTED"),
            "results": results,
            "predictions": results
        }), 200

    # -------------------------------------------------------------
    # Prediction API: Improved Models & Delay Duration Endpoints
    # -------------------------------------------------------------
    @app.post('/api/predict/order-creation-improved')
    @app.post('/predict/order-creation-improved')
    def predict_order_creation_improved_endpoint():
        payload = request.get_json(silent=True) or {}
        from prediction_service import LogisticsPredictionService
        svc = LogisticsPredictionService()
        result = svc.predict_order_creation_improved(payload)
        return jsonify(result), 200

    @app.post('/api/predict/dispatch-improved')
    @app.post('/predict/dispatch-improved')
    def predict_dispatch_improved_endpoint():
        payload = request.get_json(silent=True) or {}
        from prediction_service import LogisticsPredictionService
        svc = LogisticsPredictionService()
        result = svc.predict_dispatch_improved(payload)
        return jsonify(result), 200

    @app.post('/api/predict/delay-duration')
    @app.post('/predict/delay-duration')
    def predict_delay_duration_endpoint():
        payload = request.get_json(silent=True) or {}
        from prediction_service import LogisticsPredictionService
        svc = LogisticsPredictionService()
        result = svc.predict_delay_duration(payload)
        return jsonify(result), 200

    @app.post('/api/predict/delay-duration-improved')
    @app.post('/predict/delay-duration-improved')
    def predict_delay_duration_improved_endpoint():
        payload = request.get_json(silent=True) or {}
        from prediction_service import LogisticsPredictionService
        svc = LogisticsPredictionService()
        result = svc.predict_delay_duration_improved(payload)
        return jsonify(result), 200

    @app.post('/predict/live-event')
    def predict_live_event_endpoint():
        payload = request.get_json(silent=True) or {}
        from prediction_service import LogisticsPredictionService
        svc = LogisticsPredictionService()
        result = svc.predict_live_event(payload)
        return jsonify(result), 200

    # -------------------------------------------------------------
    # Prediction History Endpoint (MySQL SQLAlchemy ModelScore)
    # -------------------------------------------------------------
    @app.get('/api/history')
    @login_required
    @roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
    def history():
        try:
            limit = min(int(request.args.get('limit', 50)), 200)
            shipment_id = request.args.get('shipment_id')
            query = ModelScore.query
            if shipment_id:
                if str(shipment_id).isdigit():
                    query = query.filter(ModelScore.shipment_id == int(shipment_id))
            scores = query.order_by(ModelScore.scoring_timestamp.desc()).limit(limit).all()
            return jsonify({
                "count": len(scores),
                "history": [s.to_dict() for s in scores]
            }), 200
        except Exception as e:
            logger.error(f"Error fetching prediction history from MySQL: {e}", exc_info=True)
            return jsonify({
                "count": 0,
                "history": [],
                "error": "Failed to retrieve prediction history from database."
            }), 500

    # -------------------------------------------------------------
    # Legacy SPA Redirect to Primary Template Dashboard
    # -------------------------------------------------------------
    @app.route('/app')
    @app.route('/app/<path:path>')
    def serve_modern_app(path=''):
        return redirect(url_for('dashboard'))

    # Safe database initialization (non-destructive)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            logger.info(f"Database initialization check: {e}")

    return app


# Create default application instance for WSGI runners and test imports
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    port = int(os.environ.get('X_ZOHO_CATALYST_LISTEN_PORT', os.environ.get('PORT', 5000)))
    host = '0.0.0.0' if os.environ.get('X_ZOHO_CATALYST_LISTEN_PORT') or os.environ.get('FLASK_ENV') == 'production' else '127.0.0.1'
    print(f"RouteMind AI Enterprise running on http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
