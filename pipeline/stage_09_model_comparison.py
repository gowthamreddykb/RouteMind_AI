"""
stage_09_model_comparison.py - Stage 9: Model Comparison & Metric Synthesis
Implements the exact multi-metric benchmarking framework from reference notebook Cells 16, 18, and 19:
- Accuracy, Precision, Recall, F1 Score, Probability MSE, ROC-AUC, PR-AUC
Generates the comparison table and exportable JSON/CSV summaries.
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    mean_squared_error,
    roc_auc_score,
    average_precision_score,
    confusion_matrix
)
from datetime import datetime
try:
    from pipeline.config import REPORTS_DIR
except ImportError:
    from config import REPORTS_DIR

class ModelComparison:
    METRICS = ["Accuracy", "Precision", "Recall", "F1 Score", "Probability MSE", "ROC-AUC", "PR-AUC"]

    def evaluate_models(self, models: dict, X_eval: pd.DataFrame, y_eval: np.ndarray, split_name: str = "Validation") -> pd.DataFrame:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Evaluating and Comparing Models on {split_name} Split...")

        records = []
        for model_name, pipeline in models.items():
            y_pred = pipeline.predict(X_eval)
            y_prob = pipeline.predict_proba(X_eval)[:, 1]

            acc = accuracy_score(y_eval, y_pred)
            prec = precision_score(y_eval, y_pred, zero_division=0)
            rec = recall_score(y_eval, y_pred, zero_division=0)
            f1 = f1_score(y_eval, y_pred, zero_division=0)
            mse = mean_squared_error(y_eval, y_prob)
            auc = roc_auc_score(y_eval, y_prob)
            pr_auc = average_precision_score(y_eval, y_prob)

            tn, fp, fn, tp = confusion_matrix(y_eval, y_pred).ravel()

            records.append({
                "Model": model_name,
                "Accuracy": round(acc, 4),
                "Precision": round(prec, 4),
                "Recall": round(rec, 4),
                "F1 Score": round(f1, 4),
                "Probability MSE": round(mse, 4),
                "ROC-AUC": round(auc, 4),
                "PR-AUC": round(pr_auc, 4),
                "TN": int(tn),
                "FP": int(fp),
                "FN": int(fn),
                "TP": int(tp)
            })

        df_comp = pd.DataFrame(records)
        df_comp = df_comp.sort_values(by="ROC-AUC", ascending=False).reset_index(drop=True)

        # Print comparison table formatted identically to notebook Cell 18
        print("\n" + "=" * 80)
        print(f"   MODEL COMPARISON BENCHMARK TABLE ({split_name.upper()} DATA)")
        print("=" * 80)
        print(df_comp[["Model", "Accuracy", "Precision", "Recall", "F1 Score", "Probability MSE", "ROC-AUC"]].to_string(index=False))
        print("=" * 80 + "\n")

        # Save to reports
        os.makedirs(REPORTS_DIR, exist_ok=True)
        csv_path = os.path.join(REPORTS_DIR, f"model_comparison_{split_name.lower()}.csv")
        df_comp.to_csv(csv_path, index=False)

        json_path = os.path.join(REPORTS_DIR, f"model_comparison_{split_name.lower()}.json")
        with open(json_path, "w") as f:
            json.dump(records, f, indent=2)

        return df_comp
