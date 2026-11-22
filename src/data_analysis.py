"""data_analysis.py - Phase 1: dataset inspection, writes reports/*.csv and the target plot."""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from load_data import TARGET

def inspect(df, reports_dir, viz_dir):
    info = pd.DataFrame({
        "column": df.columns, "dtype": df.dtypes.astype(str).values,
        "missing_count": df.isna().sum().values,
        "missing_pct": (df.isna().mean() * 100).round(4).values,
        "unique_values": df.nunique().values,
    })
    info.to_csv(f"{reports_dir}/dataset_inspection.csv", index=False)
    info[info.missing_count > 0].to_csv(f"{reports_dir}/missing_values_report.csv", index=False)

    g = df.groupby("Order Id")
    od = pd.to_datetime(df["order date (DateOrders)"], errors="coerce")
    dup = {
        "rows": len(df), "columns": df.shape[1],
        "fully_duplicated_rows": int(df.duplicated().sum()),
        "duplicated_Order_Item_Id": int(df["Order Item Id"].duplicated().sum()),
        "unique_orders": int(df["Order Id"].nunique()),
        "orders_with_multiple_item_rows": int((g.size() > 1).sum()),
        "max_items_in_one_order": int(g.size().max()),
        "orders_with_inconsistent_target": int((g[TARGET].nunique() > 1).sum()),
        "unparseable_order_dates": int(od.isna().sum()),
        "order_date_min": str(od.min()), "order_date_max": str(od.max()),
        "target_late_rate": round(float(df[TARGET].mean()), 4),
        "invalid_target_values": int((~df[TARGET].isin([0, 1])).sum()),
    }
    pd.Series(dup, name="value").rename_axis("check").to_csv(f"{reports_dir}/duplicate_report.csv")

    counts = df[TARGET].value_counts().sort_index()
    pd.DataFrame({"target_value": counts.index, "meaning": ["Not late", "Late"], "count": counts.values,
                  "percentage": (counts.values / len(df) * 100).round(4)}).to_csv(f"{reports_dir}/target_distribution.csv", index=False)
    ax = counts.plot(kind="bar", color=["#4C9F70", "#D9534F"])
    ax.set_xticklabels(["0 = Not late", "1 = Late"], rotation=0)
    ax.set_title("Target distribution: Late_delivery_risk"); ax.set_ylabel("Rows")
    plt.tight_layout(); plt.savefig(f"{viz_dir}/target_distribution.png", dpi=120); plt.close()

    print("\n=== PHASE 1: DATASET INSPECTION ===")
    for k, v in dup.items():
        print(f"  {k}: {v}")
    print("\nColumns with missing values:\n", info[info.missing_count > 0][["column", "missing_count", "missing_pct"]].to_string(index=False))
    return dup


def write_quality_report(df, dup, reports_dir, encoding_note=""):
    """Plain-text data quality report (reports/data_quality_report.txt) with exact missing counts."""
    num = df.select_dtypes("number")
    cat_cols = [c for c in df.columns if c not in num.columns]
    lines = ["DATA QUALITY REPORT", "=" * 60, f"Rows: {len(df):,}   Columns: {df.shape[1]}   {encoding_note}", ""]
    lines.append("Missing values (count and % with 4 decimals; a rounded 0.0000% may still be a real missing count):")
    for c in df.columns:
        n = int(df[c].isna().sum())
        if n:
            lines.append(f"  {c}: {n:,} missing = {n / len(df) * 100:.4f}%")
    lines += ["", "Key checks:"] + [f"  {k}: {v}" for k, v in dup.items()]
    lines += ["", "Numerical statistics (selected):", num[["Sales", "Order Item Product Price", "Order Item Quantity",
              "Order Item Discount Rate", "Days for shipment (scheduled)"]].describe().round(3).to_string()]
    lines += ["", "Categorical cardinality (unique values):"] + [f"  {c}: {df[c].nunique():,}" for c in cat_cols if df[c].nunique() < 5000]
    with open(f"{reports_dir}/data_quality_report.txt", "w") as f:
        f.write("\n".join(lines))
