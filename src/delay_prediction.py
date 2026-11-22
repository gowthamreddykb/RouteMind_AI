"""delay_prediction.py - Model 03: Delivery Delay Estimation Inference API.
Uses CatBoost Regressor to estimate:
Delay_Days = Days for shipping (real) - Days for shipment (scheduled)
"""
import os
import sys
import json
import datetime as dt
import pandas as pd
from catboost import CatBoostRegressor

sys.path.insert(0, os.path.dirname(__file__))
from load_data import MODELS

_DELAY_CACHE = {}

def _resolve_delay_models_dir(models_dir=None):
    if models_dir is None:
        models_dir = MODELS
    if os.path.exists(os.path.join(models_dir, 'models')):
        models_dir = os.path.join(models_dir, 'models')
    return models_dir

def load_delay_model(models_dir=None, reload=False):
    models_dir = _resolve_delay_models_dir(models_dir)
    key = ('delay_catboost', os.path.abspath(models_dir))
    if reload or key not in _DELAY_CACHE:
        possible_paths = [
            os.path.join(models_dir, 'model_03', 'catboost_shipping_days_regressor.cbm'),
            os.path.join(models_dir, 'model_03', 'catboost_delay_regressor.cbm'),
            os.path.join(models_dir, 'model_03', 'catboost_model.cbm'),
            os.path.join(models_dir, 'model_03_improved', 'catboost_model_improved.cbm')
        ]
        p = next((path for path in possible_paths if os.path.exists(path)), None)
        if not p:
            raise RuntimeError(f"CatBoost delay model not found in {models_dir}")
        cb = CatBoostRegressor()
        cb.load_model(p)
        _DELAY_CACHE[key] = (cb, os.path.basename(p))
    return _DELAY_CACHE[key]

def predict_delay_api(payload, shipment_id=None, models_dir=None):
    base = {
        'shipment_id': shipment_id or (payload.get('shipment_id') if isinstance(payload, dict) else None),
        'prediction_stage': 'delay_estimation',
        'model_name': 'Model 03: CatBoost Delay Regressor',
        'model_version': '1.0.0',
        'predicted_shipping_days': None,
        'scheduled_shipping_days': None,
        'estimated_delay_days': None,
        'delay_status': 'UNKNOWN',
        'prediction_status': 'PENDING',
        'prediction_timestamp': dt.datetime.now(dt.timezone.utc).isoformat()
    }
    
    try:
        model, model_file = load_delay_model(models_dir)
        sched_days = float(payload.get('Days for shipment (scheduled)', payload.get('scheduled_days', 4.0)))
        dwell_time = float(payload.get('Order-to-Ship Time', payload.get('warehouse_processing_time', 2.0)))
        mode = str(payload.get('Shipping Mode', payload.get('shipping_mode', 'Standard Class')))
        segment = str(payload.get('Customer Segment', payload.get('customer_segment', 'Consumer')))
        region = str(payload.get('Order Region', payload.get('destination_region', 'Western Europe')))
        
        df = pd.DataFrame([{
            'Days for shipment (scheduled)': sched_days,
            'Order-to-Ship Time': dwell_time,
            'Shipping Mode': mode,
            'Customer Segment': segment,
            'Order Region': region
        }])
        
        pred_val = float(model.predict(df)[0])
        
        # If model outputs shipping days (typically 2-6 days):
        if 'shipping_days' in model_file or pred_val > 1.0:
            pred_shipping_days = round(pred_val, 2)
            estimated_delay = round(max(0.0, pred_shipping_days - sched_days), 2)
        else:
            # Model directly outputs delay
            estimated_delay = round(max(0.0, pred_val), 2)
            pred_shipping_days = round(sched_days + estimated_delay, 2)
            
        status = 'DELAY_EXPECTED' if estimated_delay >= 0.5 else 'ON_SCHEDULE'
        
        return {
            **base,
            'predicted_shipping_days': pred_shipping_days,
            'scheduled_shipping_days': sched_days,
            'estimated_delay_days': estimated_delay,
            'delay_status': status,
            'prediction_status': 'PREDICTED'
        }
    except Exception as e:
        return {
            **base,
            'prediction_status': 'ERROR',
            'error': str(e)
        }
