"""
stage_08_hyperparameter_tuning.py - Stage 8: Hyperparameter Tuning
Performs structured tuning of candidate architectures on the validation partition.
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, f1_score
from datetime import datetime
try:
    from pipeline.config import REPORTS_DIR
except ImportError:
    from config import REPORTS_DIR

class HyperparameterTuning:
    def tune_xgboost(self, X_tr: pd.DataFrame, y_tr: np.ndarray, X_va: pd.DataFrame, y_va: np.ndarray, preprocessor, scale_pos_weight: float) -> dict:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Executing Hyperparameter Grid Evaluation...")
        from xgboost import XGBClassifier
        from sklearn.pipeline import Pipeline

        param_grid = [
            {"n_estimators": 150, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.8},
            {"n_estimators": 250, "max_depth": 5, "learning_rate": 0.03, "subsample": 0.9},
            {"n_estimators": 200, "max_depth": 6, "learning_rate": 0.05, "subsample": 0.85}
        ]

        results = []
        best_auc = -1.0
        best_params = None

        for idx, params in enumerate(param_grid):
            clf = XGBClassifier(
                **params,
                scale_pos_weight=scale_pos_weight,
                eval_metric="logloss",
                random_state=42,
                n_jobs=-1
            )
            pipe = Pipeline([
                ("preprocessor", preprocessor),
                ("classifier", clf)
            ])
            pipe.fit(X_tr, y_tr)

            p_val = pipe.predict_proba(X_va)[:, 1]
            auc = roc_auc_score(y_va, p_val)
            pred_val = (p_val >= 0.5).astype(int)
            f1 = f1_score(y_va, pred_val, zero_division=0)

            record = {
                "trial": idx + 1,
                "params": params,
                "val_roc_auc": round(auc, 4),
                "val_f1": round(f1, 4)
            }
            results.append(record)
            print(f"  Trial {idx+1}: {params} -> Val AUC: {auc:.4f}, Val F1: {f1:.4f}")

            if auc > best_auc:
                best_auc = auc
                best_params = params

        tuning_report = {
            "best_params": best_params,
            "best_val_auc": round(best_auc, 4),
            "trials": results,
            "tuned_at": datetime.utcnow().isoformat() + "Z"
        }

        with open(os.path.join(REPORTS_DIR, "hyperparameter_tuning_results.json"), "w") as f:
            json.dump(tuning_report, f, indent=2)

        return tuning_report
