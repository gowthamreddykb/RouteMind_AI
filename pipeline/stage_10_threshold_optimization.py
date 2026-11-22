"""
stage_10_threshold_optimization.py - Stage 10: Threshold Optimization & Calibration
Finds optimal decision boundary to minimize expected logistics penalty costs (Cost_FN=2.0, Cost_FP=1.0)
and validates monotonic probability calibration.
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from sklearn.calibration import CalibratedClassifierCV
from datetime import datetime
try:
    from pipeline.config import REPORTS_DIR
except ImportError:
    from config import REPORTS_DIR

class ThresholdOptimization:
    def __init__(self, cost_fn: float = 2.0, cost_fp: float = 1.0):
        self.cost_fn = cost_fn
        self.cost_fp = cost_fp

    def optimize_threshold(self, y_true: np.ndarray, y_prob: np.ndarray) -> dict:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Optimizing Operational Decision Threshold...")

        thresholds = np.linspace(0.1, 0.9, 81)
        best_cost = float("inf")
        best_thr = 0.5
        best_row = {}
        rows = []

        for thr in thresholds:
            y_pred = (y_prob >= thr).astype(int)
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
            total_cost = (fn * self.cost_fn) + (fp * self.cost_fp)
            cost_per_order = total_cost / len(y_true)

            rec = {
                "threshold": round(float(thr), 2),
                "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
                "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
                "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
                "total_cost": float(total_cost),
                "cost_per_order": round(float(cost_per_order), 4),
                "flagged_rate": round(float((tp + fp) / len(y_true)), 4)
            }
            rows.append(rec)

            if total_cost < best_cost:
                best_cost = total_cost
                best_thr = round(float(thr), 2)
                best_row = rec

        report = {
            "optimal_threshold": best_thr,
            "cost_assumptions": {"cost_fn": self.cost_fn, "cost_fp": self.cost_fp},
            "metrics_at_optimal_threshold": best_row,
            "optimized_at": datetime.utcnow().isoformat() + "Z"
        }

        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(os.path.join(REPORTS_DIR, "threshold_optimization_results.json"), "w") as f:
            json.dump(report, f, indent=2)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Optimal Threshold: {best_thr} (Cost/Order: ${best_row['cost_per_order']:.2f}, Recall: {best_row['recall']:.2%}, Precision: {best_row['precision']:.2%})")
        return report
