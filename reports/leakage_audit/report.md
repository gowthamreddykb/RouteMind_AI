# Target definition and data-leakage audit


## Target definition (verified)

- `Late_delivery_risk` = 1 exactly when `Days for shipping (real)` > `Days for shipment (scheduled)` in all 62,897 non-canceled orders (and all lines), and 0 otherwise.
- `Delivery Status`: Late delivery (delay > 0), Shipping on time (= 0), Advance shipping (< 0). 'Shipping canceled' has `Late_delivery_risk` = 0 even when real > scheduled, so lateness is undefined for them.
- **Recommended target:** `late = (real days > scheduled days)` at **order level**, for orders with Delivery Status other than 'Shipping canceled' (62,897 of 65,752 orders; 57.31% late). Alternative definitions considered: (a) late vs on-time only (drop early orders): not adopted, because early orders are not late and the business question is 'will it be late'; (b) delay-days regression: possible later, but delay is a discrete -2..4 range.
- Real days are whole numbers; their match to the date gap is 97.4% (floor), so the stated day count, not the date gap, is used.


## Leakage register




| Field / construct                                                    | Leakage type                            | Evidence                                                                                                                                                                  | Treatment                                                                    |
|:---------------------------------------------------------------------|:----------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------|
| Late_delivery_risk                                                   | Direct target leakage                   | Equals 1 iff real > scheduled days; 1 for every 'Late delivery' row (verified 100%)                                                                                       | Never an input; it is the target                                             |
| Delivery Status                                                      | Direct target leakage                   | Late delivery / Shipping on time / Advance shipping map 1:1 onto delay sign                                                                                               | Exclude                                                                      |
| Days for shipping (real)                                             | Direct target leakage                   | Defines the delay                                                                                                                                                         | Exclude                                                                      |
| shipping date (DateOrders)                                           | Direct / temporal leakage               | (shipping date - order date) reproduces real days in 97.4% of rows: behaves as a delivery date                                                                            | Exclude; use only to time-order history                                      |
| Order Status                                                         | Indirect / temporal leakage             | Snapshot after order creation; CANCELED+SUSPECTED_FRAUD = 'Shipping canceled' (7,754 of 7,754 rows); 33,932 valid orders are not COMPLETE/CLOSED though already delivered | Exclude                                                                      |
| Benefit per order / Order Profit Per Order / Order Item Profit Ratio | Indirect leakage (unknown timing)       | Profit is known only after fulfilment/sale                                                                                                                                | Exclude                                                                      |
| Customer/destination/category historical late rates                  | Future-derived aggregation leakage      | If computed on the full dataset, they contain the order's own and future outcomes                                                                                         | Compute past-only, inside training folds, using completion time < order time |
| Same-day order-volume features                                       | Temporal leakage                        | Whole-day totals include orders created after the prediction time                                                                                                         | Use counts of earlier orders only                                            |
| Line-level rows (180,519)                                            | Duplicate-order leakage                 | Lines of one order share identical target; random row splits put the same order in train and test                                                                         | Predict at order level and split by Order Id (and time)                      |
| Customer Id                                                          | Identity leakage                        | 20,652 customers, ~3.2 orders each: random splits leak customer identity                                                                                                  | Use time-based split; use only as key for past-only history                  |
| Days for shipment (scheduled)                                        | Definition duplicate of target (partly) | Lateness is real > scheduled; scheduled is a function of mode                                                                                                             | Allowed only if known at order creation; no outcome info                     |


## Order Status check

Chi-square of `Order Status` vs late among valid orders: chi2 = 4.1, dof = 6, p = 0.661, V = 0.008. Even when the association is small, the field is a post-creation snapshot and is rejected on timing grounds.
