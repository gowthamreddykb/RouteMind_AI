from src.services.anomaly_service import AnomalyService

def detect(records):
    return AnomalyService.detect_anomalies(records)
