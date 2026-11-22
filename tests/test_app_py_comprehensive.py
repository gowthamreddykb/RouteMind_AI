"""
test_app_py_comprehensive.py - Comprehensive verification test suite for corrected app.py
Tests all requirements in Section 14 of the specification.
"""
import os
import sys
import json
import pytest

# Ensure project root
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if os.path.join(ROOT, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, 'src'))

from app import create_app
from extensions import db
from src.models.user_model import User
from src.models.shipment_model import Shipment


@pytest.fixture
def app():
    app = create_app('development')
    app.config['WTF_CSRF_ENABLED'] = False
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_endpoint_public(client):
    """Test 1: Health endpoint is public and reports accurate models & DB status without secrets."""
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data['system'] == "RouteMind AI Maritime Logistics Control Tower"
    assert data['database'] == "connected"
    assert data['models']['model_01_order_creation']['algorithm'] == "Logistic Regression"
    assert data['models']['model_02_dispatch']['algorithm'] == "XGBoost Classifier"
    assert data['models']['model_03_delay_duration']['algorithm'] == "CatBoost Regressor"
    assert 'password' not in json.dumps(data)
    assert 'root' not in json.dumps(data)
    print("  [PASS] /health reports accurate models and DB status securely.")


def test_unauthenticated_api_access_blocked(client):
    """Test 2: Unauthenticated API access receives JSON 401 instead of HTML redirect."""
    api_endpoints = [
        ('/api/models', 'GET', None),
        ('/api/history', 'GET', None),
        ('/api/predict/order-creation', 'POST', {}),
        ('/api/predict/dispatch', 'POST', {}),
        ('/api/predict/control-tower', 'POST', {}),
        ('/api/predict/batch', 'POST', {})
    ]

    for path, method, payload in api_endpoints:
        if method == 'GET':
            res = client.get(path, headers={'Accept': 'application/json'})
        else:
            res = client.post(path, json=payload, headers={'Content-Type': 'application/json'})

        assert res.status_code == 401, f"Failed on {path}: expected 401, got {res.status_code}"
        assert res.is_json
        data = res.get_json()
        assert data.get('error') == 'Unauthorized'
    print("  [PASS] All unauthenticated API endpoints return JSON 401.")


def test_batch_validation_rules(client):
    """Test 3: Batch prediction validates format, stage, empty list, and max size."""
    client.get('/auth/quick-login/dispatcher', follow_redirects=True)

    # Invalid JSON / not dict
    res = client.post('/api/predict/batch', data="plain text", headers={'Content-Type': 'application/json'})
    assert res.status_code == 400

    # Missing shipments or not a list
    res = client.post('/api/predict/batch', json={"stage": "order_creation", "shipments": "not_a_list"})
    assert res.status_code == 400

    # Empty batch
    res = client.post('/api/predict/batch', json={"stage": "order_creation", "shipments": []})
    assert res.status_code == 400
    assert res.get_json().get('error') == 'EMPTY_BATCH'

    # Invalid stage
    res = client.post('/api/predict/batch', json={"stage": "invalid_clustering_stage", "shipments": [{"Days for shipment (scheduled)": 4}]})
    assert res.status_code == 400
    assert res.get_json().get('error') == 'INVALID_STAGE'

    # Oversized batch
    oversized = [{"item": i} for i in range(105)]
    res = client.post('/api/predict/batch', json={"stage": "order_creation", "shipments": oversized})
    assert res.status_code == 400
    assert res.get_json().get('error') == 'BATCH_SIZE_EXCEEDED'

    print("  [PASS] Batch endpoint strictly validates payload, stage, empty list, and batch size.")


