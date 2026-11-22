# Feature-availability matrices


## Model 1: order-creation prediction

Prediction timestamp = order creation. Verdict logic: field must exist when the customer creates the order. `Shipping Mode` and the scheduled duration are marked Allowed on the **assumption** that the mode is chosen at checkout; DataCo cannot prove this.



| Column                        | Availability stage                       | Model 1 verdict                  | Reason                          |
|:------------------------------|:-----------------------------------------|:---------------------------------|:--------------------------------|
| Type                          | Order creation                           | Allowed                          | Candidate categorical           |
| Days for shipping (real)      | After delivery                           | Forbidden (leakage)              | Known only after delivery       |
| Days for shipment (scheduled) | Order creation (if mode chosen)          | Conditional                      | Candidate (redundant with mode) |
| Benefit per order             | Unknown                                  | Forbidden (unknown availability) | Reject (post-sale finance)      |
| Sales per customer            | Order creation                           | Allowed                          | Use via order value             |
| Delivery Status               | After delivery                           | Forbidden (leakage)              | Known only after delivery       |
| Late_delivery_risk            | After delivery                           | Forbidden (leakage)              | Known only after delivery       |
| Category Id                   | Order creation                           | Excluded                         | Same as Product Category Id     |
| Category Name                 | Order creation                           | Allowed                          | Candidate categorical           |
| Customer City                 | Order creation                           | Allowed                          | Weak candidate                  |
| Customer Country              | Order creation                           | Excluded                         | Low value (2 values)            |
| Customer Email                | n/a                                      | Excluded                         | Drop                            |
| Customer Fname                | n/a                                      | Excluded                         | Drop (PII)                      |
| Customer Id                   | Order creation                           | Allowed                          | Key for history features only   |
| Customer Lname                | n/a                                      | Excluded                         | Drop (PII)                      |
| Customer Password             | n/a                                      | Excluded                         | Drop                            |
| Customer Segment              | Order creation                           | Allowed                          | Candidate categorical           |
| Customer State                | Order creation                           | Allowed                          | Weak candidate                  |
| Customer Street               | n/a                                      | Excluded                         | Drop (PII, high cardinality)    |
| Customer Zipcode              | Order creation                           | Allowed                          | Weak candidate                  |
| Department Id                 | Order creation                           | Excluded                         | Redundant with Department Name  |
| Department Name               | Order creation                           | Allowed                          | Candidate categorical           |
| Latitude                      | Order creation                           | Allowed                          | Weak candidate                  |
| Longitude                     | Order creation                           | Allowed                          | Weak candidate                  |
| Market                        | Order creation                           | Allowed                          | Candidate categorical           |
| Order City                    | Order creation                           | Allowed                          | Candidate (high cardinality)    |
| Order Country                 | Order creation                           | Allowed                          | Candidate categorical           |
| Order Customer Id             | Order creation                           | Excluded                         | Redundant                       |
| order date (DateOrders)       | Order creation                           | Allowed                          | Source of month/weekday/hour    |
| Order Id                      | Order creation                           | Allowed                          | Prediction-unit key             |
| Order Item Cardprod Id        | Order creation                           | Excluded                         | Redundant                       |
| Order Item Discount           | Order creation (if discount known)       | Conditional                      | Candidate numeric               |
| Order Item Discount Rate      | Order creation (if discount known)       | Conditional                      | Candidate numeric               |
| Order Item Id                 | Order creation                           | Excluded                         | Identifier                      |
| Order Item Product Price      | Order creation                           | Allowed                          | Candidate numeric               |
| Order Item Profit Ratio       | Unknown                                  | Forbidden (unknown availability) | Reject (post-sale finance)      |
| Order Item Quantity           | Order creation                           | Allowed                          | Candidate (sum per order)       |
| Sales                         | Order creation                           | Allowed                          | Candidate via order value       |
| Order Item Total              | Order creation                           | Allowed                          | Candidate via order value       |
| Order Profit Per Order        | Unknown                                  | Forbidden (unknown availability) | Reject                          |
| Order Region                  | Order creation                           | Allowed                          | Candidate (quality caveat)      |
| Order State                   | Order creation                           | Allowed                          | Candidate (high cardinality)    |
| Order Status                  | After order creation                     | Forbidden (temporal leakage)     | Snapshot after order creation   |
| Order Zipcode                 | n/a                                      | Excluded                         | Reject (missing)                |
| Product Card Id               | Order creation                           | Excluded                         | Key                             |
| Product Category Id           | Order creation                           | Excluded                         | Redundant                       |
| Product Description           | n/a                                      | Excluded                         | Drop                            |
| Product Image                 | n/a                                      | Excluded                         | Drop                            |
| Product Name                  | Order creation                           | Allowed                          | Candidate (high cardinality)    |
| Product Price                 | Order creation                           | Allowed                          | Candidate numeric               |
| Product Status                | n/a                                      | Excluded                         | Drop                            |
| shipping date (DateOrders)    | After delivery                           | Forbidden (leakage)              | Known only after delivery       |
| Shipping Mode                 | Order creation (if selected at checkout) | Conditional                      | Candidate categorical           |


## Model 2: dispatch-time prediction

