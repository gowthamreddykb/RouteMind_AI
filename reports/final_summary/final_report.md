# RouteMind AI: executive summary of exploratory data analysis

*Prepared from the uploaded `DataCoSupplyChainDataset.csv` only. All figures are calculated from the data; per-pattern reports with graphs are in `reports/patterns/*`.*


## Headline

1. **The prediction unit is the order (65,752), not the row (180,519).** After excluding 2,855 'Shipping canceled' orders, **62,897 orders** are analysable; **57.31% are late**.
2. **Shipping mode is the only strong driver**, and the mechanism is structural: scheduled days are fixed per mode (0/1/2/4) while actual days are 2 days for First Class, 0 or 1 for Same Day, and uniformly 2-6 for Second and Standard Class.
3. **One extra deterministic rule exists:** Same Day orders placed before 12:00 are never late; at or after 12:00 they are always late.
4. **Nothing else carries detectable signal** (quantity, value, category, geography, customer history, calendar, volume): 0 of 28 tested variables are significant inside Second/Standard Class after multiple-testing correction.
5. **A dispatch-time model cannot be built from this dataset**: no dispatch timestamp, carrier, warehouse or origin exists.


## 1. Dataset overview

180,519 rows x 53 columns (cp1252); orders 2015-01-01 to 2018-01-31 (37 months); 20,652 customers; 65,752 orders with 1-5 lines (median 3). `DescriptionDataCo.csv` and `tokenized_access_logs.csv` were not supplied.


## 2. Data quality findings

- 4 constant/masked columns (`Customer Email`, `Customer Password`, `Product Description` (100% empty), `Product Status`); `Order Zipcode` 86.2% missing; `Customer Zipcode` 3 missing.
- `Order Region` is not a function of `Order Country` (8,270 orders, 12.6%, sit in countries mapped to more than one region); country labels are in Spanish.
- 'Shipping canceled' (7,754 rows) = CANCELED + SUSPECTED_FRAUD exactly, with a late flag of 0 despite timing values.
- `Order Status` is inconsistent with delivered orders (e.g. PENDING_PAYMENT with a delivery outcome).
- Several exact duplicate columns (Customer Id/Order Customer Id, Category Id/Product Category Id, etc.). `Order Profit Per Order` varies within an order (it is per line).
- No duplicate rows; no invalid prices, quantities or negative durations; 33,784 lines (18.7%) have negative profit (kept).


## 3. Correct prediction unit

The **order**: all delivery, shipping, customer and destination fields are identical across the lines of an order (0 conflicts in 10 fields). One order = one delivery record in this data; whether one order can ship in several parcels is **not observable** (an uncertainty to confirm). Quantity and value are summed over lines (each line counted once).


## 4. Late-delivery behaviour

Late 36,048 (57.31%, 95% CI 56.9-57.7%); on time and early together 26,849. Delay ranges -2 to +4 days; late orders are mostly 1 day late. Class balance is moderate (1.34:1). Calculated lateness matches `Delivery Status` and `Late_delivery_risk` exactly outside 'Shipping canceled'.


## 5. Most important shipping patterns

First Class: 100.0% (n=9,602); Second Class: 80.0% (n=12,256); Same Day: 48.4% (n=3,407); Standard Class: 39.9% (n=37,632). Actual days for Second and Standard Class are uniform over 2-6 days, independent of every field tested: their different late rates come from the different promises (2 vs 4 days). Chi-square V = 0.481; Kruskal-Wallis eta^2 = 0.233. The 100% late rate of First Class (promise 1 day, actual always 2) should be confirmed with the business: it looks like a definition artefact.


## 6. Most important geographical patterns

No usable geographic signal. Cramer's V (groups n>=100): market 0.007, region 0.022, country 0.034, state 0.060, city 0.067. Regional late rates span 52.6-60.0% (n>=100 each); **no country, state or city deviates from its shipping-mode expectation after BH correction**. Extreme city/state rates are small-sample noise.


