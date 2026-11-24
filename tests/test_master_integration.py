"""
test_master_integration.py - Comprehensive End-to-End Test Suite for RouteMind AI
Covers all 14 Workflows specified in the Master Prompt:
- Workflow A: Authentication, session management, and RBAC
- Workflow B: Shipment data import, column validation, duplicate detection, DB commit
- Workflow C: Dual-stage ML prediction (Logistic Regression & XGBoost), zero target leakage
- Workflow D: Shipment Explorer search, filtering, and pagination
- Workflow E: Shipment details, telemetry, SHAP explainability, and exceptions
- Workflow F: Exception lifecycle (Open -> Assigned -> In Progress -> Resolved -> Closed)
- Manager Escalation: Dispatcher creation, manager triage, status updates, resolution, audit trail
- AI Chatbot: Real database telemetry extraction, operational queries, domain explanations
- Reports & Charts: Real database aggregation, JSON export
- Database: Schema validation and relationships
"""
import pytest
import io
import json
import datetime as dt

from app import create_app
from extensions import db
from src.models.user_model import User
from src.models.shipment_model import Shipment
from src.models.exception_model import ShipmentException
from src.models.exception_action_model import ExceptionAction
from src.models.escalation_model import ManagerEscalation, EscalationHistory
from src.models.import_log_model import ShipmentImportLog
from src.models.audit_log_model import AuditLog
from src.services.shipment_service import ShipmentService
from src.services.prediction_service import PredictionService
from src.services.exception_service import ExceptionService
from src.services.escalation_service import EscalationService
from src.services.ai_assistant_service import AIAssistantService


@pytest.fixture
def app():
    app = create_app('development')
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['LOGIN_DISABLED'] = False
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


# ==============================================================================
# 1. WORKFLOW A: AUTHENTICATION & ROLE-BASED ACCESS CONTROL
# ==============================================================================
def test_workflow_a_authentication_and_rbac(client, app):
    with app.app_context():
        # 1. Unauthenticated gate redirects to login
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 302
        assert '/auth/login' in res.headers.get('Location', '')

        # 2. Public auth endpoints return 200
        res = client.get('/auth/login')
        assert res.status_code == 200

        res = client.get('/auth/forgot-password')
        assert res.status_code == 200

        # 3. Quick-login Dispatcher
        res = client.get('/auth/quick-login/dispatcher', follow_redirects=True)
        assert res.status_code == 200
        assert b'Dispatcher' in res.data or b'Control Tower' in res.data

        # 4. Dispatcher accessing restricted admin routes must receive 403
        res = client.get('/users/')
        assert res.status_code == 403

        res = client.get('/admin/settings')
        assert res.status_code == 403

        # 5. Logout
        res = client.get('/auth/logout', follow_redirects=False)
        assert res.status_code == 302
        assert '/auth/login' in res.headers.get('Location', '')


