"""data_splitting.py - Phase 6: chronological, order-group-safe 70/15/15 split."""
import numpy as np
import pandas as pd
from load_data import TARGET
from feature_engineering import RAW_DATE

def group_chronological_split(df, train_frac=0.70, val_frac=0.15):
    """Whole orders are sorted by order date; oldest -> train, next -> validation, newest -> test.
    Every row of one Order Id stays in the same partition. Returns a Series of 'train'/'val'/'test'."""
    orders = df.groupby("Order Id").agg(date=(RAW_DATE, "min"), n=("Order Id", "size")).reset_index()
    orders = orders.sort_values(["date", "Order Id"]).reset_index(drop=True)
    cum = orders["n"].cumsum() / orders["n"].sum()
    orders["split"] = np.where(cum <= train_frac, "train", np.where(cum <= train_frac + val_frac, "val", "test"))
    return df["Order Id"].map(orders.set_index("Order Id")["split"])

def split_summary(df, split):
    rows = []
    for name in ["train", "val", "test"]:
        part = df[split == name]
        rows.append({"partition": name, "rows": len(part), "row_pct": round(100 * len(part) / len(df), 3),
                     "unique_orders": part["Order Id"].nunique(),
                     "date_min": part[RAW_DATE].min(), "date_max": part[RAW_DATE].max(),
                     "late_count": int(part[TARGET].sum()), "not_late_count": int((part[TARGET] == 0).sum()),
                     "late_rate": round(part[TARGET].mean(), 4)})
    return pd.DataFrame(rows)

def validate_split(df, split):
    """Raises on any overlap; returns text report. Chronology is non-strict at boundaries (equal minute timestamps)."""
    ids = {n: set(df.loc[split == n, "Order Id"]) for n in ["train", "val", "test"]}
    lines, ok = [], True
    for a, b in [("train", "val"), ("train", "test"), ("val", "test")]:
        ov = len(ids[a] & ids[b]); ok &= ov == 0
        lines.append(f"Order Id overlap {a} vs {b}: {ov}  -> {'PASS' if ov == 0 else 'FAIL'}")
    d = {n: df.loc[split == n, RAW_DATE] for n in ids}
    chrono = d["train"].max() <= d["val"].min() and d["val"].max() <= d["test"].min()
    lines.append(f"Chronological order preserved (max train <= min val, max val <= min test): {'PASS' if chrono else 'FAIL'}")
    ok &= chrono
    lines.append(f"Every row assigned: {'PASS' if split.notna().all() else 'FAIL'}")
    ok &= bool(split.notna().all())
    for n in ids:
        lines.append(f"Both classes present in {n}: {'PASS' if df.loc[split == n, TARGET].nunique() == 2 else 'FAIL'}")
    if not ok:
        raise RuntimeError("Split validation FAILED:\n" + "\n".join(lines))
    return "\n".join(lines)
