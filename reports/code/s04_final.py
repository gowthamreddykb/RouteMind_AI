from common import *
from sklearn.metrics import roc_auc_score
ov = pd.read_pickle("orders_valid_hist.pkl"); o, L = load_orders()
Ka, Kb, Kc = pd.read_pickle("key_a.pkl"), pd.read_pickle("key_b.pkl"), pd.read_pickle("key_c.pkl")
NV = len(ov); OV = ov.late.mean() * 100; NO = len(o); NC = int(o.canceled_ship.sum())
dd = pd.read_csv(f"{ROOT}/data_understanding/data_dictionary.csv", keep_default_na=False)
mt = {m: (n, r) for m, n, r in Ka["mode"]}
# ---- fixed descriptive rule baseline (NOT a trained model) ----
def rule(d): return np.select([d["mode"] == "First Class", d["mode"] == "Same Day", d["mode"] == "Second Class"], [1, (d.hour >= 12).astype(int), 1], 0)
ov["rule"] = rule(ov); acc = (ov.rule == ov.late).mean() * 100
acc_mode = ov.groupby("mode").apply(lambda g: (g.rule == g.late).mean() * 100).round(1); acc_year = ov.groupby("year").apply(lambda g: (g.rule == g.late).mean() * 100).round(1)
tp = ((ov.rule == 1) & (ov.late == 1)).sum(); fp = ((ov.rule == 1) & (ov.late == 0)).sum(); fn = ((ov.rule == 0) & (ov.late == 1)).sum(); tn = ((ov.rule == 0) & (ov.late == 0)).sum()
prec, rec = tp / (tp + fp) * 100, tp / (tp + fn) * 100
# order status leakage check
chi_os, p_os, dof_os, v_os = chi2_v(ov.assign(os=ov.order_status), "os")
n_pre = int((~ov.order_status.isin(["COMPLETE", "CLOSED"])).sum())
res_n = Kc["adv"]["nsig"]
tot_sig = sum(v[0] for v in Kc["multi"].values()); tot_tested = sum(v[1] for v in Kc["multi"].values())
def V(c): return chi2_v(ov, c)[3]
Vgeo = {r["Level"]: r["Cramer V (groups n>=100)"] for r in Ka["geo"]}

