"""
stage_03_eda.py - Stage 3: Exploratory Data Analysis & Class Balance Audit
Computes statistical profiles, late delivery rates across operational dimensions,
and exact class balance ratios for XGBoost/RandomForest weighting (reference notebook Cell 15).
"""

import os
import json
import pandas as pd
from datetime import datetime
try:
    from pipeline.config import REPORTS_DIR
except ImportError:
    from config import REPORTS_DIR

class ExploratoryAnalysis:
    TARGET_COL = "Late_delivery_risk"

    def analyze(self, df: pd.DataFrame, dataset_key: str = "historical") -> dict:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Executing EDA & Imbalance Audit for '{dataset_key}'...")

        neg_count = int((df[self.TARGET_COL] == 0).sum())
        pos_count = int((df[self.TARGET_COL] == 1).sum())
        scale_pos_weight = round(neg_count / max(pos_count, 1), 4)

        # Shipping mode analysis
        mode_stats = {}
        if "Shipping Mode" in df.columns:
            mode_grp = df.groupby("Shipping Mode")[self.TARGET_COL].agg(["count", "mean"]).reset_index()
            for _, r in mode_grp.iterrows():
                mode_stats[r["Shipping Mode"]] = {
                    "total_shipments": int(r["count"]),
                    "late_rate": round(float(r["mean"]), 4)
                }

        # Order region analysis
        region_stats = {}
        if "Order Region" in df.columns:
            top_regions = df["Order Region"].value_counts().head(5).index.tolist()
            reg_grp = df[df["Order Region"].isin(top_regions)].groupby("Order Region")[self.TARGET_COL].agg(["count", "mean"]).reset_index()
            for _, r in reg_grp.iterrows():
                region_stats[r["Order Region"]] = {
                    "total_shipments": int(r["count"]),
                    "late_rate": round(float(r["mean"]), 4)
                }

        # Numerical summary
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        num_summary = df[numeric_cols].describe().round(2).to_dict()

        eda_results = {
            "dataset_key": dataset_key,
            "total_records": len(df),
            "class_imbalance": {
                "negative_count_on_time": neg_count,
                "positive_count_late": pos_count,
                "late_ratio": round(pos_count / len(df), 4),
                "scale_pos_weight": scale_pos_weight,
                "reference_formula": "negative_count / positive_count (from notebook Cell 15)"
            },
            "shipping_mode_distribution": mode_stats,
            "top_regions_distribution": region_stats,
            "analyzed_at": datetime.utcnow().isoformat() + "Z"
        }

        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_path = os.path.join(REPORTS_DIR, f"eda_summary_{dataset_key}.json")
        with open(report_path, "w") as f:
            json.dump(eda_results, f, indent=2)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Class Balance: {neg_count:,} negative / {pos_count:,} positive. scale_pos_weight: {scale_pos_weight}")
        return eda_results
