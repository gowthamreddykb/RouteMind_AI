from src.prediction import predict_at_order_creation, predict_order_creation_api

def predict(records, shipment_id=None, explain=True):
    return predict_order_creation_api(records, shipment_id=shipment_id, explain=explain)
