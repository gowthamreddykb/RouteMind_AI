"""
test_conversation_flow.py - Real-World 6-Turn End-to-End Chatbot Conversation Test
Tests:
Turn 1: 'hii' -> Pure greeting
Turn 2: 'give the all risk segements' -> Complete Risk Segmentation (Summary, Distribution, Details Table, Operations)
Turn 3: 'show only high risk shipments' -> Filtered high-risk shipments
Turn 4: 'which of these have open exceptions?' -> Exception audit on context shipments
Turn 5: 'explain the first shipment' -> Deep drill-down on first shipment
Turn 6: 'what should the dispatcher do next?' -> Grounded operational guidance
"""
import pytest
from src.app import create_app
from extensions import db
from src.services.ai_assistant_service import AIAssistantService


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def auth_client(app):
    client = app.test_client()
    client.get('/auth/quick-login/dispatcher', follow_redirects=True)
    return client


def test_complete_6_turn_conversational_flow(auth_client):
    conv_id = None

    # TURN 1: User says 'hii'
    res1 = auth_client.post('/api/chat', json={'message': 'hii', 'conversation_id': conv_id})
    assert res1.status_code == 200
    data1 = res1.get_json()
    conv_id = data1.get('conversation_id')
    assert conv_id is not None
    # Must be a greeting, NOT the full telemetry dump
    assert 'hello' in data1['response'].lower()
    assert 'how can i help you' in data1['response'].lower() or 'intelligence assistant' in data1['response'].lower()

    # TURN 2: User says 'give the all risk segements'
    res2 = auth_client.post('/api/chat', json={'message': 'give the all risk segements', 'conversation_id': conv_id})
    assert res2.status_code == 200
    data2 = res2.get_json()
    resp2 = data2['response']
    # Must contain risk segmentation sections
    assert 'A. Risk Summary' in resp2
    assert 'B. Risk Distribution' in resp2
    assert 'C. Active Consignment Inventory' in resp2
    assert 'D. Operational Interpretation' in resp2
    assert 'High / Critical Risk' in resp2
    assert 'Medium / Elevated Risk' in resp2
    assert 'Low / On-Track Risk' in resp2
    assert len(data2.get('context_shipments', [])) >= 5

    # TURN 3: User says 'show only high risk shipments'
    res3 = auth_client.post('/api/chat', json={'message': 'show only high risk shipments', 'conversation_id': conv_id})
    assert res3.status_code == 200
    data3 = res3.get_json()
    resp3 = data3['response']
    assert 'High-Risk' in resp3 or 'Critical' in resp3
    assert '| Shipment #' in resp3
    assert len(data3.get('context_shipments', [])) > 0

    # TURN 4: User says 'which of these have open exceptions?'
    res4 = auth_client.post('/api/chat', json={'message': 'which of these have open exceptions?', 'conversation_id': conv_id})
    assert res4.status_code == 200
    data4 = res4.get_json()
    resp4 = data4['response']
    assert 'Exception Audit for the' in resp4
    assert 'EXC-' in resp4
    assert 'INVESTIGATING' in resp4 or 'OPEN' in resp4

    # TURN 5: User says 'explain the first shipment'
    res5 = auth_client.post('/api/chat', json={'message': 'explain the first shipment', 'conversation_id': conv_id})
    assert res5.status_code == 200
    data5 = res5.get_json()
    resp5 = data5['response']
    assert 'Consignment Intelligence Report' in resp5
    assert 'Lifecycle Status' in resp5
    assert 'Evaluated Risk' in resp5

    # TURN 6: User says 'what should the dispatcher do next?'
    res6 = auth_client.post('/api/chat', json={'message': 'what should the dispatcher do next?', 'conversation_id': conv_id})
    assert res6.status_code == 200
    data6 = res6.get_json()
    resp6 = data6['response']
    assert 'Recommended Operations Protocol' in resp6 or 'Recommended Next Steps' in resp6
    assert 'Escalate to Manager' in resp6 or 'Exception Desk' in resp6 or 'dispatcher' in resp6.lower()


def test_15_diverse_intents(auth_client):
    """Verifies each of the 15 user-requested intents against the real database."""
    queries = [
        ("Give me all risk segments.", "Risk Segmentation"),
        ("Show all high-risk shipments.", "High-Risk"),
        ("Show all medium-risk shipments.", "Medium-Risk"),
        ("Show all low-risk shipments.", "Low-Risk"),
        ("How many shipments are there in each risk category?", "Risk Summary"),
        ("What percentage of shipments are high risk?", "High-Risk Delay Rate"),
        ("Which region has the most high-risk shipments?", "Regional Risk Concentration Analysis"),

        ("Which shipping mode has the highest delay rate?", "Shipping Mode Delay Analysis"),
        ("Explain shipment SHP-10482.", "SHP-10482"),
        ("Which shipments require manager attention?", "Manager"),
        ("Compare high-risk and low-risk shipments.", "High-Risk vs. Low-Risk"),
        ("How many manager escalations are pending?", "Manager Escalations Audit"),
        ("How many exceptions are open?", "Operational Exception Desk Audit"),
        ("What are the production model accuracy metrics?", "68.12%"),
        ("Give me a summary of the shipment risk situation.", "Risk Segmentation"),
    ]

    for q, expected in queries:
        res = auth_client.post('/api/chat', json={'message': q})
        assert res.status_code == 200, f"Query '{q}' failed with status {res.status_code}"
        data = res.get_json()
        assert expected.lower() in data['response'].lower(), f"Expected '{expected}' in response for query '{q}', got: {data['response']}"