# =============== FEATURE DISCOVERY ===============
D = folder("feature_discovery")
F = [
 ("Shipping mode", "Shipping Mode", "Category as chosen at checkout", "Pattern 2/10/15: late rate 39.9% - 100% by mode; V=0.48", "Order creation + dispatch", "At creation only if mode is selected at checkout (assumption - not provable from DataCo)", "Low (no outcome info)", "Approved candidate"),
 ("Scheduled shipping days", "Days for shipment (scheduled)", "As provided (0/1/2/4)", "Pattern 10: deterministic function of mode; Spearman vs late -0.41", "Order creation + dispatch", "Same as shipping mode", "Low", "Approved candidate (redundant with mode: keep one for linear models)"),
 ("Ordered after noon", "order date (DateOrders)", "hour >= 12", "Pattern 9/15: Same Day late rate 0% before noon vs 100% after (n=3,407); stable across years", "Order creation + dispatch", "Order creation (timestamp)", "Low", "Approved candidate (use as interaction with Shipping Mode)"),
 ("Order hour", "order date (DateOrders)", "hour 0-23", "Pattern 9: weak overall V=0.064, entirely through Same Day", "Order creation", "Order creation", "Low", "Conditional candidate (only with mode)"),
 ("Order total quantity / items / size group", "Order Item Quantity, Order Item Id", "sum(qty); count(lines); bins 1-2/3-5/6-10/11+", "Pattern 5: V=0.004, rho~0", "Order creation", "Order creation", "Low", "Conditional candidate (no effect in DataCo: ablation only)"),
 ("Order total value / value group", "Order Item Total", "sum per order; quartiles", "Pattern 6: V=0.007, rho=-0.003", "Order creation", "Order creation (if discounts known)", "Low", "Conditional candidate (no effect: ablation only)"),
 ("Product category / department", "Category Name, Department Name", "First or encoded category", "Pattern 7: V=0.016 line level; 0 categories deviate after mode adjustment", "Order creation", "Order creation", "Low", "Conditional candidate (no effect: ablation only)"),
 ("Destination region / country / market", "Order Region, Order Country, Market", "Category (target-encode inside training folds)", "Pattern 3: V<=0.034 (n>=100 groups); 0 groups deviate from mode expectation", "Order creation", "Order creation; region labels inconsistent with country", "Medium if encoded on full data", "Conditional candidate (no effect: ablation only)"),
 ("Destination state / city", "Order State, Order City", "High-cardinality category", "Pattern 3: no significant deviation; most groups n<100", "Order creation", "Order creation", "Medium (overfit risk)", "Rejected candidate (insufficient evidence, sparse)"),
 ("Customer prior order count", "Customer Id, order date, shipping date", "# earlier orders completed before this order", "Pattern 8: 67.5% of orders have >=1 prior; no effect", "Order creation", "Past-only derivable", "Medium (must be past-only)", "Conditional candidate (no effect: ablation only)"),
 ("Customer prior late rate", "Customer Id, Late flag, dates", "late/total of completed earlier orders", "Pattern 8: AUC 0.496 (>=3 prior); dispersion ratio 0.99 = chance", "Order creation", "Past-only derivable", "High if computed on full data", "Rejected candidate (no evidence beyond mode)"),
 ("Destination / category / region historical late rate", "Order Country/Region, Category, Late flag, dates", "Past-only expanding rate (>=30 prior)", "Pattern 12: AUC 0.50-0.51; within-mode 0.49-0.50", "Order creation", "Past-only derivable", "High if full-data", "Rejected candidate (no evidence)"),
 ("Mode historical late rate", "Shipping Mode, Late flag, dates", "Past-only expanding rate", "Pattern 12: AUC 0.74 but within-mode 0.49 = near-constant per mode", "Order creation", "Past-only derivable", "Medium", "Rejected candidate (duplicates Shipping Mode)"),
 ("Route historical performance", "(no origin field)", "-", "Pattern 11: not computable", "Dispatch", "NOT AVAILABLE in DataCo", "-", "Rejected candidate (unavailable)"),
 ("Order month / weekday / quarter / season", "order date", "Calendar parts", "Pattern 9: V<=0.011; monthly SD consistent with noise", "Order creation", "Order creation", "Low", "Rejected candidate (no effect found)"),
 ("Customer segment, payment type", "Customer Segment, Type", "Category", "Advanced: V=0.004 / 0.005; no within-mode signal", "Order creation", "Order creation", "Low", "Rejected candidate (no effect found)"),
 ("Order volume (same day / region)", "order date, Order Region", "Count of earlier orders only", "Pattern 13: V=0.0002; rho=-0.007", "Order creation", "Past-only derivable", "High if whole-day totals are used", "Rejected candidate (no effect found)"),
 ("Late_delivery_risk, Delivery Status, real shipping days, shipping date, delay", "same", "-", "Define the target", "After delivery", "Not available at prediction time", "Direct leakage", "Rejected candidate (leakage)"),
 ("Order Status", "Order Status", "-", f"V={v_os:.3f} vs late; CANCELED/FRAUD define the cancel flag; snapshot after order creation", "After order creation", "Not at creation", "Indirect/temporal leakage", "Rejected candidate (leakage)"),
 ("Profit / benefit / profit ratio", "Benefit per order, Order Item Profit Ratio, Order Profit Per Order", "-", "Post-sale finance fields; no pattern examined as inputs", "Unknown", "Unknown", "Unknown", "Rejected candidate"),
]
FD = pd.DataFrame(F, columns=["Feature Name", "Source Column(s)", "Calculation", "Pattern Supporting It", "Prediction Stage", "Availability", "Leakage Risk", "Recommendation"])
FD.to_csv(f"{D}/feature_candidates.csv", index=False)
R = Report(D, "Feature-engineering discovery")
R.sec("Classification rules", "- **Approved**: strong, verified evidence and valid at the prediction stage.\n- **Conditional**: available at creation and business-plausible, but **no effect detected in DataCo**; keep only for ablation tests on a time-based hold-out and expect to drop.\n- **Rejected**: leakage, unavailable, redundant, or effect tested and negligible.\n\nNo feature is approved on correlation alone; approval requires effect size, adjustment for shipping mode, and a leakage check.")
R.table(FD, maxrows=40)
R.save()

