"""dispatch_prediction.py - Model 02: Late Delivery at Dispatch Stage Inference API.
Predicts delivery lateness risk at warehouse dock dispatch using:
- Days for shipment (scheduled)
- Order-to-Ship Time (Warehouse processing duration in days)
- Shipping Mode
- Order Region
- Market
- Department Name
- Customer Segment
"""
import os
import sys
import json
import datetime as dt
import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, os.path.dirname(__file__))
from load_data import MODELS

class DispatchValidationError(ValueError):
    pass

class DispatchModelUnavailableError(RuntimeError):
    pass

_DISPATCH_CACHE = {}

def _resolve_dispatch_models_dir(models_dir=None):
    if models_dir is None:
        models_dir = MODELS
    if os.path.exists(os.path.join(models_dir, 'models')):
        models_dir = os.path.join(models_dir, 'models')
    return models_dir

def get_dispatch_schema(models_dir=None):
    models_dir = _resolve_dispatch_models_dir(models_dir)
    for sub in ['model_02', 'model_02_improved', 'dispatch']:
        p = os.path.join(models_dir, sub, 'feature_schema.json')
        if os.path.exists(p):
            with open(p, 'r') as f:
                return json.load(f)
    return {
        'mandatory_numerical_features': ['Days for shipment (scheduled)', 'Order-to-Ship Time'],
        'mandatory_categorical_features': ['Shipping Mode', 'Order Region', 'Market', 'Department Name', 'Customer Segment'],
        'optimal_threshold': 0.39,
        'risk_cutoffs': {'low': 0.30, 'medium': 0.50, 'high': 0.70}
    }

def load_dispatch_model(models_dir=None, reload=False):
    models_dir = _resolve_dispatch_models_dir(models_dir)
    key = ('dispatch', os.path.abspath(models_dir))
    if reload or key not in _DISPATCH_CACHE:
        possible_paths = [
            os.path.join(models_dir, 'model_02', 'xgboost_dispatch_pipeline.joblib'),
            os.path.join(models_dir, 'model_02_improved', 'best_model.joblib'),
            os.path.join(models_dir, 'dispatch', 'xgboost_dispatch_pipeline.joblib'),
            os.path.join(models_dir, 'dispatch', 'best_model.joblib')
        ]
        p = next((path for path in possible_paths if os.path.exists(path)), None)
        if not p:
            raise DispatchModelUnavailableError(f'Dispatch model not found in {models_dir}')
        _DISPATCH_CACHE[key] = joblib.load(p)
    return _DISPATCH_CACHE[key]

def validate_dispatch_records(records, schema=None):
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, (list, tuple)) or len(records) == 0:
        raise DispatchValidationError('Input must be a non-empty dict or list of dicts.')
    
    schema = schema or get_dispatch_schema()
    num_fields = schema.get('mandatory_numerical_features', ['Days for shipment (scheduled)', 'Order-to-Ship Time'])
    cat_fields = schema.get('mandatory_categorical_features', ['Shipping Mode', 'Order Region', 'Market', 'Department Name', 'Customer Segment'])
    required = num_fields + cat_fields

    rows = []
    problems = []
    for i, rec in enumerate(records):
        row = {}
        for f in required:
            val = rec.get(f)
            if val is None:
                if f == 'Order-to-Ship Time' and 'Warehouse Processing Time' in rec:
                    val = rec['Warehouse Processing Time']
                elif f == 'Days for shipment (scheduled)' and 'scheduled_days' in rec:
                    val = rec['scheduled_days']
            
            if val is None or (isinstance(val, str) and not val.strip()):
                problems.append(f'Record {i}: missing required field "{f}"')
                continue
            
            if f in num_fields:
                try:
                    num_val = float(val)
                    if num_val < 0:
                        problems.append(f'Record {i}: "{f}" cannot be negative')
                    row[f] = num_val
                except (ValueError, TypeError):
                    problems.append(f'Record {i}: "{f}" must be numeric, got {val!r}')
            else:
                row[f] = str(val).strip()
        rows.append(row)

    if problems:
        raise DispatchValidationError('; '.join(problems))
    return pd.DataFrame(rows)

