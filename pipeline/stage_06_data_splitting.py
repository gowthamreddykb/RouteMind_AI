"""
stage_06_data_splitting.py - Stage 6: Data Splitting (Stratified & Group-Aware)
Implements stratified splitting per reference notebook Cell 1 (train_test_split with stratify=y),
while preserving Order Id integrity to prevent order-level data leakage.
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from datetime import datetime
try:
    from pipeline.config import DATA_DIR, REPORTS_DIR
except ImportError:
    from config import DATA_DIR, REPORTS_DIR

class DataSplitting:
    TARGET_COL = "Late_delivery_risk"

    def split_data(self, df: pd.DataFrame, dataset_key: str = "historical", test_size: float = 0.20, val_size: float = 0.10, random_state: int = 42) -> dict:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Executing Data Splitting for '{dataset_key}'...")

        # If Order Id exists, perform group-aware split to avoid order item leakage
        if "Order Id" in df.columns:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Applying group-aware splitting on 'Order Id'...")
            order_target = df.groupby("Order Id")[self.TARGET_COL].max()
            unique_orders = order_target.index.values
            order_labels = order_target.values

            # Train + Val vs Test
            tr_val_orders, te_orders, y_tr_val, y_te = train_test_split(
                unique_orders, order_labels, test_size=test_size, random_state=random_state, stratify=order_labels
            )

            # Train vs Val
            relative_val = val_size / (1.0 - test_size)
            tr_orders, va_orders, _, _ = train_test_split(
                tr_val_orders, y_tr_val, test_size=relative_val, random_state=random_state, stratify=y_tr_val
            )

            tr_mask = df["Order Id"].isin(set(tr_orders))
            va_mask = df["Order Id"].isin(set(va_orders))
            te_mask = df["Order Id"].isin(set(te_orders))

            df_train = df[tr_mask].copy().reset_index(drop=True)
            df_val = df[va_mask].copy().reset_index(drop=True)
            df_test = df[te_mask].copy().reset_index(drop=True)
        else:
            # Fallback to direct stratified split (notebook Cell 1)
            y = df[self.TARGET_COL]
            df_tr_val, df_test = train_test_split(df, test_size=test_size, random_state=random_state, stratify=y)
            relative_val = val_size / (1.0 - test_size)
            df_train, df_val = train_test_split(df_tr_val, test_size=relative_val, random_state=random_state, stratify=df_tr_val[self.TARGET_COL])

        splits_dir = os.path.join(DATA_DIR, "splits", dataset_key)
        os.makedirs(splits_dir, exist_ok=True)

        summary = {
            "dataset_key": dataset_key,
            "train_rows": len(df_train),
            "val_rows": len(df_val),
            "test_rows": len(df_test),
            "total_rows": len(df),
            "train_late_rate": round(float(df_train[self.TARGET_COL].mean()), 4),
            "val_late_rate": round(float(df_val[self.TARGET_COL].mean()), 4),
            "test_late_rate": round(float(df_test[self.TARGET_COL].mean()), 4),
            "random_state": random_state,
            "split_at": datetime.utcnow().isoformat() + "Z"
        }

        with open(os.path.join(REPORTS_DIR, f"data_split_summary_{dataset_key}.json"), "w") as f:
            json.dump(summary, f, indent=2)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Split complete: Train={len(df_train):,} ({summary['train_late_rate']:.2%}), Val={len(df_val):,} ({summary['val_late_rate']:.2%}), Test={len(df_test):,} ({summary['test_late_rate']:.2%})")

        return {
            "train": df_train,
            "val": df_val,
            "test": df_test,
            "summary": summary
        }
