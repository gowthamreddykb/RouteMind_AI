"""
test_dashboard_charts.py - Comprehensive Unit & Integration Tests for Dashboard Charts
Tests all 4 Control Tower charts:
1. Shipment Volume by Destination Region (Vertical Bar)
2. Shipment Status Overview (Horizontal Bar)
3. Shipment Risk Distribution (Vertical Bar - Overall)
4. Exception Analysis by Priority (Horizontal Bar - Preserved)
"""
import pytest
import datetime as dt
from app import create_app
from extensions import db
from src.services.dashboard_service import DashboardService, LIFECYCLE_KEYS
from src.models.shipment_model import Shipment
from src.models.model_score_model import ModelScore
from src.models.exception_model import ShipmentException
from src.models.user_model import User


@pytest.fixture
def app_instance():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Seed test user
        user = User.query.filter_by(username='dispatcher_test').first()
        if not user:
            user = User(
                username='dispatcher_test',
                email='dispatcher_test@routemind.ai',
                role='DISPATCHER',
                full_name='Test Dispatcher'
            )
            user.set_password('password123')
            db.session.add(user)

        # Seed sample shipments for all 9 statuses, destination regions and risk levels
        s1 = Shipment(
            shipment_number='TEST-SHP-001',
            order_status='IN_TRANSIT',
            destination_region='Western Europe',
            order_date=dt.datetime(2026, 11, 10, 10, 0, 0),
            scheduled_days=4,
            risk_level='LOW',
            order_creation_prob=0.15,
            dispatch_prob=0.20
        )
        s2 = Shipment(
            shipment_number='TEST-SHP-002',
            order_status='DELIVERED',
            destination_region='Western Europe',
            order_date=dt.datetime(2026, 11, 5, 10, 0, 0),
            scheduled_days=3,
            actual_arrival=dt.datetime(2026, 11, 7, 14, 0, 0),
            risk_level='LOW'
        )
        s3 = Shipment(
            shipment_number='TEST-SHP-003',
            order_status='COMPLETED',
            destination_region='Central America',
            order_date=dt.datetime(2026, 11, 1, 10, 0, 0),
            scheduled_days=2,
            actual_arrival=dt.datetime(2026, 11, 6, 12, 0, 0),
            risk_level='HIGH'
        )
        s4 = Shipment(
            shipment_number='TEST-SHP-004',
            order_status='CREATED',
            destination_region='Middle East',
            order_date=dt.datetime(2026, 11, 20, 10, 0, 0),
            scheduled_days=5,
            risk_level='HIGH',
            order_creation_prob=0.88,
            dispatch_prob=0.92
        )
        db.session.add_all([s1, s2, s3, s4])
        db.session.flush()

        # Seed ModelScores for s1 and s4
        score1 = ModelScore(
            shipment_id=s1.id,
            model_id=1,
            prediction_stage='STAGE_1_ORDER_CREATION',
            predicted_probability=0.15,
            predicted_class=0,
            risk_level='LOW'
        )
        score2 = ModelScore(
            shipment_id=s4.id,
            model_id=2,
            prediction_stage='STAGE_2_WAREHOUSE_DISPATCH',
            predicted_probability=0.92,
            predicted_class=1,
            risk_level='HIGH'
        )
        db.session.add_all([score1, score2])

        # Seed Exceptions
        e1 = ShipmentException(
            shipment_id=s1.id,
            exception_type='Port Congestion',
            severity='CRITICAL',
            status='OPEN'
        )
        e2 = ShipmentException(
            shipment_id=s4.id,
            exception_type='Customs Hold',
            severity='HIGH',
            status='RESOLVED'
        )
        db.session.add_all([e1, e2])
        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()


def test_chart_1_shipment_volume_by_destination_region(app_instance):
    """Test Chart 1: Vertical bar chart, grouped by destination region, clickable bars."""
    with app_instance.app_context():
        res = DashboardService.get_shipment_volume_by_destination_region()
        assert res['chart_type'] == 'bar'
        assert res['title'] == 'Shipment Volume by Destination Region'
        assert res['total_shipments'] == 4
        # Regions: Western Europe (2), Central America (1), Middle East (1)
        assert len(res['labels']) == 3
        assert 'Western Europe' in res['labels']
        assert 'Central America' in res['labels']
        assert 'Middle East' in res['labels']
        # Western Europe should be first (sorted descending)
        assert res['labels'][0] == 'Western Europe'
        assert res['counts'][0] == 2
        # Sum of counts equals total shipments
        assert sum(res['counts']) == 4
        # Percentages
        assert res['percentages'][0] == 50.0
        # Filter urls check
        assert any('Western+Europe' in u or 'Western%20Europe' in u for u in res['filter_urls'])