## 7. Most important customer patterns

20,652 customers; 57.5% of customers are repeat customers. Customer prior late rate: AUC 0.496 (>=3 prior completed orders). Overdispersion test ratio 0.99 (p=0.66): customers' late counts are consistent with chance given shipping-mode mix.


## 8. Most important product patterns

50 categories, 118 products. Category Cramer's V = 0.016; **0 categories and 0 products deviate from the mode-expected rate** (BH p<0.05, n>=100 lines). No product or category is declared high risk.


## 9. Most important time-based patterns

Weekday V=0.005, month 0.011, year 0.007: negligible; monthly late-rate spread equals sampling noise. **Order hour V=0.064**: late rate steps from ~54% (00-11h) to ~60% (12-23h), fully explained by the Same Day noon rule. Only 3 annual cycles exist, limiting seasonal conclusions.


## 10. Most important multivariate patterns

Across 8 combinations (214 testable cells), **2 cells** differ from the mode-expected rate after correction: both are Same Day x order-time cells. Priority-based combinations are unavailable.


## 11. Statistically supported findings

- Shipping mode vs late: chi2 = 14,530.8, dof 3, p < 1e-300, V = 0.481 (strong).
- Same Day noon rule: 3,407 of 3,407 orders agree (100%).
- Everything else: all other variables have overall V <= 0.06 and 0/28 are significant within Second/Standard Class (BH-adjusted).
- Multiple-testing: BH correction applied within every family of tests. With n = 62,897 even tiny effects can be significant; effect sizes are reported beside p-values.


## 12. Unavailable or unreliable information

Order priority (absent: Pattern 4 and priority combinations not done); origin/warehouse/carrier/route (absent: Pattern 11 not done); dispatch timestamp; access logs and column descriptions (files not supplied); `Order Zipcode`; clean region labels; hierarchical clustering and DBSCAN (not run); map visualisations (no valid coordinates for destinations).


## 13. Recommended order-creation features

**Approved:** Shipping Mode (or scheduled days), ordered-after-noon interaction with Shipping Mode. **Conditional (ablation only):** order hour, quantity/items, order value, category/department, destination region/country/market, customer prior order count. See the ranked table.


## 14. Recommended dispatch-time features

None can be validated from DataCo. Everything known at order creation remains usable at dispatch; true dispatch features (dispatch timestamp, carrier, warehouse, processing duration, workload, route history) are **absent** and require RouteMind operational data.


## 15. Rejected or leakage-prone features

`Late_delivery_risk`, `Delivery Status`, `Days for shipping (real)`, `shipping date`, `Order Status`, profit fields; full-data historical aggregates; whole-day volume counts; row-level random splits (duplicate-order leakage); constant/PII columns; month/weekday/quarter, segment, payment type (no effect).


## 16. Data limitations

- Ten-field identical-value structure and uniform 2-6-day actual durations (independent of all other fields) are atypical of real logistics and suggest synthetic or heavily simulated data: confirm provenance before generalising.
- Integer-day resolution; completion time approximated by `shipping date`.
- Only 3 annual cycles; Order Region inconsistent; customer coordinates only.


## 17. Additional data required for production

Order priority; dispatch timestamp; warehouse/origin and carrier IDs; warehouse processing time; workload/capacity; destination postal codes or coordinates; weather/holiday calendar; real parcel-level tracking.


## 18. Readiness assessment before ML training

- **Model 1 (order creation): technically ready to build a baseline, but expect limited upside.** A fixed descriptive rule (First Class -> late; Same Day -> late if ordered at/after noon; Second Class -> late; Standard Class -> on time) agrees with the target in **72.3%** of the 62,897 valid orders (precision 89.6%, recall 58.4%; by mode: First Class 100.0%, Same Day 100.0%, Second Class 80.0%, Standard Class 60.2%; by year: 2015 72.3%, 2016 72.1%, 2017 72.4%, 2018 72.4%). This is **not model accuracy**: it is an in-sample descriptive rule derived from this data and must be validated on unseen, time-ordered data. Any model must demonstrate that it beats this baseline; the within-mode analysis found no signal that would let it.
- **Model 2 (dispatch time): not ready.** Required fields do not exist in DataCo.
- Before training: fix the target definition, split by time and by Order Id, build history features past-only, use logistic regression on mode + noon interaction as the reference model, and test every conditional feature by ablation on a held-out period.
- Confirm with the business: whether Shipping Mode is selected at checkout, whether First Class is really always late, and whether 'Shipping canceled' orders should be modelled.


