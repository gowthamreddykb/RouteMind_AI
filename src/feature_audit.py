"""feature_audit.py - Phase 2 & 3: feature availability audit, leakage audit, and the leakage guard."""
import pandas as pd
from load_data import CANDIDATES, PROHIBITED, TARGET

# column -> (available_at_order_time, leakage_risk, decision, reason)
SPEC = {
 "Type": ("Yes", "Low", "Include", "Payment type is chosen when the order is placed."),
 "Days for shipment (scheduled)": ("Yes", "Low", "Include", "Promised duration, known at order time. NOTE: 1-to-1 with Shipping Mode (0/1/2/4 days), so partly redundant; kept as scheduled_days."),
 "Shipping Mode": ("Yes", "Low", "Include", "Chosen by customer at order time. Strongest signal in the data."),
 "order date (DateOrders)": ("Yes", "Low", "Include", "Order timestamp; used to derive calendar features and for the chronological split. Raw timestamp itself is not passed to the model."),
 "Category Id": ("Yes", "Low", "Exclude", "Identifier code. Verified NOT strictly 1-to-1 with Category Name (51 ids vs 50 names: one name maps to two ids), but the extra id carries no business meaning; Category Name is kept instead."),
 "Category Name": ("Yes", "Low", "Include", "Product category, known at order time."),
 "Department Id": ("Yes", "Low", "Exclude", "Identifier code; Department Name carries the same information."),
 "Department Name": ("Yes", "Low", "Include", "Known at order time."),
 "Product Card Id": ("Yes", "Low", "Exclude", "Identifier code; Product Name carries the same information (1-to-1)."),
 "Product Category Id": ("Yes", "Low", "Exclude", "Identical to Category Id in 100% of rows."),
 "Product Name": ("Yes", "Low", "Include", "118 values - moderate cardinality, known at order time."),
 "Product Price": ("Yes", "Low", "Exclude", "Identical to Order Item Product Price in 100% of rows."),
 "Order Item Product Price": ("Yes", "Low", "Include", "Unit price at order time."),
 "Order Item Quantity": ("Yes", "Low", "Include", "Quantity ordered."),
 "Customer Segment": ("Yes", "Low", "Include", "Customer attribute known at order time."),
 "Customer City": ("Yes", "Low", "Include", "563 values; rare categories must be grouped in the encoder."),
 "Customer Country": ("Yes", "Low", "Include", "Only 2 values (Puerto Rico / EE. UU.). Low information."),
 "Customer State": ("Yes", "Low", "Include", "Known at order time."),
 "Market": ("Yes", "Low", "Include", "Destination market."),
 "Order City": ("Yes", "Low", "Review", "3,597 values - very high cardinality. Decide by validation ablation, with rare-category grouping."),
 "Order Country": ("Yes", "Low", "Include", "164 values; rare categories grouped in the encoder."),
 "Order Region": ("Yes", "Low", "Include", "Destination region."),
 "Order State": ("Yes", "Low", "Review", "1,089 values - high cardinality. Decide by validation ablation."),
 "Latitude": ("Conditional", "Medium", "Review", "VERIFIED to be the CUSTOMER location (e.g. Order City Bekasi, Indonesia has lat 18.25 = Puerto Rico), NOT the destination. Available at order time but duplicates Customer City/State. Decide by ablation."),
 "Longitude": ("Conditional", "Medium", "Review", "Same as Latitude: customer location, not destination."),
 "Order Item Discount": ("Yes", "Low", "Exclude", "Equals Discount Rate x Sales (redundant)."),
 "Order Item Discount Rate": ("Yes", "Low", "Include", "Known at order time; used for discount_level."),
 "Sales": ("Yes", "Low", "Include", "Item price x quantity (verified); used for order_value."),
 "Order Item Total": ("Yes", "Low", "Exclude", "Sales minus discount (matches in 97.4% rows) - redundant combination of included fields."),
}

