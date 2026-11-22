# RouteMind AI - Machine Learning Documentation

## Model 01: Order Creation (Late Delivery Risk)
- Algorithm: XGBoost Classifier (Calibrated)
- Input: Scheduled days, Type, Shipping Mode, Order Region, Market, Category, Price, Quantity, Sales
- Test Accuracy: 68.12% | ROC-AUC: 0.7720 | Threshold: 0.40

## Model 02: Warehouse Dispatch (Transit Delay Risk)
- Algorithm: XGBoost Dock Pipeline
- Input: Days for shipment (scheduled), Order-to-Ship Time, Shipping Mode, Region, Market, Department, Segment
- Test Accuracy: 97.52% | ROC-AUC: 0.9985 | Threshold: 0.39
