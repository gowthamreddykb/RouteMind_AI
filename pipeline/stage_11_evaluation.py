"""
stage_11_evaluation.py - Stage 11: Final Evaluation & Operational Reporting
Evaluates the champion model on the untouched test split:
- Confusion Matrix Display (reproducing reference notebook Cell 12 & 17)
- Classification Report (reproducing notebook Cell 3 & 16)
- Monotonic risk bucket validation (Low, Medium, High operational risk)
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from datetime import datetime
try:
    from pipeline.config import REPORTS_DIR
except ImportError:
    from config import REPORTS_DIR

class FinalEvaluation:
    def evaluate_champion(self, champion_name: str, pipeline, X_test: pd.DataFrame, y_test: np.ndarray, threshold: float = 0.5) -> dict:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Evaluating Champion Model '{champion_name}' on Untouched TEST Partition...")

        y_prob = pipeline.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= threshold).astype(int)

        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()

        # Classification Report (reproducing notebook Cell 3 & 16)
        report_text = classification_report(
            y_test,
            y_pred,
            target_names=["On-Time / Advance", "Late Delivery"],
            digits=4,
            zero_division=0
        )
        print("\n" + "=" * 60)
        print(f"   FINAL CLASSIFICATION REPORT ({champion_name}) - TEST DATA")
        print("=" * 60)
        print(report_text)
        print("=" * 60 + "\n")

        # Risk bucket monotonicity analysis
        buckets = pd.cut(
            y_prob,
            bins=[-0.01, 0.35, 0.65, 1.01],
            labels=["Low Risk (<35%)", "Medium Risk (35-65%)", "High Risk (>65%)"]
        )
        bucket_df = pd.DataFrame({"bucket": buckets, "actual": y_test})
        bucket_stats = bucket_df.groupby("bucket", observed=False)["actual"].agg(["count", "mean"]).reset_index()
        bucket_stats.columns = ["Risk Bucket", "Volume", "Observed Late Delivery Rate"]

        observed_rates = bucket_stats["Observed Late Delivery Rate"].values
        is_monotonic = bool(observed_rates[0] < observed_rates[1] < observed_rates[2])

        eval_summary = {
            "model_name": champion_name,
            "decision_threshold": threshold,
            "test_sample_size": len(y_test),
            "confusion_matrix": {
                "TN": int(tn),
                "FP": int(fp),
                "FN": int(fn),
                "TP": int(tp)
            },
            "risk_buckets": bucket_stats.to_dict(orient="records"),
            "monotonic_risk_gradient": is_monotonic,
            "evaluated_at": datetime.utcnow().isoformat() + "Z"
        }

        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(os.path.join(REPORTS_DIR, "final_test_evaluation.json"), "w") as f:
            json.dump(eval_summary, f, indent=2)

        with open(os.path.join(REPORTS_DIR, "classification_report_test.txt"), "w") as f:
            f.write(report_text)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Test Evaluation complete. Monotonic gradient verified: {is_monotonic}")
        return eval_summary
