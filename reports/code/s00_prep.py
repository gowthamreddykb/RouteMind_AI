from common import *

df = pd.read_csv(RAW, encoding="cp1252")
N = len(df)
df["order_dt"] = pd.to_datetime(df["order date (DateOrders)"], format="%m/%d/%Y %H:%M")
df["ship_dt"] = pd.to_datetime(df["shipping date (DateOrders)"], format="%m/%d/%Y %H:%M")
df["real"] = df["Days for shipping (real)"]; df["sched"] = df["Days for shipment (scheduled)"]
df["delay"] = df["real"] - df["sched"]
df["late"] = df["Late_delivery_risk"]
df["canceled_ship"] = df["Delivery Status"].eq("Shipping canceled")
df["line_value"] = df["Order Item Total"]

# ---------- order-level table (one row per Order Id) ----------
g = df.groupby("Order Id")
o = g.agg(order_dt=("order_dt", "first"), ship_dt=("ship_dt", "first"), real=("real", "first"), sched=("sched", "first"),
          delay=("delay", "first"), late=("late", "first"), status=("Delivery Status", "first"),
          order_status=("Order Status", "first"), mode=("Shipping Mode", "first"), cust=("Customer Id", "first"),
          segment=("Customer Segment", "first"), pay_type=("Type", "first"),
          country=("Order Country", "first"), state=("Order State", "first"), city=("Order City", "first"),
          region=("Order Region", "first"), market=("Market", "first"),
          cust_country=("Customer Country", "first"), cust_state=("Customer State", "first"),
          lat=("Latitude", "first"), lon=("Longitude", "first"),
          items=("Order Item Id", "size"), qty=("Order Item Quantity", "sum"), value=("line_value", "sum"),
          gross=("Sales", "sum"), discount=("Order Item Discount", "sum"), profit=("Benefit per order", "sum"),
          disc_rate=("Order Item Discount Rate", "mean"), n_cat=("Category Name", "nunique"),
          cat_first=("Category Name", "first"), dept_first=("Department Name", "first"),
          canceled_ship=("canceled_ship", "first")).reset_index()
o["hour"] = o.order_dt.dt.hour; o["weekday"] = o.order_dt.dt.day_name(); o["wd_n"] = o.order_dt.dt.weekday
o["month"] = o.order_dt.dt.month; o["year"] = o.order_dt.dt.year; o["quarter"] = o.order_dt.dt.quarter
o["ym"] = o.order_dt.dt.to_period("M"); o["date"] = o.order_dt.dt.normalize()
o["week"] = o.order_dt.dt.to_period("W-SUN").dt.start_time
o.to_pickle("orders.pkl"); df.to_pickle("lines.pkl")

ov = o[~o.canceled_ship]
out = folder("data_understanding")