## Ranked feature-discovery table




|   Rank | Feature                                                                     | Supporting Finding                                                                                                                                               | Prediction Stage          | Availability                         | Evidence Strength        | Leakage Risk                   | Recommendation              |
|-------:|:----------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------|:-------------------------------------|:-------------------------|:-------------------------------|:----------------------------|
|      1 | Shipping Mode (+ scheduled days)                                            | Late rate First Class: 100.0% (n=9,602); Second Class: 80.0% (n=12,256); Same Day: 48.4% (n=3,407); Standard Class: 39.9% (n=37,632); V=0.48; Kruskal eta^2=0.23 | Order creation / dispatch | Order creation if chosen at checkout | Strong                   | Low                            | Approved                    |
|      2 | Ordered after noon x Same Day                                               | Same Day: 0% late before 12:00, 100% after (n=3,407); rule stable in all 4 years                                                                                 | Order creation / dispatch | Order creation                       | Strong                   | Low                            | Approved                    |
|      3 | Order hour (alone)                                                          | V=0.064, entirely explained by Same Day cutoff                                                                                                                   | Order creation            | Order creation                       | Moderate (via mode only) | Low                            | Conditional                 |
|      4 | Order total quantity / items                                                | V=0.004; Spearman -0.0004                                                                                                                                        | Order creation            | Order creation                       | None found               | Low                            | Conditional (ablation only) |
|      5 | Order total value                                                           | V=0.007; Spearman -0.003                                                                                                                                         | Order creation            | Order creation                       | None found               | Low                            | Conditional (ablation only) |
|      6 | Product category / department                                               | V=0.016; 0 categories deviate after mode adjustment                                                                                                              | Order creation            | Order creation                       | None found               | Low                            | Conditional (ablation only) |
|      7 | Destination region / country / market                                       | V=0.022 (region), 0.034 (country); 0 groups deviate                                                                                                              | Order creation            | Order creation                       | None found               | Medium if encoded on full data | Conditional (ablation only) |
|      8 | Customer prior order count                                                  | No effect; 67.5% coverage                                                                                                                                        | Order creation            | Past-only                            | None found               | Medium                         | Conditional (ablation only) |
|      9 | Customer prior late rate                                                    | AUC 0.496; dispersion ratio 0.99                                                                                                                                 | Order creation            | Past-only                            | None (chance)            | High if full-data              | Rejected                    |
|     10 | Destination/category/mode history rates                                     | Within-mode AUC 0.49-0.50                                                                                                                                        | Order creation            | Past-only                            | None (chance)            | High if full-data              | Rejected                    |
|     11 | Month / weekday / quarter                                                   | V<=0.011; monthly SD consistent with noise                                                                                                                       | Order creation            | Order creation                       | None found               | Low                            | Rejected                    |
|     12 | Order volume features                                                       | V=0.0002; rho=-0.007                                                                                                                                             | Order creation            | Past-only counts                     | None found               | High if whole-day totals       | Rejected                    |
|     13 | Route / carrier / warehouse features                                        | Fields absent                                                                                                                                                    | Dispatch                  | Not available                        | Cannot assess            | -                              | Rejected (unavailable)      |
|     14 | Late_delivery_risk, Delivery Status, real days, shipping date, Order Status | Define or follow the outcome                                                                                                                                     | -                         | After delivery / after order         | -                        | Direct / temporal              | Rejected (leakage)          |
