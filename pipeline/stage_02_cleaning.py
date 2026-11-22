"""
stage_02_cleaning.py - Stage 2: Data Cleaning & Validation
Cleans and validates the dataset, dropping sensitive fields, handling missing values,
and outputting an audit log without modifying target integrity.
"""

import os
import json
import pandas as pd
from datetime import datetime
try:
    from pipeline.config import DATA_DIR, REPORTS_DIR
except ImportError:
    from config import DATA_DIR, REPORTS_DIR

class DataCleaning:
    TARGET_COL = "Late_delivery_risk"
    DATE_COLS = ["order date (DateOrders)", "shipping date (DateOrders)"]
    SENSITIVE_COLS = ["Customer Email", "Customer Password", "Customer Fname", "Customer Lname", "Customer Street"]

    def clean(self, df: pd.DataFrame, dataset_key: str = "historical") -> tuple[pd.DataFrame, dict]:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Executing Data Cleaning for '{dataset_key}'...")
        initial_rows = len(df)
        initial_cols = len(df.columns)

        # 1. Deduplication (as in reference notebook Cell 0)
        df_clean = df.drop_duplicates().copy()
        duplicates_removed = initial_rows - len(df_clean)

        # 2. Date parsing
        for col in self.DATE_COLS:
            if col in df_clean.columns:
                df_clean[col] = pd.to_datetime(df_clean[col], errors="coerce")

        # 3. Target integrity check
        if self.TARGET_COL not in df_clean.columns:
            raise KeyError(f"Target column '{self.TARGET_COL}' not found in dataset!")

        invalid_targets = (~df_clean[self.TARGET_COL].isin([0, 1])).sum()
        if invalid_targets > 0:
            print(f"Warning: Dropping {invalid_targets} rows with invalid target values.")
            df_clean = df_clean[df_clean[self.TARGET_COL].isin([0, 1])].copy()

        # 4. Sensitive columns removal (PII protection)
        cols_to_drop = [c for c in self.SENSITIVE_COLS if c in df_clean.columns]
        df_clean = df_clean.drop(columns=cols_to_drop)

        # 5. Missing values assessment
        missing_summary = df_clean.isnull().sum()
        missing_report = {col: int(count) for col, count in missing_summary.items() if count > 0}

        report = {
            "dataset_key": dataset_key,
            "initial_rows": initial_rows,
            "final_rows": len(df_clean),
            "duplicates_removed": duplicates_removed,
            "initial_columns": initial_cols,
            "final_columns": len(df_clean.columns),
            "dropped_sensitive_columns": cols_to_drop,
            "missing_values_per_column": missing_report,
            "target_distribution": {
                "0 (On Time / Advance)": int((df_clean[self.TARGET_COL] == 0).sum()),
                "1 (Late Delivery)": int((df_clean[self.TARGET_COL] == 1).sum()),
                "late_delivery_rate": round(float(df_clean[self.TARGET_COL].mean()), 4)
            },
            "cleaned_at": datetime.utcnow().isoformat() + "Z"
        }

        # Save processed data and report
        processed_dir = os.path.join(DATA_DIR, "processed", dataset_key)
        os.makedirs(processed_dir, exist_ok=True)
        cleaned_csv_path = os.path.join(processed_dir, "cleaned_dataset.csv")
        df_clean.to_csv(cleaned_csv_path, index=False)

        report_path = os.path.join(REPORTS_DIR, f"data_cleaning_report_{dataset_key}.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cleaning complete: {len(df_clean):,} rows kept. Late rate: {report['target_distribution']['late_delivery_rate']:.2%}")
        return df_clean, report