def _row(col, df, stage, avail, leak, decision, reason):
    return {"Original column name": col, "Data type": str(df[col].dtype),
            "Missing count": int(df[col].isna().sum()),
            "Missing percentage": round(df[col].isna().mean() * 100, 4),
            "Prediction stage": stage, "Available at prediction time": avail,
            "Leakage risk": leak, "Final decision": decision, "Reason": reason}

def verify_redundancy(df):
    """Programmatically confirm the 'redundant' claims used in SPEC (printed for transparency)."""
    pairs = [("Category Id", "Category Name"), ("Department Id", "Department Name"),
             ("Product Card Id", "Product Name"), ("Category Id", "Product Category Id")]
    print("\nRedundancy verification (1-to-1 mappings):")
    for a, b in pairs:
        one = df.groupby(a)[b].nunique().max() == 1 and df.groupby(b)[a].nunique().max() == 1
        print(f"  {a} <-> {b}: {'1-to-1' if one else 'NOT 1-to-1'}")
    print("  Product Price == Order Item Product Price:", bool((df['Product Price'] == df['Order Item Product Price']).all()))

def _apply(c, overrides):
    a, l, d, r = SPEC[c]
    if c in overrides:
        d, extra = overrides[c]
        r = r + " | RESOLVED by validation ablation: " + extra
    return a, l, d, r

def _risk(cat):
    return "High" if (cat == "Target" or "leak" in cat.lower()) else "Medium"

def build_audits(df, reports_dir, overrides=None):
    """overrides = {column: (decision, extra_reason)} used to resolve Review items after validation ablation."""
    overrides = overrides or {}
    # Order-creation audit
    rows = [_row(c, df, "Order creation", *_apply(c, overrides)) for c in CANDIDATES]
    rows += [_row(c, df, "Order creation", "No", _risk(cat), "Exclude", r)
             for c, cat, r in PROHIBITED if c in df.columns]
    oc = pd.DataFrame(rows); oc.to_csv(f"{reports_dir}/order_creation_feature_audit.csv", index=False)

    # Dispatch audit: same order-time features, plus the dispatch-specific question
    rows = []
    for c in CANDIDATES:
        a, l, d, r = _apply(c, overrides)
        rows.append(_row(c, df, "Dispatch", a, l, d, r + " (Order-time feature carried into dispatch stage.)"))
    for c, cat, r in PROHIBITED:
        if c not in df.columns:
            continue
        if c == "shipping date (DateOrders)":
            r = ("NOT a genuine dispatch timestamp: it equals order date + actual shipping days (0/1 days -> 0.5, 2->2.0, ... 6->6.0). "
                 "Using it, or dispatch_* / hours_to_dispatch derived from it, would leak the delivery outcome.")
            rows.append(_row(c, df, "Dispatch", "No", "High", "Exclude", r))
        else:
            rows.append(_row(c, df, "Dispatch", "No", _risk(cat), "Exclude", r))
    dp = pd.DataFrame(rows); dp.to_csv(f"{reports_dir}/dispatch_feature_audit.csv", index=False)

    leak = pd.DataFrame([{"Excluded column": c, "Category": cat, "Reason": r} for c, cat, r in PROHIBITED])
    leak.to_csv(f"{reports_dir}/leakage_audit_report.csv", index=False)
    return oc, dp, leak

def approved_features(audit_df, include_review=False):
    ok = ["Include"] + (["Review"] if include_review else [])
    mask = audit_df["Final decision"].isin(ok) & audit_df["Original column name"].isin(CANDIDATES)
    return audit_df.loc[mask, "Original column name"].tolist()

def assert_no_prohibited(feature_cols, target=TARGET):
    """Leakage guard: stop training with a readable error if anything prohibited is in the feature list."""
    banned = {c for c, _, _ in PROHIBITED}
    if target in feature_cols:
        raise ValueError(f"STOP: target '{target}' is in the feature list.")
    bad = sorted(set(feature_cols) & banned)
    if bad:
        raise ValueError(f"STOP: prohibited/leaky columns found in feature list: {bad}. Remove them before training.")
    return True