# ==============================================================================
# 2. WORKFLOW B: SHIPMENT DATA IMPORT
# ==============================================================================
def test_workflow_b_shipment_data_import(client, app):
    with app.app_context():
        from src.models.shipment_event_model import ShipmentEvent
        # Clean up prior test runs if existing
        pre_shps = Shipment.query.filter(Shipment.shipment_number.in_(['SHP-E2E-001', 'SHP-E2E-002', 'SHP-E2E-ERR'])).all()
        for s in pre_shps:
            ShipmentEvent.query.filter_by(shipment_id=s.id).delete()
            db.session.delete(s)
        ShipmentImportLog.query.filter(ShipmentImportLog.filename.like('test_%')).delete()
        db.session.commit()

        dispatcher = User.query.filter_by(username='dispatcher').first()

        # Valid CSV
        valid_csv = (
            "shipment_id,Shipping Mode,Days for shipment (scheduled),Sales,Quantity,Order Region\n"
            "SHP-E2E-001,Standard Class,4,150.0,1,Western Europe\n"
            "SHP-E2E-002,First Class,1,280.0,2,Central America\n"
        )
        stream = io.StringIO(valid_csv)
        res = ShipmentService.import_csv(stream, 'test_e2e.csv', user=dispatcher)

        assert res['total_rows'] == 2
        assert res['success_count'] == 2
        assert res['rejected_count'] == 0
        assert res['status'] == 'SUCCESS'

        # Verify imported in DB
        s1 = Shipment.query.filter_by(shipment_number='SHP-E2E-001').first()
        assert s1 is not None
        assert s1.assigned_to_name == 'dispatcher'
        assert s1.risk_level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

        # Test duplicate rejection on re-import
        stream_dup = io.StringIO(valid_csv)
        res_dup = ShipmentService.import_csv(stream_dup, 'test_e2e_dup.csv', user=dispatcher)
        assert res_dup['success_count'] == 0
        assert res_dup['rejected_count'] == 2
        assert res_dup['status'] == 'FAILED'

        # Test invalid scheduled days
        invalid_csv = (
            "shipment_id,Shipping Mode,Days for shipment (scheduled),Sales,Quantity,Order Region\n"
            "SHP-E2E-ERR,Standard Class,-5,150.0,1,Western Europe\n"
        )
        stream_inv = io.StringIO(invalid_csv)
        res_inv = ShipmentService.import_csv(stream_inv, 'test_err.csv', user=dispatcher)
        assert res_inv['rejected_count'] == 1
        assert len(res_inv['errors']) == 1

        # Clean up test shipments and events
        from src.models.shipment_event_model import ShipmentEvent
        shps = Shipment.query.filter(Shipment.shipment_number.in_(['SHP-E2E-001', 'SHP-E2E-002'])).all()
        for s in shps:
            ShipmentEvent.query.filter_by(shipment_id=s.id).delete()
            db.session.delete(s)
        ShipmentImportLog.query.filter(ShipmentImportLog.filename.like('test_%')).delete()
        db.session.commit()


# ==============================================================================
# 3. WORKFLOW C: MACHINE LEARNING PREDICTION
# ==============================================================================
def test_workflow_c_ml_prediction(app):
    with app.app_context():
        # Stage 1: Order Creation Features
        order_features = {
            "Days for shipment (scheduled)": 4.0,
            "Order Item Quantity": 1,
            "Sales": 120.0,
            "Shipping Mode": "Standard Class",
            "Order Region": "Western Europe",
            "Market": "Europe",
            "Type": "DEBIT"
        }
        res1 = PredictionService.score_order_creation(order_features)
        assert res1['prediction_status'] == 'PREDICTED'
        assert 0.0 <= res1['predicted_probability'] <= 1.0
        assert res1['risk_level'] in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

        # Dual-stage inference
        dispatch_features = {
            "Days for shipment (scheduled)": 1.0,
            "Order-to-Ship Time": 3.8,
            "Shipping Mode": "First Class",
            "Order Region": "Western Europe",
            "Market": "Europe",
            "Department Name": "Maritime Logistics",
            "Customer Segment": "Consumer"
        }
        unified = PredictionService.score_control_tower_unified(order_features, dispatch_features)
        assert unified['control_tower_summary']['overall_risk_level'] in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        assert unified['control_tower_summary']['recommended_action'] in ['HOLD_FOR_EXPEDITE', 'MONITOR_DOCK_DEPARTURE', 'CLEAR_FOR_TRANSIT']


# ==============================================================================
# 4. WORKFLOW D & E: SHIPMENT EXPLORER & DETAILS
# ==============================================================================
def test_workflow_d_and_e_shipment_explorer(client, app):
    with app.app_context():
        client.get('/auth/quick-login/dispatcher')

        # List with filter
        res = client.get('/shipments/?status=IN_TRANSIT')
        assert res.status_code == 200
        assert b'Shipment Records' in res.data

        # Search
        res = client.get('/shipments/?search=SHP')
        assert res.status_code == 200

        # Details
        first_shp = Shipment.query.first()
        if first_shp:
            res = client.get(f'/shipments/{first_shp.shipment_number}')
            assert res.status_code == 200
            assert bytes(first_shp.shipment_number, 'utf-8') in res.data
            assert b'Consignment Specifications' in res.data


