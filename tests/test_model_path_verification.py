import os
import sys

# Ensure root is in python path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

import config
from src.load_data import MODELS
from src.prediction import load_model, predict_order_creation_api
from src.dispatch_prediction import load_dispatch_model, predict_dispatch_api

def test_models():
    print(f"Config MODELS_DIR: {config.Config.MODELS_DIR}")
    print(f"load_data MODELS: {MODELS}")
    
    assert "Logistics-Control-Tower" in config.Config.MODELS_DIR, f"Config MODELS_DIR is not pointing to external path: {config.Config.MODELS_DIR}"
    assert "Logistics-Control-Tower" in MODELS, f"load_data MODELS is not pointing to external path: {MODELS}"
    
    m1 = load_model()
    print("Model 01 successfully loaded:", type(m1))
    
    p1 = predict_order_creation_api({
        'Days for shipment (scheduled)': 4,
        'Order Item Quantity': 1,
        'Sales': 150.0,
        'Shipping Mode': 'Standard Class',
        'Order Region': 'Western Europe',
        'Type': 'DEBIT',
        'Market': 'Europe',
        'Primary Category': 'Fitness'
    })
    print("Model 01 prediction result:", p1.get('prediction_status'), p1.get('predicted_probability'), p1.get('risk_level'))
    assert p1.get('prediction_status') == 'PREDICTED'
    
    m2 = load_dispatch_model()
    print("Model 02 successfully loaded:", type(m2))
    
    p2 = predict_dispatch_api({
        'Days for shipment (scheduled)': 4,
        'Order-to-Ship Time': 2.5,
        'Shipping Mode': 'Standard Class',
        'Order Region': 'Western Europe',
        'Market': 'Europe',
        'Department Name': 'Maritime Logistics',
        'Customer Segment': 'Consumer'
    })
    print("Model 02 prediction result:", p2.get('prediction_status'), p2.get('predicted_probability'), p2.get('risk_level'))
    assert p2.get('prediction_status') == 'PREDICTED'
    
    print("\nALL EXTERNAL MODEL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_models()
