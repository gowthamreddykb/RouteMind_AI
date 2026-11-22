"""target_validation.py - Phase 2: independent verification of the target and separation of delivery outcomes.

DataCo has NO actual-delivery or scheduled-delivery TIMESTAMPS and no timezone information. The only independent
evidence is durations: 'Days for shipping (real)' and 'Days for shipment (scheduled)'. Lateness is therefore verified as
    real duration > scheduled duration
which is the duration-based equivalent of 'actual delivery > scheduled delivery'.
"""
import pandas as pd
from load_data import TARGET

TARGET_VERSION = "target_v2 (eligible completed deliveries; cancelled/fraud kept out of the lateness model)"

def classify_outcomes(raw):
    """ON_TIME / LATE / CANCELLED / UNDELIVERED / UNKNOWN for every row."""
    real, sched = raw["Days for shipping (real)"], raw["Days for shipment (scheduled)"]
    out = pd.Series("UNKNOWN", index=raw.index)
    cancelled = raw["Delivery Status"].eq("Shipping canceled")
    valid = real.notna() & sched.notna() & (real >= 0) & (sched >= 0)
    out[valid & (real > sched)] = "LATE"
    out[valid & (real <= sched)] = "ON_TIME"
    out[cancelled] = "CANCELLED"
    out[~cancelled & real.isna() & sched.notna()] = "UNDELIVERED"      # no delivery duration recorded
    return out

def eligible_mask(outcome):
    return outcome.isin(["ON_TIME", "LATE"])

def target_report(raw, outcome, reports_dir):
    elig = eligible_mask(outcome)
    rule = (raw["Days for shipping (real)"] > raw["Days for shipment (scheduled)"]).astype(int)
    agree_all = (rule == raw[TARGET]).mean(); agree_elig = (rule[elig] == raw.loc[elig, TARGET]).mean()
    summary = outcome.value_counts().rename_axis("outcome").reset_index(name="rows")
    summary["share_pct"] = (summary.rows / len(raw) * 100).round(4)
    summary["original_label_late_rate"] = summary.outcome.map(raw.groupby(outcome)[TARGET].mean()).round(4)
    summary["used_in_lateness_model"] = summary.outcome.isin(["ON_TIME", "LATE"])
    summary.to_csv(f"{reports_dir}/target_outcome_summary.csv", index=False)
    xt = pd.crosstab(raw["Order Status"], raw["Delivery Status"])
    lines = ["TARGET DEFINITION REPORT", "=" * 70, f"Target version: {TARGET_VERSION}", "",
             "Original label Late_delivery_risk: 1 = late, 0 = not late (as supplied by DataCo).",
             f"Independent re-derivation: late iff 'Days for shipping (real)' > 'Days for shipment (scheduled)'.",
             f"  agreement on ALL rows:            {agree_all * 100:.4f}%",
             f"  agreement on ELIGIBLE rows:       {agree_elig * 100:.4f}%  (ON_TIME + LATE)",
             "  The only disagreements are 'Shipping canceled' rows (Order Status CANCELED / SUSPECTED_FRAUD): they have a real>scheduled duration",
             "  but the original label is 0 (not late). A cancelled order was never delivered, so it is neither late nor on time.", "",
             "Outcome summary:", summary.to_string(index=False), "",
             "Order Status x Delivery Status (counts):", xt.to_string(), "",
             "Findings:",
             " - CANCELLED (Delivery Status = 'Shipping canceled') == Order Status CANCELED + SUSPECTED_FRAUD: always labelled 0 -> label noise for a lateness model.",
             " - Order Status values PENDING / ON_HOLD / PROCESSING / PAYMENT_REVIEW coexist with recorded delivery durations, so Order Status cannot be used to",
             "   decide 'undelivered'. No row lacks a delivery duration, hence UNDELIVERED = 0 and UNKNOWN = 0 in this file.",
             " - Timestamps: no actual-delivery / scheduled-delivery timestamps and no timezone exist -> timestamp comparison BLOCKED; duration comparison used.",
             " - 'shipping date (DateOrders)' = order date + real duration (see leakage audit): it is a delivery-time proxy, never a feature. It is used ONLY to know WHEN an",
             "   outcome became known when building historical-rate features (an order's outcome is available only after its delivery).",
             "", "Decision: the binary lateness model is trained and evaluated on ON_TIME + LATE rows only. CANCELLED rows are kept in the data and reported",
             "separately; a cancellation-risk model would be a different prediction task and is not built here."]
    with open(f"{reports_dir}/target_definition_report.txt", "w") as f:
        f.write("\n".join(lines))
    return summary, agree_all, agree_elig
