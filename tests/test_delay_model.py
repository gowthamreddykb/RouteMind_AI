import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from src.delay_prediction import load_delay_model, predict_delay_api

def test_delay():
    model, fname = load_delay_model()
    print(f"CatBoost model loaded successfully: {fname}")
    
    res = predict_delay_api({
        'Days for shipment (scheduled)': 4.0,
        'Order-to-Ship Time': 2.5,
        'Shipping Mode': 'Standard Class',
        'Customer Segment': 'Consumer',
        'Order Region': 'Western Europe'
    }, shipment_id='SHP-10001')
    
    print("Prediction result:", res)
    assert res['prediction_status'] == 'PREDICTED'
    assert res['predicted_shipping_days'] is not None
    assert res['estimated_delay_days'] is not None
    print("CatBoost Regressor test PASSED!")

if __name__ == '__main__':
    test_delay()