# ---------- data dictionary ----------
M = {  # column: (inferred meaning, group, ML use, availability)
"Type": ("Payment type (DEBIT/TRANSFER/CASH/PAYMENT)", "Order", "Candidate categorical", "Order creation"),
"Days for shipping (real)": ("Actual days between order date and shipping date", "Delivery outcome", "NOT an input (defines target)", "After delivery"),
"Days for shipment (scheduled)": ("Promised days; fixed per Shipping Mode (verified)", "Shipping", "Candidate (redundant with mode)", "Order creation (if mode chosen)"),
"Benefit per order": ("Profit of the order item (identical to Order Profit Per Order)", "Order/finance", "Reject (post-sale finance)", "Unknown"),
"Sales per customer": ("Equals Order Item Total (verified 100%) - net line value, not per-customer", "Order/finance", "Use via order value", "Order creation"),
"Delivery Status": ("Advance shipping / Shipping on time / Late delivery / Shipping canceled", "Delivery outcome", "NOT an input (target source)", "After delivery"),
"Late_delivery_risk": ("1 iff real > scheduled days (verified); 0 for canceled", "Delivery outcome", "TARGET (not an input)", "After delivery"),
"Category Id": ("Category id", "Product", "Same as Product Category Id", "Order creation"),
"Category Name": ("Product category", "Product", "Candidate categorical", "Order creation"),
"Customer City": ("Customer residence city", "Customer", "Weak candidate", "Order creation"),
"Customer Country": ("Customer residence country (EE. UU. / Puerto Rico only)", "Customer", "Low value (2 values)", "Order creation"),
"Customer Email": ("Masked (constant)", "Customer", "Drop", "n/a"),
"Customer Fname": ("First name", "Customer", "Drop (PII)", "n/a"),
"Customer Id": ("Customer identifier", "Customer", "Key for history features only", "Order creation"),
"Customer Lname": ("Last name", "Customer", "Drop (PII)", "n/a"),
"Customer Password": ("Masked (constant)", "Customer", "Drop", "n/a"),
"Customer Segment": ("Consumer / Corporate / Home Office", "Customer", "Candidate categorical", "Order creation"),
"Customer State": ("Customer residence state", "Customer", "Weak candidate", "Order creation"),
"Customer Street": ("Street address", "Customer", "Drop (PII, high cardinality)", "n/a"),
"Customer Zipcode": ("Customer ZIP", "Customer", "Weak candidate", "Order creation"),
"Department Id": ("Department id", "Product", "Redundant with Department Name", "Order creation"),
"Department Name": ("Product department", "Product", "Candidate categorical", "Order creation"),
"Latitude": ("Customer-location latitude (verified by country means)", "Location", "Weak candidate", "Order creation"),
"Longitude": ("Customer-location longitude (verified by country means)", "Location", "Weak candidate", "Order creation"),
"Market": ("5 sales markets", "Location (destination)", "Candidate categorical", "Order creation"),
"Order City": ("Delivery destination city", "Location (destination)", "Candidate (high cardinality)", "Order creation"),
"Order Country": ("Delivery destination country (Spanish names)", "Location (destination)", "Candidate categorical", "Order creation"),
"Order Customer Id": ("Same as Customer Id (verified 100%)", "Customer", "Redundant", "Order creation"),
"order date (DateOrders)": ("Order timestamp (minute resolution)", "Order", "Source of month/weekday/hour", "Order creation"),
"Order Id": ("Order identifier (65,752 unique)", "Order", "Prediction-unit key", "Order creation"),
"Order Item Cardprod Id": ("Product card id (equals Product Card Id)", "Product", "Redundant", "Order creation"),
"Order Item Discount": ("Discount amount on the line", "Order/finance", "Candidate numeric", "Order creation (if discount known)"),
"Order Item Discount Rate": ("Discount rate on the line", "Order/finance", "Candidate numeric", "Order creation (if discount known)"),
"Order Item Id": ("Line-item identifier (unique per row)", "Order line", "Identifier", "Order creation"),
"Order Item Product Price": ("Unit price (equals Product Price)", "Product", "Candidate numeric", "Order creation"),
"Order Item Profit Ratio": ("Profit ratio of the line", "Order/finance", "Reject (post-sale finance)", "Unknown"),
"Order Item Quantity": ("Units on the line (1-5)", "Order line", "Candidate (sum per order)", "Order creation"),
"Sales": ("Price x quantity (verified 100%), before discount", "Order/finance", "Candidate via order value", "Order creation"),
"Order Item Total": ("Sales - discount (verified 100%): net line value", "Order/finance", "Candidate via order value", "Order creation"),
"Order Profit Per Order": ("Identical to Benefit per order; varies by line, not per order", "Order/finance", "Reject", "Unknown"),
"Order Region": ("23 regions (a country maps to up to 4 regions - inconsistent)", "Location (destination)", "Candidate (quality caveat)", "Order creation"),
"Order State": ("Delivery destination state/province", "Location (destination)", "Candidate (high cardinality)", "Order creation"),
"Order Status": ("COMPLETE, PENDING_PAYMENT, ... ; CANCELED+SUSPECTED_FRAUD = Shipping canceled", "Order", "Reject (post-order, partly leaks)", "After order creation"),
"Order Zipcode": ("Destination ZIP (86% missing)", "Location", "Reject (missing)", "n/a"),
"Product Card Id": ("Product id", "Product", "Key", "Order creation"),
"Product Category Id": ("Same as Category Id", "Product", "Redundant", "Order creation"),
"Product Description": ("Entirely empty", "Product", "Drop", "n/a"),
"Product Image": ("Image URL", "Product", "Drop", "n/a"),
"Product Name": ("Product name (118)", "Product", "Candidate (high cardinality)", "Order creation"),
"Product Price": ("List price", "Product", "Candidate numeric", "Order creation"),
"Product Status": ("Constant 0", "Product", "Drop", "n/a"),
"shipping date (DateOrders)": ("Date such that (shipping date - order date) ~ real days: behaves as a completion date", "Delivery outcome", "NOT an input", "After delivery"),
"Shipping Mode": ("Same Day / First Class / Second Class / Standard Class", "Shipping", "Candidate categorical", "Order creation (if selected at checkout)"),
}
raw_cols = list(pd.read_csv(RAW, encoding="cp1252", nrows=1).columns)
rows = []
for c in raw_cols:
    s = df[c]
    rows.append({"Column": c, "Data type": str(s.dtype), "Example": str(s.iloc[0])[:30], "Missing %": round(s.isna().mean() * 100, 2),
                 "Unique": s.nunique(), "Description (inferred - DescriptionDataCo.csv not supplied)": M[c][0], "Group": M[c][1],
                 "Possible ML use": M[c][2], "Availability stage": M[c][3]})
