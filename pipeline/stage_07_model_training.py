"""
stage_07_model_training.py - Stage 7: Model Training (Reference Methodology Implementation)
Implements model training directly adopting the architecture and parameters from reference notebook:
- Random Forest Classifier (Cell 2: n_estimators=200, max_depth=5, class_weight='balanced')
- XGBoost Classifier (Cell 15: scale_pos_weight=negative/positive, n_estimators=200, max_depth=4, lr=0.05)
- Logistic Regression (Baseline)
- LightGBM (Gradient Boosting Benchmark)
"""

import os
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
import lightgbm as lgb
from datetime import datetime

class ModelTraining:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def train_models(self, X_train: pd.DataFrame, y_train: np.ndarray, preprocessor, preprocessor_tree, scale_pos_weight: float) -> dict:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Training Models with Reference Methodology...")

        models = {}

        # 1. Random Forest Classifier (Directly from notebook Cell 2)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 1/4 Training Random Forest Classifier (class_weight='balanced')...")
        rf_clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            class_weight="balanced",
            random_state=self.random_state,
            n_jobs=-1
        )
        rf_pipe = Pipeline([
            ("preprocessor", preprocessor_tree),
            ("classifier", rf_clf)
        ])
        rf_pipe.fit(X_train, y_train)
        models["Random Forest"] = rf_pipe

        # 2. XGBoost Classifier (Directly from notebook Cell 15)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 2/4 Training XGBoost Classifier (scale_pos_weight={scale_pos_weight:.3f})...")
        xgb_clf = XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=self.random_state,
            n_jobs=-1
        )
        xgb_pipe = Pipeline([
            ("preprocessor", preprocessor_tree),
            ("classifier", xgb_clf)
        ])
        xgb_pipe.fit(X_train, y_train)
        models["XGBoost"] = xgb_pipe

        # 3. Logistic Regression (Baseline with standard scaling)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 3/4 Training Logistic Regression Baseline...")
        lr_clf = LogisticRegression(
            C=1.0,
            penalty="l2",
            solver="liblinear",
            class_weight="balanced",
            max_iter=1000,
            random_state=self.random_state
        )
        lr_pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", lr_clf)
        ])
        lr_pipe.fit(X_train, y_train)
        models["Logistic Regression"] = lr_pipe

        # 4. LightGBM Classifier (Benchmark)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 4/4 Training LightGBM Classifier...")
        lgb_clf = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            scale_pos_weight=scale_pos_weight,
            random_state=self.random_state,
            verbose=-1,
            n_jobs=-1
        )
        lgb_pipe = Pipeline([
            ("preprocessor", preprocessor_tree),
            ("classifier", lgb_clf)
        ])
        lgb_pipe.fit(X_train, y_train)
        models["LightGBM"] = lgb_pipe

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully trained all 4 model pipelines.")
        return models