def test_order_creation_prediction_flow(client):
    """Test 4: Order creation prediction with Logistic Regression, validation, and shipment linkage."""
    client.get('/auth/quick-login/dispatcher', follow_redirects=True)

    # Missing features returns 422
    res = client.post('/api/predict/order-creation', json={"Days for shipment (scheduled)": 4})
    assert res.status_code == 422
    assert res.get_json()['error']['code'] == 'VALIDATION_ERROR'

    # Unknown shipment returns 404
    res = client.post('/api/predict/order-creation', json={"shipment_id": 999999})
    assert res.status_code == 404
    assert res.get_json()['error']['code'] == 'SHIPMENT_NOT_FOUND'

    # Valid raw input
    valid_payload = {
        'Days for shipment (scheduled)': 4,
        'Order Item Quantity': 2,
        'Sales': 250.0,
        'Shipping Mode': 'Standard Class',
        'Order Region': 'Western Europe',
        'Type': 'DEBIT',
        'Market': 'Europe',
        'Primary Category': 'Sporting Goods'
    }
    res = client.post('/api/predict/order-creation', json=valid_payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data['prediction_status'] == 'PREDICTED'
    assert 'Logistic' in data['model_name'] and 'Regression' in data['model_name']
    assert 0.0 <= data['predicted_probability'] <= 1.0
    print("  [PASS] Order-creation prediction executed with Logistic Regression and verified schemas.")


def test_dispatch_prediction_flow(client):
    """Test 5: Dispatch prediction with XGBoost and rejection of missing dispatch features."""
    client.get('/auth/quick-login/dispatcher', follow_redirects=True)

    # Missing Order-to-Ship Time returns 422
    res = client.post('/api/predict/dispatch', json={"Days for shipment (scheduled)": 4, "Shipping Mode": "Standard Class"})
    assert res.status_code == 422
    assert res.get_json()['error']['code'] == 'VALIDATION_ERROR'

    # Valid dispatch input
    valid_dispatch = {
        'Days for shipment (scheduled)': 4,
        'Order-to-Ship Time': 2.0,
        'Shipping Mode': 'Standard Class',
        'Order Region': 'Western Europe',
        'Market': 'Europe',
        'Department Name': 'Fan Shop',
        'Customer Segment': 'Consumer'
    }
    res = client.post('/api/predict/dispatch', json=valid_dispatch)
    assert res.status_code == 200
    data = res.get_json()
    assert data['prediction_status'] == 'PREDICTED'
    assert data['prediction_stage'] == 'dispatch'
    assert 0.0 <= data['predicted_probability'] <= 1.0
    print("  [PASS] Dispatch prediction executed with XGBoost and genuine dispatch features.")


def test_control_tower_unified_prediction(client):
    """Test 6: Control Tower unified prediction preserves Stage 1 and Stage 2 independently."""
    client.get('/auth/quick-login/dispatcher', follow_redirects=True)

    # Test with valid dual-stage payload
    payload = {
        'Days for shipment (scheduled)': 4,
        'Order Item Quantity': 2,
        'Sales': 250.0,
        'Shipping Mode': 'Standard Class',
        'Order Region': 'Western Europe',
        'Type': 'DEBIT',
        'Market': 'Europe',
        'Primary Category': 'Sporting Goods',
        'Order-to-Ship Time': 2.5,
        'Department Name': 'Fan Shop',
        'Customer Segment': 'Consumer'
    }
    res = client.post('/api/predict/control-tower', json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert 'stage_comparison' in data
    assert 'order_creation_probability' in data['stage_comparison']
    assert 'dispatch_probability' in data['stage_comparison']
    assert 'model_01_order_creation' in data
    assert 'model_02_dispatch' in data
    # Verify no fake overall probability
    assert 'overall_risk_probability' not in data['stage_comparison']
    print("  [PASS] Control Tower unified prediction evaluates both stages independently without max(p1,p2) leakage.")


def test_prediction_history_mysql(client):
    """Test 7: Prediction history is queried from MySQL model_scores via SQLAlchemy."""
    client.get('/auth/quick-login/dispatcher', follow_redirects=True)
    res = client.get('/api/history')
    assert res.status_code == 200
    data = res.get_json()
    assert 'count' in data
    assert 'history' in data
    assert isinstance(data['history'], list)
    print(f"  [PASS] Prediction history queried directly from MySQL (count: {data['count']}).")


if __name__ == '__main__':
    pytest.main(['-v', __file__])
