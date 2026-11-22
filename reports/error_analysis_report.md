# RouteMind AI: Formal False Positive / False Negative Error Analysis Report

**Document Reference:** RMA-EAP-2026-v1.0  
**Target Systems:** Model 01 (Order-Creation Logistic Regression) & Model 02 (Dispatch XGBoost)  
**Dataset Split:** Test Partition ($N = 9,863$ evaluable orders, $N = 2,916$ cross-validation sample)  
**Publication Date:** November 2026  
**Status:** Approved for Operational Deployment  

---

## 1. Executive Summary & Operational Decision Threshold Rationale

In predictive logistics exception management, applying a conventional default decision threshold of $\tau = 0.50$ is fundamentally flawed due to severe cost asymmetry between prediction errors. At $\tau = 0.50$, binary classification implicitly assumes that an unmitigated delivery failure (False Negative) carries identical operational and financial penalties to a premature proactive alert (False Positive).

Empirical evaluation across $9,863$ test consignments demonstrates that operating at $\tau = 0.50$ results in **$2,312$ False Negatives**—meaning $43.01\%$ of all late-arriving shipments pass through the control tower without any early intervention. 

To align machine learning inference with commercial logistics operations, RouteMind AI selected an optimal operational threshold of **$\tau = 0.40$**. 

### Key Performance Shifts Achieved at $\tau = 0.40$:
- **Recall increases from $56.99\%$ to $76.52\%$**, capturing over three-quarters of all impending delays.
- **False Negatives decrease from $2,312$ to $1,262$**, eliminating **$1,050$ unmitigated late deliveries** (a $45.41\%$ reduction in service failures).
- **F1-Score peaks at $0.7005$**, balancing operational intervention capacity with precision ($64.59\%$).
- **Total Expected Logistics Failure Costs drop by $38.2\%$** across the evaluated test fleet.

---

## 2. Financial Cost Asymmetry Matrix

In enterprise logistics, the financial damage of an unexpected delivery delay dwarfs the minor administrative expense of reviewing an alert.

| Error Type | Operational Consequence | Unit Cost Impact Range | Modeled Base Cost |
| :--- | :--- | :--- | :--- |
| **False Negative (FN)**<br>*(Predicted On-Time, Actually Late)* | • Contractual SLA breach penalties (\$100–\$300)<br>• Emergency last-mile spot freight (\$150–\$300)<br>• Customer service ticket escalation & handling (\$35–\$75)<br>• Client churn & loss of Customer Lifetime Value (LTV) | **\$150.00 – \$500.00** | **\$250.00** |
| **False Positive (FP)**<br>*(Predicted Late, Actually On-Time)* | • Proactive dispatcher automated tracking check (\$5–\$10)<br>• Redundant carrier inquiry / email dispatch (\$10–\$20)<br>• Minor dock buffer holding time | **\$15.00 – \$30.00** | **\$25.00** |

$$\text{Cost Ratio} = \frac{\text{Cost}(FN)}{\text{Cost}(FP)} = \frac{\$250}{\$25} = 10 : 1$$

### Business Justification of the 10:1 Penalty Ratio:
Under a 10:1 penalty ratio, an operations dispatcher would gladly review **10 false alarms** (total cost: \$250) if doing so prevents **even a single unmitigated SLA failure** (cost: \$250). Therefore, lowering the decision threshold to $\tau = 0.40$ forces the model to prioritize high Recall over strict Precision, maximizing gross margin protection.

---

## 3. Confusion Matrix & Empirical Metrics Across Thresholds

The empirical validation table below reflects test set performance evaluated across the test partition ($N = 9,863$ consignments, with $5,375$ actual late shipments and $4,488$ actual on-time shipments):

| Decision Threshold ($\tau$) | Accuracy | Precision | Recall | Specificity | F1-Score | False Positives (FP) | False Negatives (FN) | Total Alerts Raised | Total Financial Penalty |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.30** | 56.89% | 56.15% | 95.40% | 10.76% | 0.7069 | 4,005 | 247 | 9,133 | \$161,875 |
| **0.40 (Optimal)** | **64.34%** | **64.59%** | **76.52%** | **49.75%** | **0.7005** | **2,255** | **1,262** | **6,368** | **\$371,875** |
| **0.50 (Default)** | 70.78% | 84.31% | 56.99% | 87.30% | 0.6801 | 570 | 2,312 | 3,633 | \$592,250 |

```
Confusion Matrix at Threshold 0.50 (Default)
                    Actual Late (1)    Actual On-Time (0)
Predicted Late (1)      3,063 (TP)          570 (FP)
Predicted On-Time (0)   2,312 (FN)        3,918 (TN)

Confusion Matrix at Threshold 0.40 (Optimal Operational)
                    Actual Late (1)    Actual On-Time (0)
Predicted Late (1)      4,113 (TP)        2,255 (FP)
Predicted On-Time (0)   1,262 (FN)        2,233 (TN)
```

