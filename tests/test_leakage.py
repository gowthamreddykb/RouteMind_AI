import json, os
import numpy as np
import pytest
from sklearn.metrics import roc_auc_score
import feature_engineering as FE
import feature_audit as FA
import load_data as L

BANNED = {c for c, _, _ in L.PROHIBITED}

def test_target_not_in_features(cleaned):
    f = FE.engineer_order_features(cleaned)
    assert L.TARGET not in f.columns

def test_actual_duration_and_outcome_columns_excluded(cleaned):
    f = FE.engineer_order_features(cleaned, ("Order City", "Order State", "Latitude", "Longitude"))
    for c in ["Days for shipping (real)", "Delivery Status", "Order Status", "shipping date (DateOrders)"]:
        assert c not in f.columns

def test_identifiers_not_model_inputs(cleaned):
    f = FE.engineer_order_features(cleaned)
    for c in ["Order Id", "Order Item Id", "Customer Id", "Order Customer Id", "Product Card Id", "Category Id"]:
        assert c not in f.columns

def test_raw_required_fields_have_no_prohibited_column():
    assert not (set(FE.BASE_RAW_FIELDS + FE.REVIEW_NUMERIC + FE.REVIEW_CATEGORICAL) & BANNED)

def test_features_computable_without_any_outcome_column(cleaned):
    only = cleaned[FE.BASE_RAW_FIELDS]
    assert len(FE.engineer_order_features(only)) == len(cleaned)

def test_no_single_feature_reveals_target(parts):
    tr = parts["train"].sample(30000, random_state=0); y = tr[L.TARGET]
    f = FE.engineer_order_features(tr, ("Order City", "Order State", "Latitude", "Longitude"))
    for c in f.columns:
        s = f[c]
        score = s.fillna(s.median()) if s.dtype.kind in "fi" else s.map(y.groupby(s).mean())
        auc = roc_auc_score(y, score)
        assert max(auc, 1 - auc) < 0.80, f"{c} looks like leakage (AUC {auc:.3f})"

def test_saved_schema_has_no_prohibited_inputs(production):
    schema = production["feature_schema"]
    assert not (set(schema["required_raw_fields"]) & BANNED)
    assert L.TARGET not in schema["model_input_numeric"] + schema["model_input_categorical"]
