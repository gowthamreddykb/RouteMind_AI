import pytest
from src.services.anomaly_service import AnomalyService

def test_anomaly_detection():
    data = [{'shipment_id': 'ANOM-1', 'scheduled_days': 1, 'warehouse_time': 4.0, 'sales': 100, 'quantity': 1}]
    res = AnomalyService.detect_anomalies(data)
    assert len(res) == 1
    assert res[0]['severity'] in ('HIGH', 'MEDIUM')
