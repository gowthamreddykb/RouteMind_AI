"""
stage_12_explainability.py - Stage 12: Feature Importance & Explainability
Computes operational feature attribution for the champion model,
identifying the top drivers of late delivery risk across logistics operations.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
try:
    from pipeline.config import REPORTS_DIR
except ImportError:
    from config import REPORTS_DIR

class Explainability:
    def compute_importance(self, pipeline, feature_names: list[str], top_n: int = 10) -> list[dict]:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Computing Feature Importance & Attribution...")

        classifier = pipeline.named_steps.get("classifier")
        if hasattr(classifier, "feature_importances_"):
            raw_importances = classifier.feature_importances_
            preprocessor = pipeline.named_steps.get("preprocessor")

            # Try retrieving transformed feature names if available
            try:
                out_names = preprocessor.get_feature_names_out()
            except Exception:
                out_names = [f"feat_{i}" for i in range(len(raw_importances))]

            df_imp = pd.DataFrame({
                "feature": out_names,
                "importance": raw_importances
            }).sort_values(by="importance", ascending=False).reset_index(drop=True)

            top_features = df_imp.head(top_n).to_dict(orient="records")
        else:
            top_features = [{"feature": "linear_coef", "importance": 1.0}]

        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(os.path.join(REPORTS_DIR, "feature_importance.json"), "w") as f:
            json.dump(top_features, f, indent=2)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Top 3 Risk Drivers: {', '.join([f['feature'] for f in top_features[:3]])}")
        return top_features
