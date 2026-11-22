"""data_cleaning.py - Phase 4. Cleans types/labels/invalid rows. Imputation is NOT done here (it happens inside the
sklearn pipeline, fitted on training data only, to avoid leakage)."""
import pandas as pd
from load_data import TARGET
from feature_engineering import standardize_categories, parse_order_date, RAW_DATE

PRIVATE_COLS = ["Customer Email", "Customer Password", "Customer Fname", "Customer Lname", "Customer Street"]
ZIP_COLS = ["Customer Zipcode", "Order Zipcode"]

def clean_data(df):
    """Return (cleaned_df, summary_df). The raw dataframe is never modified."""
    log = []
    def note(step, affected, detail):
        log.append({"step": step, "rows_or_values_affected": int(affected), "detail": detail})
    out = df.copy()
    n0 = len(out)

    # 1. Target validation (stop if invalid - never silently modify the target)
    bad = (~out[TARGET].isin([0, 1])).sum()
    if bad:
        raise ValueError(f"Target has {bad} invalid values; stop and investigate.")
    note("target validation", 0, "Late_delivery_risk contains only 0/1; target not modified")

    # 2. Exact duplicate rows
    dups = out.duplicated().sum()
    out = out.drop_duplicates()
    note("duplicate rows", dups, "exact duplicate rows removed (0 found)" if dups == 0 else "removed")

    # 3. Inconsistent target within one order
    incons = (out.groupby("Order Id")[TARGET].nunique() > 1).sum()
    if incons:
        raise ValueError(f"{incons} orders have inconsistent target labels; stop and investigate.")
    note("target consistency per order", 0, "no order has conflicting labels")

    # 4. Whitespace / label standardisation (same function used at inference)
    text_cols = [c for c in out.columns if out[c].dtype.kind in "OTU" or str(out[c].dtype) in ("str", "string")]
    text_cols = [c for c in text_cols if c not in PRIVATE_COLS + [RAW_DATE, "shipping date (DateOrders)", "Product Image"]]
    before = out[text_cols].copy()
    out[text_cols] = standardize_categories(out[text_cols], text_cols)
    changed = int((before.astype(str) != out[text_cols].astype(str)).sum().sum())
    note("text standardisation", changed, "collapsed repeated spaces (e.g. 'South of  USA'); Customer Country 'EE. UU.' -> 'United States'")

    # 5. Dates
    out[RAW_DATE] = parse_order_date(out[RAW_DATE])
    out["shipping date (DateOrders)"] = pd.to_datetime(out["shipping date (DateOrders)"], format="%m/%d/%Y %H:%M", errors="coerce")
    bad_dates = int(out[RAW_DATE].isna().sum())
    if bad_dates:
        out = out[out[RAW_DATE].notna()]
    note("invalid order dates", bad_dates, "rows with unparseable order date removed (0 found)" if bad_dates == 0 else "removed")

    # 6. Postal codes -> strings (never numeric, never invented)
    for c in ZIP_COLS:
        out[c] = out[c].map(lambda v: None if pd.isna(v) else str(int(v)))
    note("postal codes", 0, "stored as strings; missing values left missing (Order Zipcode 86.24% missing; excluded from model)")

    # 7. Numeric range validation (rows violating basic business rules are removed and counted)
    rules = {"Order Item Quantity<=0": out["Order Item Quantity"] <= 0,
             "Order Item Product Price<0": out["Order Item Product Price"] < 0,
             "Sales<0": out["Sales"] < 0,
             "Discount rate outside [0,1]": ~out["Order Item Discount Rate"].between(0, 1)}
    invalid = pd.concat(rules, axis=1).any(axis=1)
    for k, v in rules.items():
        note("range check: " + k, v.sum(), "violations found")
    out = out[~invalid]

    # 8. Columns removed from the cleaned file
    empty = [c for c in out.columns if out[c].isna().all()]
    out = out.drop(columns=empty)
    note("fully-missing columns dropped", len(empty), f"{empty}")
    out = out.drop(columns=[c for c in PRIVATE_COLS if c in out.columns])
    note("personal/credential columns dropped from cleaned file", len(PRIVATE_COLS),
         "Customer Email/Password/Fname/Lname/Street removed so personal data is not propagated downstream")

    # 9. Missing values report (handled later inside the pipeline)
    remaining = out.isna().sum()
    remaining = remaining[remaining > 0]
    note("remaining missing values", remaining.sum(), f"{remaining.to_dict()} - numeric: median / categorical: 'Unknown' inside the pipeline (train-fitted)")
    note("label limitation (kept, documented)", int(out['Order Status'].isin(['CANCELED', 'SUSPECTED_FRAUD']).sum()),
         "CANCELED/SUSPECTED_FRAUD orders are always labelled 0; not removable at order time (status unknown) - treated as label noise")
    note("final row count", len(out), f"{n0 - len(out)} rows removed in total; Order Id / Order Item Id preserved for grouping")
    return out.reset_index(drop=True), pd.DataFrame(log)
