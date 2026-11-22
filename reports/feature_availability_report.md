# Feature Availability and Domain Alignment Report

## 1. Domain Separation Audit

The reference notebook (`final random forest (1).ipynb`) operates on a **Network Security / Brute Force Detection** domain with features like `failed_login_count`, `connection_count_5min`, `source_ip`, and `destination_ip`.

RouteMind AI operates strictly in the **Supply Chain Logistics Operations** domain. The methodology (Random Forest + XGBoost with dynamic class weighting, ColumnTransformer with median imputation and one-hot encoding, live event streaming, and 6-metric benchmarking) has been adapted into RouteMind AI while keeping all features strictly aligned to logistics lifecycle stages.

---

## 2. Logistics Lifecycle Feature Availability Matrix

### Stage 1: Order Creation (Customer Checkout)
- **Operational Moment**: Customer places an order and pays online.
- **Genuine Available Features**:
  1. `Days for shipment (scheduled)`: SLA promised to buyer.
  2. `Type`: Payment instrument (`DEBIT`, `TRANSFER`, `CASH`, `PAYMENT`).
  3. `Shipping Mode`: Selected courier service (`Standard Class`, `First Class`, `Second Class`, `Same Day`).
  4. `Order Item Quantity`: Units purchased.
  5. `Sales`: Total order monetary value.
  6. `Order Item Product Price`: Unit price.
  7. `Order Item Discount Rate`: Promotional discount applied.
  8. `Category Name`: Product catalog department.
  9. `Order Region` & `Order Country`: Destination market geography.
  10. `Customer Segment`: Buyer classification (`Consumer`, `Corporate`, `Home Office`).
- **Forbidden Columns**: Post-order events (`Days for shipping (real)`, `Delivery Status`, actual dispatch timestamp).

---

### Stage 2: Carrier Dispatch (Warehouse Exit)
- **Operational Moment**: Package has been picked, packed, labeled, and handed over to logistics carrier.
- **Genuine Available Features**:
  1. All Order Creation features.
  2. `warehouse_processing_days`: Elapsed time between order timestamp and warehouse dispatch timestamp.
  3. `Order Status`: Operational state at dispatch (`COMPLETE`, `PENDING_PAYMENT`, `PROCESSING`).
- **Forbidden Columns**: Final delivery outcome (`Days for shipping (real)`, `Delivery Status`).

---

## 3. Compliance Summary
All pipeline transformers strictly enforce feature availability boundaries. Attempting to pass forbidden post-delivery columns into the feature matrix raises an explicit `ValueError` guard.