dd = pd.DataFrame(rows); dd.to_csv(f"{out}/data_dictionary.csv", index=False)

r = Report(out, "Data understanding: DataCo supply-chain dataset")
r.sec("Scope and source", f"- File: `DataCoSupplyChainDataset.csv` (cp1252). **{N:,} rows x {len(raw_cols)} columns.**\n- `DescriptionDataCo.csv` and `tokenized_access_logs.csv` were **not supplied**: column meanings below are inferred from names and verified against values, not against official descriptions.")
r.sec("Structure verified", f"""- Unique `Order Id`: **{o.shape[0]:,}**; unique `Order Item Id`: {df['Order Item Id'].nunique():,} (= row count). A row is an **order line item**.
- Lines per order: min {o['items'].min()}, median {o['items'].median():.0f}, max {o['items'].max()}; orders with >1 line: {(o['items']>1).sum():,}.
- Every shipping/delivery/customer/destination field is identical across lines of one order (checked on 10 fields, 0 conflicts), so **the order is the prediction unit**.
- Fully duplicate rows: {df.drop(columns=['order_dt','ship_dt','real','sched','delay','late','canceled_ship','line_value']).duplicated().sum()}.
- Customers: {df['Customer Id'].nunique():,}. Date range (orders): {o.order_dt.min()} to {o.order_dt.max()}.""")
r.sec("Data dictionary", "Full table also in `data_dictionary.csv`.\n")
r.table(dd, maxrows=60)
r.save()

# ---------- data quality ----------
q = []
def add(issue, col, k, base, example, reason, treat, ml):
    q.append({"Issue": issue, "Column(s)": col, "Affected": int(k), "Base": int(base), "% affected": round(100 * k / base, 2),
              "Example": example, "Possible reason": reason, "Recommended treatment": treat, "Affects ML?": ml})
