import pytest
from src.services.prediction_service import PredictionService

def test_prediction_service_structure():
    assert hasattr(PredictionService, 'score_order_creation')
    assert hasattr(PredictionService, 'score_dispatch')
    assert hasattr(PredictionService, 'score_unified')