# ---------------------------------------------------------------------------------------------
# Evidence-backed leakage checks (numbers are computed from the data, not assumed)
# ---------------------------------------------------------------------------------------------
def leakage_evidence(df):
    import numpy as np
    ev = {}
    late = df[TARGET]
    ev["Days for shipping (real)"] = f"late == (real > scheduled) in {((df['Days for shipping (real)'] > df['Days for shipment (scheduled)']).astype(int) == late).mean() * 100:.2f}% of rows"
    ev["Delivery Status"] = "'Late delivery' rows have target=1 in %.1f%% of cases; all other statuses have target=0" % (late[df['Delivery Status'] == 'Late delivery'].mean() * 100)
    rate = df.groupby("Order Status")[TARGET].mean().round(3).to_dict()
    ev["Order Status"] = f"late rate by status {rate}: CANCELED and SUSPECTED_FRAUD are always 0 -> status is a post-order outcome that leaks the label"
    ev["Product Status"] = f"{df['Product Status'].nunique()} distinct value(s): {df['Product Status'].unique().tolist()} (constant, no information)"
    ev["Order Profit Per Order"] = f"identical to 'Benefit per order' in {np.isclose(df['Order Profit Per Order'], df['Benefit per order']).mean() * 100:.1f}% of rows; correlation with target {df[[TARGET, 'Order Profit Per Order']].corr().iloc[0, 1]:.3f}; profit is only final after fulfilment"
    ev["Benefit per order"] = "duplicate of Order Profit Per Order (see above)"
    ev["Order Item Profit Ratio"] = f"correlation with target {df[[TARGET, 'Order Item Profit Ratio']].corr().iloc[0, 1]:.3f}; derived from profit (post-fulfilment)"
    ev["Sales per customer"] = f"identical to 'Order Item Total' in {np.isclose(df['Sales per customer'], df['Order Item Total']).mean() * 100:.1f}% of rows (not a true per-customer aggregate; redundant)"
    ev["Order Item Cardprod Id"] = f"identical to Product Card Id in {(df['Order Item Cardprod Id'] == df['Product Card Id']).mean() * 100:.1f}% of rows"
    ev["Product Description"] = f"{df['Product Description'].isna().sum():,} of {len(df):,} values missing"
    ev["Order Zipcode"] = f"{df['Order Zipcode'].isna().mean() * 100:.4f}% missing"
    ev["Customer Zipcode"] = f"{df['Customer Zipcode'].isna().sum()} missing; {df['Customer Zipcode'].nunique()} distinct codes"
    od = pd.to_datetime(df["order date (DateOrders)"], format="%m/%d/%Y %H:%M")
    sd = pd.to_datetime(df["shipping date (DateOrders)"], format="%m/%d/%Y %H:%M")
    gap = (sd - od).dt.total_seconds() / 86400
    by_real = gap.groupby(df["Days for shipping (real)"]).agg(["min", "max"]).round(2)
    ev["shipping date (DateOrders)"] = ("gap (shipping date - order date, days) by Days for shipping (real): "
        + "; ".join(f"{k}->{r['min']}..{r['max']}" for k, r in by_real.iterrows())
        + f"; correlation with real duration {np.corrcoef(gap, df['Days for shipping (real)'])[0, 1]:.4f} => derived from the outcome, not a dispatch event")
    ev["Customer Id"] = f"{df['Customer Id'].nunique():,} distinct ids; identifier"
    return ev

def write_leakage_report(df, reports_dir):
    ev = leakage_evidence(df)
    rows = [{"Excluded column": c, "Category": cat, "Reason": r, "Evidence (computed)": ev.get(c, "")}
            for c, cat, r in PROHIBITED]
    for c in ["Order City", "Order State", "Latitude", "Longitude"]:   # conditionally approved items
        rows.append({"Excluded column": c + " (conditionally approved)", "Category": "Review",
                     "Reason": SPEC[c][3], "Evidence (computed)": "see validation ablation in training_summary / report"})
    pd.DataFrame(rows).to_csv(f"{reports_dir}/leakage_audit_report.csv", index=False)

