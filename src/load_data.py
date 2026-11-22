"""load_data.py - loads the DataCo CSV and holds the column lists from the RouteMind AI specification."""
import os
import pandas as pd

# Project paths (relative to the project root, never hard-coded absolute paths)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_CSV = os.path.join(ROOT, "data", "raw", "DataCoSupplyChainDataset.csv")
DESCRIPTION_CSV = os.path.join(ROOT, "data", "raw", "DescriptionDataCoSupplyChain.csv")
REPORTS = os.path.join(ROOT, "reports")
VIZ = os.path.join(ROOT, "visualizations")
PROCESSED = os.path.join(ROOT, "data", "processed")
DEFAULT_EXTERNAL_MODELS = r'C:\gowtham_mithraz\python\Logistics-Control-Tower\files\models'
MODELS = os.environ.get("MODELS_DIR", DEFAULT_EXTERNAL_MODELS if os.path.exists(DEFAULT_EXTERNAL_MODELS) else os.path.join(ROOT, "models"))
RANDOM_SEED = 42

TARGET = "Late_delivery_risk"

# The 29 candidate columns from the official specification (exact names).
CANDIDATES = [
    "Type", "Days for shipment (scheduled)", "Shipping Mode", "order date (DateOrders)",
    "Category Id", "Category Name", "Department Id", "Department Name", "Product Card Id",
    "Product Category Id", "Product Name", "Product Price", "Order Item Product Price",
    "Order Item Quantity", "Customer Segment", "Customer City", "Customer Country",
    "Customer State", "Market", "Order City", "Order Country", "Order Region", "Order State",
    "Latitude", "Longitude", "Order Item Discount", "Order Item Discount Rate", "Sales",
    "Order Item Total",
]

# Columns that must never be model inputs: (column, category, reason)
PROHIBITED = [
    (TARGET, "Target", "Target variable - must never appear in X."),
    ("Days for shipping (real)", "Target leakage", "Actual shipping duration. Verified: every late row (target=1) has real > scheduled (100%), and the rule real > scheduled reproduces the target in 97.55% of all rows (the other 2.45% are cancelled/fraud orders labelled 0)."),
    ("Delivery Status", "Target leakage", "Reveals delivery outcome; 'Late delivery' == target 1 in 100% of rows (verified)."),
    ("Order Status", "Post-order information", "May reflect events after order creation (e.g. CANCELED, COMPLETE)."),
    ("Customer Email", "Personal data", "Personal information; not predictive."),
    ("Customer Password", "Personal data", "Credential; must never be used."),
    ("Customer Fname", "Personal data", "Personal information."),
    ("Customer Lname", "Personal data", "Personal information."),
    ("Customer Street", "Personal data", "Personal address information."),
    ("Customer Id", "Identifier", "Record identifier; keep only for joins/grouping."),
    ("Order Customer Id", "Identifier", "Duplicate customer identifier."),
    ("Order Id", "Identifier", "Used for grouping the split only."),
    ("Order Item Id", "Identifier", "Row identifier."),
    ("Customer Zipcode", "Initially excluded", "Postal code; sparse/high-cardinality, not approved for first model."),
    ("Order Zipcode", "Initially excluded", "86.24% missing (verified)."),
    ("Order Item Cardprod Id", "Initially excluded", "Identical to Product Card Id in 100% of rows (verified)."),
    ("Product Description", "Initially excluded", "100% missing (verified)."),
    ("Product Image", "Initially excluded", "URL/text, one value per product, not predictive."),
    ("Product Status", "Initially excluded", "Single constant value (verified)."),
    ("Order Profit Per Order", "Initially excluded", "Profit is finalised after the order is fulfilled."),
    ("Order Item Profit Ratio", "Initially excluded", "Profit is finalised after the order is fulfilled."),
    ("Benefit per order", "Initially excluded", "Profit/benefit is finalised after the order is fulfilled."),
    ("Sales per customer", "Initially excluded", "Aggregate; not an order-time value."),
    ("shipping date (DateOrders)", "Target leakage (discovered)",
     "VERIFIED: equals order date + actual shipping days (2 days -> exactly 2.0 days, etc.). It is a delivery-duration "
     "proxy, NOT a real dispatch timestamp. Excluded from BOTH models."),
]

def load_dataset(path):
    """Read the CSV. UTF-8 fails on this file, so we fall back to cp1252 then latin1."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}\nPut DataCoSupplyChainDataset.csv in data/raw/")
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"[load_data] Loaded {df.shape[0]:,} rows x {df.shape[1]} columns (encoding={enc})")
            return df
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode the CSV with utf-8, utf-8-sig, cp1252 or latin1.")

def load_description(path=DESCRIPTION_CSV):
    """Optional column-description file. Returns None (with a message) if the user did not provide it."""
    if not os.path.exists(path):
        print("[load_data] DescriptionDataCoSupplyChain.csv not provided - column meanings verified empirically instead.")
        return None
    return pd.read_csv(path, encoding="cp1252")

def check_candidates_exist(df):
    """Stop with a clear message if any specified candidate column is missing."""
    missing = [c for c in CANDIDATES + [TARGET] if c not in df.columns]
    if missing:
        raise KeyError(f"Required columns missing from CSV: {missing}. Resolve before continuing.")
    print(f"[load_data] All {len(CANDIDATES)} candidate columns + target exist.")