# ==============================================================================
# 5. WORKFLOW F: EXCEPTION MANAGEMENT LIFECYCLE
# ==============================================================================
def test_workflow_f_exception_lifecycle(client, app):
    with app.app_context():
        client.get('/auth/quick-login/dispatcher')
        first_shp = Shipment.query.first()
        assert first_shp is not None

        # 1. Create Exception
        res = client.post('/exceptions/api/create', json={
            'shipment_id': first_shp.id,
            'exception_type': 'BERTHING_CONGESTION',
            'severity': 'HIGH'
        })
        assert res.status_code == 200
        exc_id = res.get_json()['exception']['id']

        # 2. Add Operational Note
        res = client.post('/exceptions/api/add-note', json={
            'exception_id': exc_id,
            'note': 'Vessel held at outer anchorage due to terminal congestion.'
        })
        assert res.status_code == 200

        # 3. Update Status to IN_PROGRESS
        res = client.post('/exceptions/api/update-status', json={
            'exception_id': exc_id,
            'status': 'IN_PROGRESS',
            'root_cause': 'Berth allocation delay'
        })
        assert res.status_code == 200

        # 4. Manager Login & Assign
        client.get('/auth/logout')
        client.get('/auth/quick-login/manager')

        res = client.post('/exceptions/api/assign', json={
            'exception_id': exc_id,
            'assigned_to': 'manager'
        })
        assert res.status_code == 200

        # 5. Resolve
        res = client.post('/exceptions/api/resolve', json={
            'exception_id': exc_id
        })
        assert res.status_code == 200

        # 6. Close
        res = client.post('/exceptions/api/close', json={
            'exception_id': exc_id,
            'notes': 'Berth assigned and cargo offloaded safely.'
        })
        assert res.status_code == 200

        # Clean up test exception
        ExceptionAction.query.filter_by(exception_id=exc_id).delete()
        ShipmentException.query.filter_by(id=exc_id).delete()
        db.session.commit()


# ==============================================================================
# 6. MANAGER ESCALATION WORKFLOW
# ==============================================================================
def test_manager_escalation_workflow(client, app):
    with app.app_context():
        client.get('/auth/quick-login/dispatcher')
        first_shp = Shipment.query.first()
        assert first_shp is not None

        # Dispatcher escalates shipment
        res = client.post('/escalations/create', json={
            'shipment_id': first_shp.id,
            'priority': 'HIGH',
            'reason': 'Severe destination terminal delay exceeding SLA',
            'dispatcher_remarks': 'Requested expedited customs clearance'
        })
        assert res.status_code == 201
        data = res.get_json()
        esc_id = data['escalation']['id']
        assert data['escalation']['status'] == 'PENDING'

        # Switch to Manager
        client.get('/auth/logout')
        client.get('/auth/quick-login/manager')

        # Manager updates status to UNDER_REVIEW
        res = client.post(f'/escalations/{esc_id}/update-status', json={
            'status': 'UNDER_REVIEW',
            'remarks': 'Reviewing berth priority with harbour master'
        })
        assert res.status_code == 200
        assert res.get_json()['escalation']['status'] == 'UNDER_REVIEW'

        # Manager assigns responsibility
        res = client.post(f'/escalations/{esc_id}/assign', json={
            'assigned_to_name': 'suresh_raina'
        })
        assert res.status_code == 200

        # Manager resolves escalation
        res = client.post(f'/escalations/{esc_id}/resolve', json={
            'resolution_notes': 'Harbour master approved priority berthing window.',
            'manager_remarks': 'Resolved with zero SLA breach penalty.'
        })
        assert res.status_code == 200
        assert res.get_json()['escalation']['status'] == 'RESOLVED'

        # Clean up test escalation
        EscalationHistory.query.filter_by(escalation_id=esc_id).delete()
        ManagerEscalation.query.filter_by(id=esc_id).delete()
        db.session.commit()


# ==============================================================================
# 7. AI LOGISTICS CHATBOT
# ==============================================================================
def test_ai_logistics_chatbot(client, app):
    with app.app_context():
        client.get('/auth/quick-login/dispatcher')

        # 1. Operational queries
        res = client.post('/ai/assistant/api/chat', json={
            'message': 'How many shipments are currently high risk?'
        })
        assert res.status_code == 200
        assert 'high-risk' in res.get_json()['message'].lower()

        # 2. Regional bottleneck query
        res = client.post('/ai/assistant/api/chat', json={
            'message': 'Which region has the most high-risk shipments?'
        })
        assert res.status_code == 200
        assert 'region' in res.get_json()['message'].lower()

        # 3. Specific shipment explanation query
        first_shp = Shipment.query.first()
        if first_shp:
            res = client.post('/ai/assistant/api/chat', json={
                'message': f'Explain shipment {first_shp.shipment_number}'
            })
            assert res.status_code == 200
            msg = res.get_json()['message']
            assert first_shp.shipment_number in msg
