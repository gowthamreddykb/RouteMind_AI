import pytest
from src.ai.resolution_recommender import recommend_resolution

def test_recommend_resolution():
    res = recommend_resolution('HIGH', 'HOLD_FOR_EXPEDITE')
    assert res['action'] == 'CARRIER_EXPEDITE'
    assert res['urgency'] == 'IMMEDIATE'