# ---------------------------------------------------------------------------------------------
# Stage availability report, approved/excluded lists and feature dictionary
# ---------------------------------------------------------------------------------------------
DESCRIPTIONS = {
 "Type": "Payment type (DEBIT/TRANSFER/CASH/PAYMENT)", "Days for shipment (scheduled)": "Promised shipping days at order time (determined by Shipping Mode)",
 "Shipping Mode": "Shipping service chosen by customer", "order date (DateOrders)": "Order creation timestamp",
 "Category Name": "Product category", "Department Name": "Store department", "Product Name": "Product (118 distinct)",
 "Order Item Product Price": "Unit price of the item", "Order Item Quantity": "Units ordered in this item row",
 "Customer Segment": "Consumer / Corporate / Home Office", "Customer City": "Customer city", "Customer Country": "Customer country (Puerto Rico / United States)",
 "Customer State": "Customer state", "Market": "Destination market (5 values)", "Order Country": "Destination country", "Order Region": "Destination region",
 "Order City": "Destination city (3,597 values)", "Order State": "Destination state (1,089 values)",
 "Latitude": "Customer location latitude (verified: not destination)", "Longitude": "Customer location longitude (verified: not destination)",
 "Order Item Discount Rate": "Discount fraction applied (0-0.25)", "Sales": "Item price x quantity",
 "scheduled_days": "Engineered: renamed Days for shipment (scheduled)", "order_value": "Engineered: renamed Sales",
 "order_year": "Engineered from order date", "order_month": "Engineered from order date", "order_day": "Engineered from order date",
 "order_day_of_week": "Engineered from order date (Monday=0)", "order_hour": "Engineered from order date", "is_weekend": "Engineered: Saturday/Sunday flag",
}
def _kind(df, c):
    if "date" in c.lower() and "DateOrders" in c: return "Date"
    return "Numerical" if df[c].dtype.kind in "fi" else "Categorical"

def write_stage_reports(df, oc, reports_dir):
    """prediction_stage_availability_report, approved/excluded feature lists, feature_dictionary."""
    cand_dec = dict(zip(oc["Original column name"], oc["Final decision"]))
    reason = dict(zip(oc["Original column name"], oc["Reason"]))
    risk = dict(zip(oc["Original column name"], oc["Leakage risk"]))
    rows = []
    for c in df.columns:
        if c in CANDIDATES:
            a = SPEC[c][0]; avail = {"Yes": "Yes", "Conditional": "Review"}[a]
            rows.append({"Feature Name": c, "Order Creation Availability": avail, "Dispatch Availability": avail,
                         "Data Type": _kind(df, c), "Leakage Risk": risk[c], "Missing Percentage": round(df[c].isna().mean() * 100, 4),
                         "Decision": cand_dec[c], "Reason": reason[c]})
        else:
            rows.append({"Feature Name": c, "Order Creation Availability": "No",
                         "Dispatch Availability": "No",
                         "Data Type": _kind(df, c), "Leakage Risk": risk.get(c, "Medium"), "Missing Percentage": round(df[c].isna().mean() * 100, 4),
                         "Decision": "Exclude", "Reason": reason.get(c, "")})
    stage = pd.DataFrame(rows)
    stage.to_csv(f"{reports_dir}/prediction_stage_availability_report.csv", index=False)
    stage[stage.Decision == "Include"].to_csv(f"{reports_dir}/approved_feature_list.csv", index=False)
    stage[stage.Decision != "Include"].to_csv(f"{reports_dir}/excluded_feature_list.csv", index=False)
    fd = [{"Feature": c, "Description": d, "Used by model": "Yes", "Stage": "Order creation"} for c, d in DESCRIPTIONS.items()
          if c in ["scheduled_days", "order_value", "order_year", "order_month", "order_day", "order_day_of_week", "order_hour", "is_weekend"]
          or cand_dec.get(c) == "Include"]
    for c, cat, r in PROHIBITED:
        fd.append({"Feature": c, "Description": r, "Used by model": "No", "Stage": cat})
    pd.DataFrame(fd).to_csv(f"{reports_dir}/feature_dictionary.csv", index=False)
    return stage
