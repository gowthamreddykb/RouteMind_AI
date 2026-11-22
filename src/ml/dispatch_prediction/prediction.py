from src.dispatch_prediction import predict_at_dispatch, predict_dispatch_api

def predict(records, shipment_id=None, explain=True):
    return predict_dispatch_api(records, shipment_id=shipment_id, explain=explain)
