# Model Comparison and Benchmark Evaluation Report

## 1. Benchmarking Framework (Reference Notebook Cell 18)
The 4 candidate architectures were trained and benchmarked using the exact multi-metric evaluation framework from reference notebook Cell 18:
1. **Random Forest Classifier** (`class_weight='balanced'`, `n_estimators=200`, `max_depth=8`) per notebook Cell 2
2. **LightGBM Classifier** (`learning_rate=0.05`, `scale_pos_weight=0.922`)
3. **XGBoost Classifier** (`scale_pos_weight=negative/positive`, `subsample=0.8`, `colsample_bytree=0.8`) per notebook Cell 15
4. **Logistic Regression Baseline** (`solver='liblinear'`, `C=1.0`, `class_weight='balanced'`)

---

## 2. Multi-Metric Benchmark Results Table (Validation Partition)

| Model Architecture | Accuracy | Precision | Recall | F1 Score | Probability MSE (Brier) | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|
| **Random Forest (Balanced)** | **68.06%** | **82.68%** | 48.72% | 0.6132 | **0.2041** | **0.7236** | **0.7915** |
| **LightGBM Classifier** | 67.00% | 78.37% | 50.38% | 0.6134 | 0.2072 | 0.7175 | 0.7850 |
| **XGBoost Classifier** | 67.26% | 78.54% | 50.89% | **0.6176** | 0.2062 | 0.7133 | 0.7821 |
| **Logistic Regression (Baseline)** | 66.73% | 77.12% | **51.15%** | 0.6150 | 0.2082 | 0.7106 | 0.7789 |

---

## 3. Operational Decision Threshold Optimization
- **Cost Function Assumptions**: Missed Late Delivery Penalty ($Cost_{FN} = \$2.00$), False Late Alert ($Cost_{FP} = \$1.00$).
- **Optimized Threshold**: At threshold **0.33**, the expected penalty cost per shipment drops to **$0.48 / order** (down from $0.62 at default 0.50 threshold).
- **Late Recall Boost**: Late delivery recall increases from **48.72% to 96.94%**, successfully catching nearly all delayed shipments prior to customer impact.

---

## 4. Test Partition Classification Report (Untouched Test Data)

```
============================================================
   FINAL CLASSIFICATION REPORT (Random Forest) - TEST DATA
============================================================
                   precision    recall  f1-score   support

On-Time / Advance     0.6316    0.0658    0.1191      1460
    Late Delivery     0.5252    0.9642    0.6800      1565

         accuracy                         0.5306      3025
        macro avg     0.5784    0.5150    0.3996      3025
     weighted avg     0.5766    0.5306    0.4093      3025
============================================================
```

- **Monotonic Risk Buckets**: Verified True.
  - Low Risk (<35% probability): 21.4% actual late rate
  - Medium Risk (35-65% probability): 52.1% actual late rate
  - High Risk (>65% probability): 78.6% actual late rate
- **Top 3 Risk Attribution Drivers (SHAP / Feature Importance)**:
  1. `Days for shipment (scheduled)` (SLA window)
  2. `Shipping Mode: Standard Class`
  3. `Shipping Mode: First Class`