# =============== AVAILABILITY MATRICES ===============
D = folder("feature_availability")
def m1(r):
    s = r["Availability stage"]; u = r["Possible ML use"]
    if s.startswith("Order creation"):
        if u.startswith("NOT") or "TARGET" in u: return "Forbidden", "Outcome field"
        if u.startswith(("Drop", "Reject", "Redundant", "Same as", "Identifier", "Key", "Low value")) and not u.startswith("Key for history"): return "Excluded", u
        return ("Conditional" if "if" in s else "Allowed"), u
    if s.startswith("After delivery"): return "Forbidden (leakage)", "Known only after delivery"
    if s.startswith("After order"): return "Forbidden (temporal leakage)", "Snapshot after order creation"
    if s == "Unknown": return "Forbidden (unknown availability)", u
    return "Excluded", u
M1 = dd[["Column", "Availability stage", "Possible ML use"]].copy(); M1[["Model 1 verdict", "Reason"]] = dd.apply(lambda r: pd.Series(m1(r)), axis=1)
M1.to_csv(f"{D}/matrix_model1_order_creation.csv", index=False)
def m2(r):
    v, why = m1(r)
    if v in ("Allowed", "Conditional"): return v + " (carried over from order creation)", "Order-creation fields remain known at dispatch"
    return v, why
M2 = M1[["Column", "Availability stage"]].copy(); M2[["Model 2 verdict", "Reason"]] = M1.apply(lambda r: pd.Series(m2(r)), axis=1)
miss = pd.DataFrame([{"Required dispatch-time field": f, "In DataCo?": "No", "Note": "Searched all 53 columns: absent"} for f in ["Actual dispatch timestamp", "Warehouse identifier / origin", "Carrier identifier", "Warehouse processing duration", "Current workload / capacity", "Route origin coordinates", "Dispatch-time shipping mode (changes after order)"]])
M2.to_csv(f"{D}/matrix_model2_dispatch.csv", index=False); miss.to_csv(f"{D}/missing_dispatch_fields.csv", index=False)
R = Report(D, "Feature-availability matrices")
R.sec("Model 1: order-creation prediction", "Prediction timestamp = order creation. Verdict logic: field must exist when the customer creates the order. `Shipping Mode` and the scheduled duration are marked Allowed on the **assumption** that the mode is chosen at checkout; DataCo cannot prove this.\n"); R.table(M1[["Column", "Availability stage", "Model 1 verdict", "Reason"]], maxrows=60)
R.sec("Model 2: dispatch-time prediction", "**DataCo contains no dispatch-time data**, so no dispatch model can be built from it. Fields known at order creation stay valid at dispatch; the fields a dispatch model needs are missing:\n"); R.table(miss)
R.parts.append("\n`shipping date (DateOrders)` is not a dispatch timestamp: it satisfies (shipping date - order date) ~ `Days for shipping (real)` in 97.4% of rows, so it behaves as a completion/delivery date and is **outcome information**.\n"); R.table(M2[["Column", "Availability stage", "Model 2 verdict"]], maxrows=60)
R.save()