add("Entirely missing", "Product Description", df["Product Description"].isna().sum(), N, "NaN", "Not populated", "Drop", "No")
add("Mostly missing", "Order Zipcode", df["Order Zipcode"].isna().sum(), N, "NaN", "Not collected for most destinations", "Drop; do not impute", "Yes if used")
add("Missing", "Customer Zipcode", df["Customer Zipcode"].isna().sum(), N, "NaN", "Unknown", "Leave missing; do not guess", "Minor")
add("Constant/masked columns", "Customer Email, Customer Password, Product Status", 4 * N, 4 * N, "XXXXXXXXX / 0", "Anonymisation", "Drop", "No")
x = o.groupby("country")["region"].nunique(); k = (o.country.isin(x[x > 1].index)).sum()
add("Country mapped to >1 Region", "Order Country, Order Region", k, len(o), f"{x[x>1].index[0]} -> {df[df['Order Country']==x[x>1].index[0]]['Order Region'].unique()[:3].tolist()}", "Region labels not derived from country", "Use country and region separately; flag region as unreliable", "Yes (geography features)")
add("Non-English country/state labels", "Order Country, Customer Country", len(o), len(o), "Estados Unidos, EE. UU.", "Spanish export", "Standardise labels before modelling", "Cosmetic")
add("Canceled/fraud orders carry delivery days", "Delivery Status", int(o.canceled_ship.sum()), len(o), "Shipping canceled with real>sched", "Status set but timing fields populated; Late flag = 0", "Exclude from the late-delivery target", "Yes")
ctab = pd.crosstab(df["Order Status"], df["Delivery Status"])
add("Order Status contradicts completed delivery", "Order Status vs Delivery Status", int(df[df["Order Status"].isin(["PENDING_PAYMENT", "PENDING", "PROCESSING", "ON_HOLD", "PAYMENT_REVIEW"]) & ~df.canceled_ship].shape[0]), N, "PENDING_PAYMENT + Shipping on time", "Status is a snapshot, not synced with delivery", "Do not use Order Status as an input", "Yes (leakage risk)")
gap = ((df.ship_dt - df.order_dt).dt.total_seconds() / 86400)
add("Real days differ from date gap", "Days for shipping (real) vs dates", (np.floor(gap) != df.real).sum(), N, "see below", "Rounding/definition", "Use stated real days; confirm definition", "Minor")
add("Ship date before order date", "dates", (df.ship_dt < df.order_dt).sum(), N, "none", "-", "-", "No")
add("Non-positive quantity", "Order Item Quantity", (df["Order Item Quantity"] <= 0).sum(), N, "none", "-", "-", "No")
add("Non-positive price/sales", "Product Price / Sales", ((df["Product Price"] <= 0) | (df["Sales"] <= 0)).sum(), N, "none", "-", "-", "No")
add("Negative profit lines", "Benefit per order", (df["Benefit per order"] < 0).sum(), N, f"min {df['Benefit per order'].min():.1f}", "Genuine losses or discounts", "Keep; not an ML input", "No")
add("Discount > sales", "Order Item Discount", (df["Order Item Discount"] > df["Sales"]).sum(), N, "none", "-", "-", "No")
add("Order Profit Per Order varies within an order", "Order Profit Per Order", int((g["Order Profit Per Order"].nunique() > 1).sum()), len(o), "differs per line", "Mislabelled: it is per line", "Do not treat as order-level", "Minor")
add("Customer has >1 name/segment", "Customer Id", int((df.groupby("Customer Id")[["Customer Fname", "Customer Lname", "Customer Segment"]].nunique() > 1).any(axis=1).sum()), df["Customer Id"].nunique(), "-", "ID reuse or edits", "Review; keep Customer Id as key", "Minor")
add("Product Name -> >1 category", "Product Name", int((df.groupby("Product Name")["Category Name"].nunique() > 1).sum()), df["Product Name"].nunique(), "-", "-", "-", "No")
add("Product with >1 price", "Product Card Id", int((df.groupby("Product Card Id")["Product Price"].nunique() > 1).sum()), df["Product Card Id"].nunique(), "-", "-", "-", "No")
cs = df.groupby("Order Id")["Order Item Quantity"].sum()
add("Multi-line orders (not a defect: needs aggregation)", "Order Id", int((o["items"] > 1).sum()), len(o), "up to 5 lines", "Order contains several products", "Aggregate to order level", "Yes")
add("Scheduled days vs mode inconsistent", "Days for shipment (scheduled), Shipping Mode", int((df.groupby("Shipping Mode")["sched"].nunique() > 1).sum()), 4, "none", "Schedule is a function of mode", "Treat as redundant", "Yes (redundancy)")
Q = pd.DataFrame(q); Q.to_csv(f"{folder('data_quality')}/data_quality_issues.csv", index=False)
r = Report(folder("data_quality"), "Data quality investigation")
r.sec("Findings", "Counts use the stated base (rows or orders). Zero-count rows are checks that passed.\n")
r.table(Q, floatfmt=".2f", maxrows=40)
r.sec("Cleaning decisions", f"""- **Nothing was deleted from the raw file.** Analysis tables are derived copies.
- Orders: {len(o):,} -> **{len(ov):,}** after excluding {int(o.canceled_ship.sum()):,} `Shipping canceled` orders ({o.canceled_ship.mean()*100:.1f}%) from lateness analyses, because the dataset defines no late flag for them.
- `Shipping canceled` rows equal `Order Status` in (CANCELED, SUSPECTED_FRAUD): {int((df.canceled_ship & df['Order Status'].isin(['CANCELED','SUSPECTED_FRAUD'])).sum()):,} of {int(df.canceled_ship.sum()):,} rows (verified).
- No imputation was performed. ZIP codes are left missing.""")
r.save()
print(Q[["Issue", "Affected", "Base", "% affected"]].to_string())
print("orders", len(o), "valid", len(ov), "late rate valid orders", ov.late.mean().round(4))
print(o.canceled_ship.sum(), (df.canceled_ship & df['Order Status'].isin(['CANCELED','SUSPECTED_FRAUD'])).sum(), (df['Order Status'].isin(['CANCELED','SUSPECTED_FRAUD'])).sum())
print("delay values (valid):", ov.delay.value_counts().sort_index().to_dict())
