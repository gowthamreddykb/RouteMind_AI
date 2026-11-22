"""
test_pipeline_and_db.py - End-to-End Integration & Unit Test Suite
Validates the complete 13-stage reference pipeline, database adapter, live event manager, and Flask endpoints.
"""

import os
import json
import pytest
import pandas as pd
import numpy as np

from pipeline.stage_01_ingestion import DataIngestion
from pipeline.stage_02_cleaning import DataCleaning
from pipeline.stage_04_feature_engineering import FeatureEngineering
from pipeline.stage_06_data_splitting import DataSplitting
from pipeline.live_event_manager import LiveEventManager
from sql.db_adapter import DatabaseAdapter
from app import app

@pytest.fixture(scope="module")
def sample_data():
    ingestion = DataIngestion()
    df, manifest = ingestion.load_dataset(dataset_key="historical", sample_rows=500)
    return df, manifest

def test_data_ingestion_historical(sample_data):
    df, manifest = sample_data
    assert len(df) == 500
    assert manifest["dataset_key"] == "historical"
    assert "Late_delivery_risk" in df.columns
    assert len(manifest["sha256"]) == 64

def test_data_cleaning(sample_data):
    df, _ = sample_data
    cleaning = DataCleaning()
    df_clean, report = cleaning.clean(df, dataset_key="test_run")
    assert len(df_clean) <= len(df)
    assert "Customer Password" not in df_clean.columns
    assert "Customer Email" not in df_clean.columns
    assert report["target_distribution"]["late_delivery_rate"] >= 0.0

def test_feature_engineering_no_leakage(sample_data):
    df, _ = sample_data
    fe = FeatureEngineering()
    X, num_cols, cat_cols = fe.prepare_features(df, stage="order_creation")
    assert "Late_delivery_risk" not in X.columns
    assert "Days for shipping (real)" not in X.columns
    assert "Delivery Status" not in X.columns
    assert len(num_cols) > 0
    assert len(cat_cols) > 0

def test_data_splitting_group_integrity(sample_data):
    df, _ = sample_data
    cleaning = DataCleaning()
    df_clean, _ = cleaning.clean(df, dataset_key="test_run")
    splitting = DataSplitting()
    splits = splitting.split_data(df_clean, dataset_key="test_run", test_size=0.20, val_size=0.10)

    train_orders = set(splits["train"]["Order Id"]) if "Order Id" in splits["train"].columns else set()
    test_orders = set(splits["test"]["Order Id"]) if "Order Id" in splits["test"].columns else set()
    if train_orders and test_orders:
        overlap = train_orders.intersection(test_orders)
        assert len(overlap) == 0, f"Order Id leakage detected between train and test: {overlap}"

def test_database_adapter_persistence(tmp_path):
    test_db = str(tmp_path / "test_control_tower.db")
    db = DatabaseAdapter(db_path=test_db)

    score_id = db.record_prediction({
        "shipment_id": "TEST-SHIP-01",
        "model_id": "test_model_v1",
        "prediction_stage": "order_creation",
        "late_delivery_probability": 0.7250,
        "predicted_class": 1,
        "selected_threshold": 0.40,
        "risk_category": "High Risk",
        "alert_level": "CRITICAL (RED)"
    })
    assert score_id > 0

    recent = db.get_recent_scores(limit=5)
    assert len(recent) == 1
    assert recent[0]["shipment_id"] == "TEST-SHIP-01"
    assert recent[0]["late_delivery_probability"] == 0.7250

def test_live_event_manager(tmp_path):
    history_file = str(tmp_path / "live_events.csv")
    mgr = LiveEventManager(tracking_history_file=history_file)

    payload = {
        "Order Id": "LIVE-PYTEST-01",
        "Days for shipment (scheduled)": 2,
        "Type": "TRANSFER",
        "Shipping Mode": "First Class",
        "Sales": 500.0
    }
    result = mgr.add_new_shipment_event(payload)
    assert "random_forest" in result
    assert "xgboost" in result
    assert "consolidated_assessment" in result

    summary = mgr.get_activity_summary()
    assert summary["total_events"] == 1

def test_flask_api_full_endpoints():
    client = app.test_client()

    # 1. Health
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json["status"] == "healthy"

    # 2. Live event
    r = client.post("/predict/live-event", json={
        "Order Id": "LIVE-API-01",
        "Days for shipment (scheduled)": 3,
        "Type": "DEBIT",
        "Shipping Mode": "Second Class"
    })
    assert r.status_code == 200
    assert "consolidated_assessment" in r.json

    # 3. Batch
    r = client.post("/predict/batch", json={
        "shipments": [
            {"Order Id": "B1", "Days for shipment (scheduled)": 4, "Type": "PAYMENT", "Shipping Mode": "Standard Class"}
        ]
    })
    assert r.status_code == 200
    assert r.json["count"] == 1

    # 4. Registry
    r = client.get("/models/registry")
    assert r.status_code == 200
    assert "models" in r.json