# =============== LEAKAGE AUDIT ===============
D = folder("leakage_audit")
LK = pd.DataFrame([
 ("Late_delivery_risk", "Direct target leakage", "Equals 1 iff real > scheduled days; 1 for every 'Late delivery' row (verified 100%)", "Never an input; it is the target"),
 ("Delivery Status", "Direct target leakage", "Late delivery / Shipping on time / Advance shipping map 1:1 onto delay sign", "Exclude"),
 ("Days for shipping (real)", "Direct target leakage", "Defines the delay", "Exclude"),
 ("shipping date (DateOrders)", "Direct / temporal leakage", "(shipping date - order date) reproduces real days in 97.4% of rows: behaves as a delivery date", "Exclude; use only to time-order history"),
 ("Order Status", "Indirect / temporal leakage", f"Snapshot after order creation; CANCELED+SUSPECTED_FRAUD = 'Shipping canceled' (7,754 of 7,754 rows); {n_pre:,} valid orders are not COMPLETE/CLOSED though already delivered", "Exclude"),
 ("Benefit per order / Order Profit Per Order / Order Item Profit Ratio", "Indirect leakage (unknown timing)", "Profit is known only after fulfilment/sale", "Exclude"),
 ("Customer/destination/category historical late rates", "Future-derived aggregation leakage", "If computed on the full dataset, they contain the order's own and future outcomes", "Compute past-only, inside training folds, using completion time < order time"),
 ("Same-day order-volume features", "Temporal leakage", "Whole-day totals include orders created after the prediction time", "Use counts of earlier orders only"),
 ("Line-level rows (180,519)", "Duplicate-order leakage", "Lines of one order share identical target; random row splits put the same order in train and test", "Predict at order level and split by Order Id (and time)"),
 ("Customer Id", "Identity leakage", "20,652 customers, ~3.2 orders each: random splits leak customer identity", "Use time-based split; use only as key for past-only history"),
 ("Days for shipment (scheduled)", "Definition duplicate of target (partly)", "Lateness is real > scheduled; scheduled is a function of mode", "Allowed only if known at order creation; no outcome info"),
], columns=["Field / construct", "Leakage type", "Evidence", "Treatment"])
LK.to_csv(f"{D}/leakage_register.csv", index=False)
R = Report(D, "Target definition and data-leakage audit")
R.sec("Target definition (verified)", f"- `Late_delivery_risk` = 1 exactly when `Days for shipping (real)` > `Days for shipment (scheduled)` in all {NO-NC:,} non-canceled orders (and all lines), and 0 otherwise.\n- `Delivery Status`: Late delivery (delay > 0), Shipping on time (= 0), Advance shipping (< 0). 'Shipping canceled' has `Late_delivery_risk` = 0 even when real > scheduled, so lateness is undefined for them.\n- **Recommended target:** `late = (real days > scheduled days)` at **order level**, for orders with Delivery Status other than 'Shipping canceled' ({NV:,} of {NO:,} orders; {OV:.2f}% late). Alternative definitions considered: (a) late vs on-time only (drop early orders): not adopted, because early orders are not late and the business question is 'will it be late'; (b) delay-days regression: possible later, but delay is a discrete -2..4 range.\n- Real days are whole numbers; their match to the date gap is 97.4% (floor), so the stated day count, not the date gap, is used.")
R.sec("Leakage register", ""); R.table(LK, maxrows=20)
R.sec("Order Status check", f"Chi-square of `Order Status` vs late among valid orders: chi2 = {chi_os:,.1f}, dof = {dof_os}, p = {p_os:.3g}, V = {v_os:.3f}. Even when the association is small, the field is a post-creation snapshot and is rejected on timing grounds.")
R.save()

# =============== ACCESS LOGS ===============
D = folder("patterns", "access_logs"); R = Report(D, "Access-log analysis (tokenized_access_logs.csv)")
R.sec("Status: not performed", "`tokenized_access_logs.csv` was **not uploaded** (the upload folder holds only `DataCoSupplyChainDataset.csv`). No log statistics, graphs or conclusions are produced: **Insufficient data**.")
R.sec("What would be analysed once the file is supplied", "Product/category/department browsing frequency, URL frequency, hourly and daily activity, IP-level activity, repeated browsing and, if event order is reliable, sequences.")
R.sec("Relationship to shipment prediction", "DataCo's shipment data has **no IP address, session id, URL or shared key**. Without a shared identifier and event timestamps proving availability before order creation, access logs must stay separate and cannot be a shipment-prediction feature.")
R.save()