**DataCo contains no dispatch-time data**, so no dispatch model can be built from it. Fields known at order creation stay valid at dispatch; the fields a dispatch model needs are missing:



| Required dispatch-time field                      | In DataCo?   | Note                            |
|:--------------------------------------------------|:-------------|:--------------------------------|
| Actual dispatch timestamp                         | No           | Searched all 53 columns: absent |
| Warehouse identifier / origin                     | No           | Searched all 53 columns: absent |
| Carrier identifier                                | No           | Searched all 53 columns: absent |
| Warehouse processing duration                     | No           | Searched all 53 columns: absent |
| Current workload / capacity                       | No           | Searched all 53 columns: absent |
| Route origin coordinates                          | No           | Searched all 53 columns: absent |
| Dispatch-time shipping mode (changes after order) | No           | Searched all 53 columns: absent |


`shipping date (DateOrders)` is not a dispatch timestamp: it satisfies (shipping date - order date) ~ `Days for shipping (real)` in 97.4% of rows, so it behaves as a completion/delivery date and is **outcome information**.


| Column                        | Availability stage                       | Model 2 verdict                                |
|:------------------------------|:-----------------------------------------|:-----------------------------------------------|
| Type                          | Order creation                           | Allowed (carried over from order creation)     |
| Days for shipping (real)      | After delivery                           | Forbidden (leakage)                            |
| Days for shipment (scheduled) | Order creation (if mode chosen)          | Conditional (carried over from order creation) |
| Benefit per order             | Unknown                                  | Forbidden (unknown availability)               |
| Sales per customer            | Order creation                           | Allowed (carried over from order creation)     |
| Delivery Status               | After delivery                           | Forbidden (leakage)                            |
| Late_delivery_risk            | After delivery                           | Forbidden (leakage)                            |
| Category Id                   | Order creation                           | Excluded                                       |
| Category Name                 | Order creation                           | Allowed (carried over from order creation)     |
| Customer City                 | Order creation                           | Allowed (carried over from order creation)     |
| Customer Country              | Order creation                           | Excluded                                       |
| Customer Email                | n/a                                      | Excluded                                       |
| Customer Fname                | n/a                                      | Excluded                                       |
| Customer Id                   | Order creation                           | Allowed (carried over from order creation)     |
| Customer Lname                | n/a                                      | Excluded                                       |
| Customer Password             | n/a                                      | Excluded                                       |
| Customer Segment              | Order creation                           | Allowed (carried over from order creation)     |
| Customer State                | Order creation                           | Allowed (carried over from order creation)     |
| Customer Street               | n/a                                      | Excluded                                       |
| Customer Zipcode              | Order creation                           | Allowed (carried over from order creation)     |
| Department Id                 | Order creation                           | Excluded                                       |
| Department Name               | Order creation                           | Allowed (carried over from order creation)     |
| Latitude                      | Order creation                           | Allowed (carried over from order creation)     |
| Longitude                     | Order creation                           | Allowed (carried over from order creation)     |
| Market                        | Order creation                           | Allowed (carried over from order creation)     |
| Order City                    | Order creation                           | Allowed (carried over from order creation)     |
| Order Country                 | Order creation                           | Allowed (carried over from order creation)     |
| Order Customer Id             | Order creation                           | Excluded                                       |
| order date (DateOrders)       | Order creation                           | Allowed (carried over from order creation)     |
| Order Id                      | Order creation                           | Allowed (carried over from order creation)     |
| Order Item Cardprod Id        | Order creation                           | Excluded                                       |
| Order Item Discount           | Order creation (if discount known)       | Conditional (carried over from order creation) |
| Order Item Discount Rate      | Order creation (if discount known)       | Conditional (carried over from order creation) |
| Order Item Id                 | Order creation                           | Excluded                                       |
| Order Item Product Price      | Order creation                           | Allowed (carried over from order creation)     |
| Order Item Profit Ratio       | Unknown                                  | Forbidden (unknown availability)               |
| Order Item Quantity           | Order creation                           | Allowed (carried over from order creation)     |
| Sales                         | Order creation                           | Allowed (carried over from order creation)     |
| Order Item Total              | Order creation                           | Allowed (carried over from order creation)     |
| Order Profit Per Order        | Unknown                                  | Forbidden (unknown availability)               |
| Order Region                  | Order creation                           | Allowed (carried over from order creation)     |
| Order State                   | Order creation                           | Allowed (carried over from order creation)     |
| Order Status                  | After order creation                     | Forbidden (temporal leakage)                   |
| Order Zipcode                 | n/a                                      | Excluded                                       |
| Product Card Id               | Order creation                           | Excluded                                       |
| Product Category Id           | Order creation                           | Excluded                                       |
| Product Description           | n/a                                      | Excluded                                       |
| Product Image                 | n/a                                      | Excluded                                       |
| Product Name                  | Order creation                           | Allowed (carried over from order creation)     |
| Product Price                 | Order creation                           | Allowed (carried over from order creation)     |
| Product Status                | n/a                                      | Excluded                                       |
| shipping date (DateOrders)    | After delivery                           | Forbidden (leakage)                            |
| Shipping Mode                 | Order creation (if selected at checkout) | Conditional (carried over from order creation) |