def test_chart_2_shipment_status_overview(app_instance):
    """Test Chart 2: Horizontal bar chart, all 9 lifecycle statuses, counts displayed beside bars."""
    with app_instance.app_context():
        res = DashboardService.get_shipment_status_overview()
        assert res['chart_type'] == 'horizontalBar'
        assert res['title'] == 'Shipment Status Overview'
        assert res['total_shipments'] == 4
        assert len(res['labels']) == 9
        assert len(res['status_codes']) == 9
        assert set(res['status_codes']) == set(LIFECYCLE_KEYS)
        # Sum of counts equals total shipments
        assert sum(res['counts']) == 4
        assert res['counts'][res['status_codes'].index('IN_TRANSIT')] == 1
        assert res['counts'][res['status_codes'].index('DELIVERED')] == 1
        assert res['counts'][res['status_codes'].index('COMPLETED')] == 1
        assert res['counts'][res['status_codes'].index('CREATED')] == 1
        # Percentages check
        assert sum(res['percentages']) == 100.0
        # Filter urls check
        assert res['filter_urls'][res['status_codes'].index('IN_TRANSIT')] == '/shipments/?status=IN_TRANSIT'


def test_chart_3_shipment_risk_distribution_overall(app_instance):
    """Test Chart 3: Vertical bar chart, overall active shipments risk, single assessment."""
    with app_instance.app_context():
        # Active shipments are s1 and s4 (s2 and s3 are DELIVERED/COMPLETED)
        res = DashboardService.get_shipment_risk_distribution()
        assert res['chart_type'] == 'bar'
        assert res['title'] == 'Shipment Risk Distribution'
        assert res['total_active'] == 2
        assert res['labels'] == ['Low Risk', 'Medium Risk', 'High Risk']
        # s1 is LOW, s4 is HIGH
        assert res['counts'] == [1, 0, 1]
        assert res['percentages'] == [50.0, 0.0, 50.0]
        # Filter urls check
        assert res['filter_urls'] == [
            '/shipments/?risk=Low+Risk',
            '/shipments/?risk=Medium+Risk',
            '/shipments/?risk=High+Risk'
        ]


def test_chart_4_exception_priority_analysis(app_instance):
    """Test Chart 4: Horizontal bar chart, Low/Med/High/Urgent, filterable by status."""
    with app_instance.app_context():
        # All exceptions
        res_all = DashboardService.get_exception_priority_analysis(status_filter='ALL')
        assert res_all['chart_type'] == 'horizontalBar'
        assert res_all['total_exceptions'] == 2
        assert res_all['labels'] == ['Low', 'Medium', 'High', 'Urgent']
        # e1 is CRITICAL -> Urgent (1), e2 is HIGH -> High (1)
        assert res_all['counts'] == [0, 0, 1, 1]

        # Filter by OPEN only
        res_open = DashboardService.get_exception_priority_analysis(status_filter='OPEN')
        assert res_open['total_exceptions'] == 1
        assert res_open['counts'] == [0, 0, 0, 1]

        # Filter by RESOLVED only
        res_res = DashboardService.get_exception_priority_analysis(status_filter='RESOLVED')
        assert res_res['total_exceptions'] == 1
        assert res_res['counts'] == [0, 0, 1, 0]


def test_dashboard_charts_api_endpoints(app_instance):
    """Test authorized API routes returning chart payloads."""
    client = app_instance.test_client()
    with app_instance.app_context():
        user = User.query.filter_by(username='dispatcher_test').first()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    # 1. Full payload endpoint
    resp = client.get('/api/dashboard/charts')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    assert 'destination_volume' in data['charts']
    assert 'status_overview' in data['charts']
    assert 'risk_distribution' in data['charts']
    assert 'exception_priority' in data['charts']

    # 2. Individual chart endpoints
    r1 = client.get('/api/dashboard/chart/destination_volume')
    assert r1.status_code == 200
    assert r1.get_json()['chart']['chart_id'] == 'shipment_destination_volume'

    r2 = client.get('/api/dashboard/chart/status_overview')
    assert r2.status_code == 200
    assert r2.get_json()['chart']['chart_id'] in ['shipment_status_overview', 'shipment_status_distribution']

    r3 = client.get('/api/dashboard/chart/risk_distribution')
    assert r3.status_code == 200
    assert r3.get_json()['chart']['chart_id'] == 'shipment_risk_distribution'

    r4 = client.get('/api/dashboard/chart/exception_priority?status=OPEN')
    assert r4.status_code == 200
    assert r4.get_json()['chart']['status_filter'] == 'OPEN'
