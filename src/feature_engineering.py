"""feature_engineering.py - ONE shared set of transformations used for training AND for Flask inference.

The function engineer_order_features() takes RAW DataCo-style columns and returns the model features.
It is the first step of the saved sklearn Pipeline, so Flask can pass raw fields straight in.
Only order-creation information is used. Nothing here touches delivery outcomes.
"""
import re
import numpy as np
import pandas as pd

RAW_DATE = "order date (DateOrders)"

# Raw fields a caller must supply for the order-creation model (all known when the order is placed)
BASE_RAW_FIELDS = [
    "Type", "Days for shipment (scheduled)", "Shipping Mode", RAW_DATE, "Category Name", "Department Name",
    "Product Name", "Order Item Product Price", "Order Item Quantity", "Customer Segment", "Customer City",
    "Customer Country", "Customer State", "Market", "Order Country", "Order Region",
    "Order Item Discount Rate", "Sales",
]
# Columns whose inclusion is decided by validation ablation (Phase 3 'Review' items)
REVIEW_NUMERIC = ["Latitude", "Longitude"]
REVIEW_CATEGORICAL = ["Order City", "Order State"]

NUMERIC_BASE = ["scheduled_days", "order_value", "Order Item Product Price", "Order Item Quantity",
                "Order Item Discount Rate", "order_year", "order_month", "order_day",
                "order_day_of_week", "order_hour", "is_weekend"]
CATEGORICAL_BASE = ["Type", "Shipping Mode", "Category Name", "Department Name", "Product Name",
                    "Customer Segment", "Customer City", "Customer Country", "Customer State",
                    "Market", "Order Country", "Order Region"]

COUNTRY_FIX = {"EE. UU.": "United States"}   # Spanish abbreviation for USA, the only inconsistent label found

def normalize_text(series):
    """Strip + collapse repeated whitespace; keep missing values as NaN (object dtype)."""
    s = series.astype(object)
    return s.map(lambda v: np.nan if pd.isna(v) else re.sub(r"\s+", " ", str(v)).strip())

def standardize_categories(df, cols):
    """Same standardisation for training and inference (whitespace + country label)."""
    out = df.copy()
    for c in cols:
        out[c] = normalize_text(out[c])
    if "Customer Country" in cols:
        out["Customer Country"] = out["Customer Country"].replace(COUNTRY_FIX)
    return out

def parse_order_date(series):
    """Parse DataCo format 'm/d/Y H:M'; fall back to general parsing (ISO strings, datetimes). Invalid -> NaT."""
    out = pd.to_datetime(series, format="%m/%d/%Y %H:%M", errors="coerce")
    bad = out.isna() & series.notna()
    if bad.any():
        out[bad] = pd.to_datetime(series[bad], errors="coerce")
    return out

def feature_lists(extra_cols=(), hist_cols=()):
    """Return (numeric_features, categorical_features) for approved review columns and optional historical-rate columns."""
    num = NUMERIC_BASE + [c for c in REVIEW_NUMERIC if c in extra_cols] + list(hist_cols)
    cat = CATEGORICAL_BASE + [c for c in REVIEW_CATEGORICAL if c in extra_cols]
    return num, cat

def engineer_order_features(raw, extra_cols=(), hist_cols=()):
    """RAW columns -> model feature table (numeric columns first, then categorical).
    hist_cols are leakage-safe historical-rate columns added upstream by historical_features (past outcomes only)."""
    extra_cols = list(extra_cols); hist_cols = list(hist_cols)
    missing = [c for c in BASE_RAW_FIELDS + extra_cols + hist_cols if c not in raw.columns]
    if missing:
        raise KeyError(f"Missing required raw fields: {missing}")
    d = parse_order_date(raw[RAW_DATE])
    out = pd.DataFrame(index=raw.index)
    out["scheduled_days"] = pd.to_numeric(raw["Days for shipment (scheduled)"], errors="coerce")
    out["order_value"] = pd.to_numeric(raw["Sales"], errors="coerce")
    for c in ["Order Item Product Price", "Order Item Quantity", "Order Item Discount Rate"]:
        out[c] = pd.to_numeric(raw[c], errors="coerce")
    out["order_year"] = d.dt.year.astype(float)
    out["order_month"] = d.dt.month.astype(float)
    out["order_day"] = d.dt.day.astype(float)
    out["order_day_of_week"] = d.dt.dayofweek.astype(float)      # Monday = 0
    out["order_hour"] = d.dt.hour.astype(float)
    out["is_weekend"] = (d.dt.dayofweek >= 5).astype(float).where(d.notna())
    for c in REVIEW_NUMERIC:
        if c in extra_cols:
            out[c] = pd.to_numeric(raw[c], errors="coerce")
    for c in hist_cols:
        out[c] = pd.to_numeric(raw[c], errors="coerce")
    cats = CATEGORICAL_BASE + [c for c in REVIEW_CATEGORICAL if c in extra_cols]
    std = standardize_categories(raw[cats], cats)
    for c in cats:
        out[c] = std[c]
    return out

def engineering_report(raw, extra_cols=()):
    """Table describing every engineered feature (written to reports/feature_engineering_report.csv)."""
    feats = engineer_order_features(raw, extra_cols)
    src = {"scheduled_days": "Days for shipment (scheduled)", "order_value": "Sales",
           "order_year": RAW_DATE, "order_month": RAW_DATE, "order_day": RAW_DATE,
           "order_day_of_week": RAW_DATE, "order_hour": RAW_DATE, "is_weekend": RAW_DATE}
    rows = []
    for c in feats.columns:
        rows.append({"feature": c, "source_column": src.get(c, c),
                     "kind": "engineered" if c in src else "passed through (standardised)",
                     "dtype": str(feats[c].dtype), "missing_count": int(feats[c].isna().sum()),
                     "min": feats[c].min() if feats[c].dtype.kind in "fi" else "",
                     "max": feats[c].max() if feats[c].dtype.kind in "fi" else "",
                     "note": {"scheduled_days": "Renamed raw column (raw column not kept: avoids duplicate)",
                              "order_value": "Renamed Sales (avoids duplicate)"}.get(c, "")})
    rows.append({"feature": "(not created) order_quarter", "source_column": RAW_DATE, "kind": "skipped",
                 "note": "Redundant with order_month"})
    rows.append({"feature": "(not created) discount_level", "source_column": "Order Item Discount Rate", "kind": "skipped",
                 "note": "Rate has only 18 distinct values; bucketing adds no information"})
    rows.append({"feature": "(not created) dispatch_* / hours_to_dispatch", "source_column": "shipping date (DateOrders)",
                 "kind": "skipped", "note": "Source column is not a real dispatch timestamp (leakage) - see audits"})
    return pd.DataFrame(rows)
