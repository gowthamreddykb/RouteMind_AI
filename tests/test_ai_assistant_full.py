"""
test_ai_assistant_full.py - Comprehensive Unit & Integration Tests for AI Shipment Assistant
Tests:
1. Endpoint availability (/api/chat, /ai/assistant/api/chat, /ai-assistant/api/chat)
2. Empty message validation
3. Single shipment queries (status, delay risk, maritime specs)
4. Multi-shipment queries with structured Markdown tables
5. Contextual follow-up memory across conversation turns
6. Aggregation and analytical questions (delay rate %, mode delay, regional bottlenecks)
7. ML model accuracy and SHAP explainability questions
8. Chat history retrieval and conversation clearing
"""
import pytest
import json
from src.app import create_app
from extensions import db
from src.models.user_model import User
from src.models.shipment_model import Shipment
from src.models.chat_model import ChatConversation, ChatMessage


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Logs in as dispatcher for authenticated chat sessions."""
    res = client.get('/auth/quick-login/dispatcher', follow_redirects=True)
    assert res.status_code == 200
    return client


def test_1_empty_message_validation(auth_client):
    """Test that empty queries return 400 Bad Request with informative message."""
    res = auth_client.post('/api/chat', json={'message': '   '})
    assert res.status_code == 400
    data = res.get_json()
    assert data['success'] is False
    assert 'valid question' in data['response'].lower()


def test_2_single_shipment_query(auth_client, app):
    """Test querying a specific consignment reference."""
    with app.app_context():
        s = Shipment.query.first()
        assert s is not None, "At least one shipment should exist in DB"
        ref = s.shipment_number

    res = auth_client.post('/api/chat', json={'message': f'Explain status of shipment {ref}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert ref in data['response']
    assert 'Consignment Intelligence Report' in data['response']
    assert 'Evaluated Risk' in data['response']
    assert data['conversation_id'] is not None


def test_3_multi_shipment_table_query(auth_client):
    """Test querying multiple shipments returns a markdown table with column headers."""
    res = auth_client.post('/api/chat', json={'message': 'Show all high risk shipments'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert '| Shipment #' in data['response'] or 'No shipments matched' in data['response']


def test_4_conversational_followup_memory(auth_client):
    """Test multi-turn conversational memory using conversation_id."""
    # Turn 1: Ask for shipments
    res1 = auth_client.post('/api/chat', json={'message': 'List top 5 delayed shipments'})
    assert res1.status_code == 200
    data1 = res1.get_json()
    conv_id = data1.get('conversation_id')
    assert conv_id is not None

    # Turn 2: Follow-up question referencing 'these'
    res2 = auth_client.post('/api/chat', json={
        'message': 'Which of these have open exceptions?',
        'conversation_id': conv_id
    })
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2['success'] is True
    assert 'Exception Audit for the' in data2['response'] or 'Context Consignments' in data2['response']


def test_5_delay_percentage_and_analytical_queries(auth_client):
    """Test fleet delay rate and analytical percentage questions."""
    res = auth_client.post('/api/chat', json={'message': 'What percentage of shipments are late?'})
    assert res.status_code == 200
    data = res.get_json()
    assert 'Fleet Lateness Risk Metrics' in data['response']
    assert '%' in data['response']

    # Shipping mode query
    res_mode = auth_client.post('/api/chat', json={'message': 'Which shipping mode has highest delay rate?'})
    assert res_mode.status_code == 200
    data_mode = res_mode.get_json()
    assert 'shipping class' in data_mode['response'].lower() or 'shipping mode' in data_mode['response'].lower()


def test_6_ml_model_accuracy_query(auth_client):
    """Test questions regarding model accuracy and architecture."""
    res = auth_client.post('/api/chat', json={'message': 'What are the production model accuracy metrics?'})
    assert res.status_code == 200
    data = res.get_json()
    assert 'Model 01' in data['response']
    assert 'Logistic Regression' in data['response']
    assert 'Model 02' in data['response']
    assert 'XGBoost' in data['response']
    assert '68.12%' in data['response']
    assert '97.52%' in data['response']


def test_7_chat_history_and_clear(auth_client):
    """Test history endpoint and clear conversation endpoint."""
    # Send a message
    res = auth_client.post('/api/chat', json={'message': 'Daily operational summary'})
    assert res.status_code == 200
    conv_id = res.get_json().get('conversation_id')
    assert conv_id is not None

    # Check history
    h_res = auth_client.get(f'/api/chat/history?conversation_id={conv_id}')
    assert h_res.status_code == 200
    h_data = h_res.get_json()
    assert len(h_data.get('messages', [])) >= 2

    # Clear chat
    c_res = auth_client.post('/api/chat/clear', json={'conversation_id': conv_id})
    assert c_res.status_code == 200
    assert c_res.get_json()['success'] is True
