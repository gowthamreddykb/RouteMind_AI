"""
stage_04_feature_engineering.py - Stage 4: Feature Engineering & Preprocessing Pipeline
Constructs domain-aligned features for Order Creation and Dispatch stages.
Implements the exact ColumnTransformer architecture from reference notebook Cell 2:
- Numeric: SimpleImputer(strategy='median') + StandardScaler
- Categorical: SimpleImputer(strategy='most_frequent') + OneHotEncoder(handle_unknown='ignore')
Strictly blocks data leakage by dropping all post-delivery columns.
"""

import os
import json
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

class FeatureEngineering:
    # Prohibited columns (Strict Leakage Prevention)
    PROHIBITED_LEAKAGE_COLUMNS = [
        "Days for shipping (real)",
        "Delivery Status",
        "Delivery Status.1",
        "Delivery Status.2",
        "Order Status.1",
        "Order Status.2",
        "Late_delivery_risk"  # Target must never be in feature matrix
    ]

    # Model 01: Order Creation Features (Information available at checkout)
    ORDER_CREATION_NUMERIC = [
        "Days for shipment (scheduled)",
        "Order Item Quantity",
        "Sales",
        "Order Item Product Price",
        "Order Item Discount Rate"
    ]
    ORDER_CREATION_CATEGORICAL = [
        "Type",
        "Shipping Mode",
        "Order Region",
        "Market",
        "Order Country",
        "Customer Segment",
        "Category Name"
    ]

    # Model 02: Dispatch Stage Features (Information available when package leaves warehouse)
    DISPATCH_NUMERIC = ORDER_CREATION_NUMERIC + [
        "warehouse_processing_days"
    ]
    DISPATCH_CATEGORICAL = ORDER_CREATION_CATEGORICAL + [
        "Order Status"
    ]

    def build_preprocessor(self, numeric_cols: list[str], categorical_cols: list[str], scale_numeric: bool = True) -> ColumnTransformer:
        """
        Builds the modular ColumnTransformer specified in reference notebook Cell 2,
        with optional scaling for linear algorithms and unscaled passthrough for tree ensembles.
        """
        if scale_numeric:
            num_pipeline = Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler())
            ])
        else:
            num_pipeline = Pipeline([
                ("imputer", SimpleImputer(strategy="median"))
            ])

        cat_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])

        return ColumnTransformer(
            transformers=[
                ("num", num_pipeline, numeric_cols),
                ("cat", cat_pipeline, categorical_cols)
            ]
        )

    def prepare_features(self, df: pd.DataFrame, stage: str = "order_creation") -> tuple[pd.DataFrame, list[str], list[str]]:
        """Prepares features and validates no leakage columns are present."""
        df_feats = df.copy()

        # Feature engineering for dispatch stage
        if stage == "dispatch":
            if "shipping date (DateOrders)" in df_feats.columns and "order date (DateOrders)" in df_feats.columns:
                delta = (pd.to_datetime(df_feats["shipping date (DateOrders)"]) - pd.to_datetime(df_feats["order date (DateOrders)"]))
                df_feats["warehouse_processing_days"] = delta.dt.total_seconds() / (24 * 3600)
                df_feats["warehouse_processing_days"] = df_feats["warehouse_processing_days"].clip(lower=0, upper=10)
            else:
                df_feats["warehouse_processing_days"] = 0.0

            num_cols = [c for c in self.DISPATCH_NUMERIC if c in df_feats.columns]
            cat_cols = [c for c in self.DISPATCH_CATEGORICAL if c in df_feats.columns]
        else:
            num_cols = [c for c in self.ORDER_CREATION_NUMERIC if c in df_feats.columns]
            cat_cols = [c for c in self.ORDER_CREATION_CATEGORICAL if c in df_feats.columns]

        # Verify no prohibited leakage columns in feature set
        selected_cols = num_cols + cat_cols
        for prohibited in self.PROHIBITED_LEAKAGE_COLUMNS:
            if prohibited in selected_cols:
                raise ValueError(f"CRITICAL LEAKAGE DETECTED: Column '{prohibited}' is prohibited in {stage} stage!")

        # Cast categorical columns to string to handle mixed types from Excel/CSV
        for c in cat_cols:
            df_feats[c] = df_feats[c].fillna("Unknown").astype(str)

        # Cast numeric columns to float
        for c in num_cols:
            df_feats[c] = pd.to_numeric(df_feats[c], errors="coerce")

        X = df_feats[selected_cols].copy()
        return X, num_cols, cat_cols