def explain_dispatch_factors(row_dict, prob, threshold):
    factors = []
    sched_days = row_dict.get('Days for shipment (scheduled)', 4)
    ship_time = row_dict.get('Order-to-Ship Time', 2)
    mode = row_dict.get('Shipping Mode', 'Standard Class')
    region = row_dict.get('Order Region', 'Western Europe')

    # Factor 1: Warehouse Processing Time vs Scheduled Transit Days
    time_ratio = ship_time / max(sched_days, 1)
    if time_ratio >= 1.0:
        factors.append({
            'feature': 'Order-to-Ship Time',
            'feature_value': f'{ship_time:.1f} days',
            'impact': 'CRITICAL_RISK',
            'explanation': f'Warehouse processing ({ship_time:.1f}d) exceeded/matched total scheduled transit window ({sched_days}d), severely endangering on-time arrival.'
        })
    elif time_ratio >= 0.6:
        factors.append({
            'feature': 'Order-to-Ship Time',
            'feature_value': f'{ship_time:.1f} days',
            'impact': 'ELEVATED_RISK',
            'explanation': f'Warehouse processing consumed {time_ratio*100:.0f}% of scheduled window ({sched_days}d).'
        })
    else:
        factors.append({
            'feature': 'Order-to-Ship Time',
            'feature_value': f'{ship_time:.1f} days',
            'impact': 'LOW_RISK',
            'explanation': f'Warehouse processing cleared swiftly ({ship_time:.1f}d), preserving {sched_days - ship_time:.1f} buffer days for carrier transit.'
        })

    # Factor 2: Shipping Mode
    if mode in ['First Class', 'Same Day']:
        factors.append({
            'feature': 'Shipping Mode',
            'feature_value': mode,
            'impact': 'HIGH_SENSITIVITY',
            'explanation': f'High priority expedited mode ({mode}) carries zero-tolerance SLA buffer for dispatch delays.'
        })
    else:
        factors.append({
            'feature': 'Shipping Mode',
            'feature_value': mode,
            'impact': 'NORMAL',
            'explanation': f'Standard carrier route schedule applies for {mode}.'
        })

    # Factor 3: Regional Hub
    factors.append({
        'feature': 'Order Region',
        'feature_value': region,
        'impact': 'NEUTRAL',
        'explanation': f'Destination regional transit historical baseline applied for {region}.'
    })

    return factors

def predict_at_dispatch(records, shipment_id=None, explain=True, models_dir=None):
    single = isinstance(records, dict)
    pipe = load_dispatch_model(models_dir)
    schema = get_dispatch_schema(models_dir)
    df = validate_dispatch_records(records, schema)

    probs = pipe.predict_proba(df)[:, 1]
    threshold = float(schema.get('optimal_threshold', 0.39))

    n = len(df)
    recs = [records] if single else list(records)
    ids = shipment_id if isinstance(shipment_id, (list, tuple)) else [shipment_id] * n
    now = dt.datetime.now(dt.timezone.utc).isoformat()

    results = []
    for i in range(n):
        p = float(probs[i])
        sid = ids[i] or recs[i].get('shipment_id', recs[i].get('order_id', f'DSP-{i+1}'))
        
        if p >= 0.50:
            level = 'HIGH'
        elif p >= 0.35:
            level = 'MEDIUM'
        else:
            level = 'LOW'

        row_dict = df.iloc[i].to_dict()
        factors = explain_dispatch_factors(row_dict, p, threshold) if explain else []

        results.append({
            'shipment_id': sid,
            'prediction_stage': 'dispatch',
            'model_name': 'Model 02: XGBoost Dispatch Classifier',
            'model_version': '1.0.0',
            'late_delivery_probability': round(p, 4),
            'predicted_probability': round(p, 4),
            'risk_percentage': round(p * 100, 2),
            'predicted_class': int(p >= threshold),
            'decision_threshold': threshold,
            'risk_level': level,
            'prediction_status': 'PREDICTED',
            'scoring_timestamp': now,
            'prediction_timestamp': now,
            'top_risk_factors': factors,
            'dock_clearance_status': 'HOLD_FOR_EXPEDITE' if level == 'HIGH' else ('MONITOR' if level == 'MEDIUM' else 'CLEAR_FOR_TRANSIT')
        })

    return results[0] if single else results

def predict_dispatch_api(payload, shipment_id=None, store=None, models_dir=None, explain=True):
    base = {
        'shipment_id': shipment_id or (payload.get('shipment_id') if isinstance(payload, dict) else None),
        'prediction_stage': 'dispatch',
        'predicted_probability': None,
        'risk_percentage': None,
        'risk_level': None,
        'decision_threshold': 0.39,
        'model_version': '1.0.0',
        'prediction_timestamp': dt.datetime.now(dt.timezone.utc).isoformat(),
        'top_risk_factors': []
    }
    try:
        r = predict_at_dispatch(payload, shipment_id=shipment_id, explain=explain, models_dir=models_dir)
        if store is not None:
            try:
                store.log_prediction(r, features=payload)
            except Exception:
                pass
        return r
    except DispatchValidationError as e:
        code, msg = 'VALIDATION_ERROR', str(e)
    except DispatchModelUnavailableError as e:
        code, msg = 'MODEL_UNAVAILABLE', str(e)
    except Exception as e:
        code, msg = 'INTERNAL_ERROR', f'{type(e).__name__}: {e}'
    
    return {**base, 'prediction_status': 'ERROR', 'error': {'code': code, 'message': msg}}