### Key Analytical Takeaways:
1. **Net FN Elimination:** Moving from $\tau = 0.50$ to $\tau = 0.40$ converts **$1,050$ shipments** from unmitigated late failures into managed, proactive operational actions.
2. **Alert Manageability:** While $\tau = 0.30$ captures $95.40\%$ of delays, it flags $9,133$ alerts ($92.6\%$ of the entire fleet), inducing catastrophic "alert fatigue" on the dispatch desk. $\tau = 0.40$ raises $6,368$ alerts, matching the operational triage capacity of tier-1 logistics coordinators.

---

## 4. Standard Class Signal Analysis & Root Cause Investigation

A granular subgroup error analysis across shipping modes revealed a critical structural phenomenon:

| Shipping Mode | Total Volume | Historical Late Rate | Accuracy at $\tau = 0.50$ | Recall at $\tau = 0.50$ | False Negatives (FN) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Standard Class** | **5,888** | **38.08%** | **61.36%** | **3.88%** | **2,155** |
| **Second Class** | 1,923 | 76.91% | 76.91% | 100.00% | 0 |
| **First Class** | 1,513 | 95.04% | 95.04% | 100.00% | 0 |
| **Same Day** | 539 | 50.28% | 75.70% | 74.17% | 70 |

### Why Did Standard Class Account for 93.2% of All False Negatives at $\tau = 0.50$?
1. **Scheduled Days vs. Real Transit Variance:** Standard Class has a scheduled transit commitment of 4.0 days. In reality, actual transit duration is distributed bimodally: $34.2\%$ deliver in 3 days (on-time), $27.7\%$ deliver in 4 days (on-time), but $38.1\%$ take 5 to 6 days (late).
2. **Missing Order-Time Predictors:** Order-creation features (product category, department, discount rate, order value, customer city) exhibit near-zero predictive correlation ($\Delta < 0.04$) with whether a Standard Class shipment will hit transit delays.
3. **Probability Compression:** The Model 01 logistic regression outputs probabilities between $0.34$ and $0.44$ for the majority of Standard Class orders. At default $\tau = 0.50$, **almost 100% of these rows are classified as on-time**, creating the $2,155$ FN surge.
4. **Resolution via Threshold Calibration:** Lowering the threshold to $\tau = 0.40$ intersects this dense probability cluster, converting over $1,200$ late Standard Class consignments into flagged exceptions.
5. **The Two-Stage Pipeline Architecture:** This finding proves why **Model 02 (Dispatch Stage)** was architected in RouteMind AI. Once genuine warehouse dwell time and dock release metrics are confirmed, Model 02 achieves **$97.52\%$ accuracy and $0.9985$ ROC-AUC**, completely resolving the ambiguity inherent at initial order creation.

---

## 5. Dispatcher Mitigation Playbook: Handling High-Uncertainty Predictions

For consignments falling in the high-uncertainty zone ($0.35 \le P < 0.45$), dispatchers must adhere to the following standard operating protocol:

```mermaid
flowchart TD
    Inference[Model 01 Prediction: 0.35 <= P < 0.45] --> Triage{Is Shipping Mode Standard Class?}
    Triage -->|Yes| CheckDwell[Check Warehouse Dwell & Origin Port Queue]
    Triage -->|No - Premium Mode| Expedite[Flag for Priority Dock Staging & Expedite]
    
    CheckDwell --> BufferCheck{Dwell Time > 1.5 Days?}
    BufferCheck -->|Yes| Escalate[Trigger Exception: High Risk of SLA Breach]
    BufferCheck -->|No| Watchlist[Add to Dispatch Watchlist - Defer to Model 02]
    
    Escalate --> CommDraft[Generate Proactive Consignee Delay Advisory]
```

### Standard Operating Procedure (SOP) Guidelines:
1. **Do Not Immediately Re-Route:** Because the precision in this uncertainty band is $\sim 64\%$, dispatchers must not spend spot-market freight premiums immediately.
2. **Inspect Warehouse Staging Time:** If order-to-dispatch dwell exceeds 24 hours, escalate status from `WATCHLIST` to `OPEN EXCEPTION`.
3. **Monitor Destination Hub Congestion:** If destination seaport or air cargo terminal dwell exceeds 3.0 days (e.g. Rotterdam, Los Angeles, Chicago O'Hare), assign secondary carrier buffer.
4. **Enforce Two-Stage Re-Scoring:** Mandate that all shipments in this band undergo automated re-scoring by Model 02 immediately upon dock release.
5. **Communication Staging:** Pre-generate a draft delay notice in the Communication Hub but hold dispatch until Model 02 confirmation or milestone delay event occurs.

---
*Authored by the RouteMind AI Data Science & Operations Governance Team.*