# =============== FINAL SUMMARY ===============
D = folder("final_summary")
mlist = "; ".join(f"{m}: {r:.1f}% (n={int(n):,})" for m, n, r in Ka["mode"])
geoS = pd.DataFrame(Ka["geo"])
rank = pd.DataFrame([
 (1, "Shipping Mode (+ scheduled days)", f"Late rate {mlist}; V=0.48; Kruskal eta^2=0.23", "Order creation / dispatch", "Order creation if chosen at checkout", "Strong", "Low", "Approved"),
 (2, "Ordered after noon x Same Day", "Same Day: 0% late before 12:00, 100% after (n=3,407); rule stable in all 4 years", "Order creation / dispatch", "Order creation", "Strong", "Low", "Approved"),
 (3, "Order hour (alone)", "V=0.064, entirely explained by Same Day cutoff", "Order creation", "Order creation", "Moderate (via mode only)", "Low", "Conditional"),
 (4, "Order total quantity / items", "V=0.004; Spearman -0.0004", "Order creation", "Order creation", "None found", "Low", "Conditional (ablation only)"),
 (5, "Order total value", "V=0.007; Spearman -0.003", "Order creation", "Order creation", "None found", "Low", "Conditional (ablation only)"),
 (6, "Product category / department", f"V=0.016; 0 categories deviate after mode adjustment", "Order creation", "Order creation", "None found", "Low", "Conditional (ablation only)"),
 (7, "Destination region / country / market", f"V={Vgeo['Region']:.3f} (region), {Vgeo['Country']:.3f} (country); 0 groups deviate", "Order creation", "Order creation", "None found", "Medium if encoded on full data", "Conditional (ablation only)"),
 (8, "Customer prior order count", "No effect; 67.5% coverage", "Order creation", "Past-only", "None found", "Medium", "Conditional (ablation only)"),
 (9, "Customer prior late rate", f"AUC {Kb['cust']['auc3']:.3f}; dispersion ratio {Kb['cust']['disp']:.2f}", "Order creation", "Past-only", "None (chance)", "High if full-data", "Rejected"),
 (10, "Destination/category/mode history rates", "Within-mode AUC 0.49-0.50", "Order creation", "Past-only", "None (chance)", "High if full-data", "Rejected"),
 (11, "Month / weekday / quarter", f"V<=0.011; monthly SD consistent with noise", "Order creation", "Order creation", "None found", "Low", "Rejected"),
 (12, "Order volume features", f"V=0.0002; rho={Kb['vol']['rho']:.3f}", "Order creation", "Past-only counts", "None found", "High if whole-day totals", "Rejected"),
 (13, "Route / carrier / warehouse features", "Fields absent", "Dispatch", "Not available", "Cannot assess", "-", "Rejected (unavailable)"),
 (14, "Late_delivery_risk, Delivery Status, real days, shipping date, Order Status", "Define or follow the outcome", "-", "After delivery / after order", "-", "Direct / temporal", "Rejected (leakage)"),
], columns=["Rank", "Feature", "Supporting Finding", "Prediction Stage", "Availability", "Evidence Strength", "Leakage Risk", "Recommendation"])
rank.to_csv(f"{D}/ranked_feature_table.csv", index=False)
top_state = geoS.set_index("Level")
R = Report(D, "RouteMind AI: executive summary of exploratory data analysis")
R.parts.append(f"*Prepared from the uploaded `DataCoSupplyChainDataset.csv` only. All figures are calculated from the data; per-pattern reports with graphs are in `reports/patterns/*`.*\n")
R.sec("Headline", f"""1. **The prediction unit is the order (65,752), not the row (180,519).** After excluding {NC:,} 'Shipping canceled' orders, **{NV:,} orders** are analysable; **{OV:.2f}% are late**.
2. **Shipping mode is the only strong driver**, and the mechanism is structural: scheduled days are fixed per mode (0/1/2/4) while actual days are 2 days for First Class, 0 or 1 for Same Day, and uniformly 2-6 for Second and Standard Class.
3. **One extra deterministic rule exists:** Same Day orders placed before 12:00 are never late; at or after 12:00 they are always late.
4. **Nothing else carries detectable signal** (quantity, value, category, geography, customer history, calendar, volume): {res_n} of 28 tested variables are significant inside Second/Standard Class after multiple-testing correction.
5. **A dispatch-time model cannot be built from this dataset**: no dispatch timestamp, carrier, warehouse or origin exists.""")
R.sec("1. Dataset overview", f"180,519 rows x 53 columns (cp1252); orders 2015-01-01 to 2018-01-31 (37 months); {o['cust'].nunique():,} customers; 65,752 orders with 1-5 lines (median 3). `DescriptionDataCo.csv` and `tokenized_access_logs.csv` were not supplied.")
R.sec("2. Data quality findings", "- 4 constant/masked columns (`Customer Email`, `Customer Password`, `Product Description` (100% empty), `Product Status`); `Order Zipcode` 86.2% missing; `Customer Zipcode` 3 missing.\n- `Order Region` is not a function of `Order Country` (8,270 orders, 12.6%, sit in countries mapped to more than one region); country labels are in Spanish.\n- 'Shipping canceled' (7,754 rows) = CANCELED + SUSPECTED_FRAUD exactly, with a late flag of 0 despite timing values.\n- `Order Status` is inconsistent with delivered orders (e.g. PENDING_PAYMENT with a delivery outcome).\n- Several exact duplicate columns (Customer Id/Order Customer Id, Category Id/Product Category Id, etc.). `Order Profit Per Order` varies within an order (it is per line).\n- No duplicate rows; no invalid prices, quantities or negative durations; 33,784 lines (18.7%) have negative profit (kept).")
R.sec("3. Correct prediction unit", "The **order**: all delivery, shipping, customer and destination fields are identical across the lines of an order (0 conflicts in 10 fields). One order = one delivery record in this data; whether one order can ship in several parcels is **not observable** (an uncertainty to confirm). Quantity and value are summed over lines (each line counted once).")
R.sec("4. Late-delivery behaviour", f"Late {Ka['late_n']:,} ({OV:.2f}%, 95% CI 56.9-57.7%); on time and early together {NV-Ka['late_n']:,}. Delay ranges -2 to +4 days; late orders are mostly 1 day late. Class balance is moderate (1.34:1). Calculated lateness matches `Delivery Status` and `Late_delivery_risk` exactly outside 'Shipping canceled'.")
R.sec("5. Most important shipping patterns", f"{mlist}. Actual days for Second and Standard Class are uniform over 2-6 days, independent of every field tested: their different late rates come from the different promises (2 vs 4 days). Chi-square V = 0.481; Kruskal-Wallis eta^2 = 0.233. The 100% late rate of First Class (promise 1 day, actual always 2) should be confirmed with the business: it looks like a definition artefact.")
R.sec("6. Most important geographical patterns", f"No usable geographic signal. Cramer's V (groups n>=100): market {Vgeo['Market']:.3f}, region {Vgeo['Region']:.3f}, country {Vgeo['Country']:.3f}, state {Vgeo['State']:.3f}, city {Vgeo['City']:.3f}. Regional late rates span 52.6-60.0% (n>=100 each); **no country, state or city deviates from its shipping-mode expectation after BH correction**. Extreme city/state rates are small-sample noise.")
R.sec("7. Most important customer patterns", f"{o['cust'].nunique():,} customers; 57.5% of customers are repeat customers. Customer prior late rate: AUC {Kb['cust']['auc3']:.3f} (>=3 prior completed orders). Overdispersion test ratio {Kb['cust']['disp']:.2f} (p={Kb['cust']['p']:.2f}): customers' late counts are consistent with chance given shipping-mode mix.")
R.sec("8. Most important product patterns", "50 categories, 118 products. Category Cramer's V = 0.016; **0 categories and 0 products deviate from the mode-expected rate** (BH p<0.05, n>=100 lines). No product or category is declared high risk.")
R.sec("9. Most important time-based patterns", f"Weekday V={Kb['time']['weekday']:.3f}, month {Kb['time']['month']:.3f}, year {Kb['time']['year']:.3f}: negligible; monthly late-rate spread equals sampling noise. **Order hour V={Kb['time']['hour']:.3f}**: late rate steps from ~54% (00-11h) to ~60% (12-23h), fully explained by the Same Day noon rule. Only 3 annual cycles exist, limiting seasonal conclusions.")
R.sec("10. Most important multivariate patterns", f"Across 8 combinations ({tot_tested} testable cells), **{tot_sig} cells** differ from the mode-expected rate after correction: both are Same Day x order-time cells. Priority-based combinations are unavailable.")
R.sec("11. Statistically supported findings", f"- Shipping mode vs late: chi2 = 14,530.8, dof 3, p < 1e-300, V = 0.481 (strong).\n- Same Day noon rule: 3,407 of 3,407 orders agree (100%).\n- Everything else: all other variables have overall V <= 0.06 and {res_n}/28 are significant within Second/Standard Class (BH-adjusted).\n- Multiple-testing: BH correction applied within every family of tests. With n = 62,897 even tiny effects can be significant; effect sizes are reported beside p-values.")
R.sec("12. Unavailable or unreliable information", "Order priority (absent: Pattern 4 and priority combinations not done); origin/warehouse/carrier/route (absent: Pattern 11 not done); dispatch timestamp; access logs and column descriptions (files not supplied); `Order Zipcode`; clean region labels; hierarchical clustering and DBSCAN (not run); map visualisations (no valid coordinates for destinations).")
R.sec("13. Recommended order-creation features", "**Approved:** Shipping Mode (or scheduled days), ordered-after-noon interaction with Shipping Mode. **Conditional (ablation only):** order hour, quantity/items, order value, category/department, destination region/country/market, customer prior order count. See the ranked table.")
R.sec("14. Recommended dispatch-time features", "None can be validated from DataCo. Everything known at order creation remains usable at dispatch; true dispatch features (dispatch timestamp, carrier, warehouse, processing duration, workload, route history) are **absent** and require RouteMind operational data.")
R.sec("15. Rejected or leakage-prone features", "`Late_delivery_risk`, `Delivery Status`, `Days for shipping (real)`, `shipping date`, `Order Status`, profit fields; full-data historical aggregates; whole-day volume counts; row-level random splits (duplicate-order leakage); constant/PII columns; month/weekday/quarter, segment, payment type (no effect).")
R.sec("16. Data limitations", "- Ten-field identical-value structure and uniform 2-6-day actual durations (independent of all other fields) are atypical of real logistics and suggest synthetic or heavily simulated data: confirm provenance before generalising.\n- Integer-day resolution; completion time approximated by `shipping date`.\n- Only 3 annual cycles; Order Region inconsistent; customer coordinates only.")
R.sec("17. Additional data required for production", "Order priority; dispatch timestamp; warehouse/origin and carrier IDs; warehouse processing time; workload/capacity; destination postal codes or coordinates; weather/holiday calendar; real parcel-level tracking.")
R.sec("18. Readiness assessment before ML training", f"""- **Model 1 (order creation): technically ready to build a baseline, but expect limited upside.** A fixed descriptive rule (First Class -> late; Same Day -> late if ordered at/after noon; Second Class -> late; Standard Class -> on time) agrees with the target in **{acc:.1f}%** of the {NV:,} valid orders (precision {prec:.1f}%, recall {rec:.1f}%; by mode: {', '.join(f'{k} {v}%' for k, v in acc_mode.items())}; by year: {', '.join(f'{k} {v}%' for k, v in acc_year.items())}). This is **not model accuracy**: it is an in-sample descriptive rule derived from this data and must be validated on unseen, time-ordered data. Any model must demonstrate that it beats this baseline; the within-mode analysis found no signal that would let it.
- **Model 2 (dispatch time): not ready.** Required fields do not exist in DataCo.
- Before training: fix the target definition, split by time and by Order Id, build history features past-only, use logistic regression on mode + noon interaction as the reference model, and test every conditional feature by ablation on a held-out period.
- Confirm with the business: whether Shipping Mode is selected at checkout, whether First Class is really always late, and whether 'Shipping canceled' orders should be modelled.""")
R.sec("Ranked feature-discovery table", ""); R.table(rank, maxrows=20)
R.save("final_report.md")
open(f"{D}/final_report.md", "a", encoding="utf-8").write("")
# index
idx = ["# RouteMind AI: EDA reports index\n", "Start with `final_summary/final_report.md`.\n"]
for dp, dn, fn_ in sorted(os.walk(ROOT)):
    if "report.md" in fn_ or "final_report.md" in fn_: idx.append(f"- `{os.path.relpath(dp, ROOT)}/` : " + ", ".join(sorted(f for f in fn_ if f.endswith((".md", ".png", ".csv")))[:40]))
open(f"{ROOT}/README.md", "w").write("\n".join(idx))
print(acc, prec, rec, acc_mode.to_dict(), acc_year.to_dict(), v_os, n_pre)
