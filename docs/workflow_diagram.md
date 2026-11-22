# RouteMind AI: End-to-End Operational Lifecycle & Workflow Specification

**Document Identifier:** RMA-WFL-2026-v1.0  
**Domain Scope:** Predictive Maritime Logistics Exception Management & Resolution  
**Standard Operating Procedure Compliance:** ISO 9001 / Logistics Control Tower Operational Protocol  

---

## 1. End-to-End Lifecycle Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Dispatcher as Operations Dispatcher
    participant Ingest as Data Ingestion Service
    participant Model01 as Model 01 (Order-Creation)
    participant Model02 as Model 02 (Dispatch-Stage)
    participant Model03 as Model 03 (CatBoost Regressor)
    participant SHAP as SHAP Explainability Engine
    participant ExcDesk as Exception Desk
    actor Manager as Operations Manager
    participant GenAI as GenAI Resolution Recommender
    participant CommHub as Communication Hub
    actor Consignee as Customer / Consignee

    Note over Dispatcher, Ingest: Stage 1: Order Creation & Baseline Inference
    Dispatcher->>Ingest: Upload Shipment / Order Placement CSV
    Ingest->>Ingest: Validate Schema & Filter Prohibited Post-Order Columns
    Ingest->>Model01: Request Baseline Prediction (P_late)
    Model01-->>Ingest: Return Probability (Threshold: 0.40) & Risk Level
    Ingest->>Model03: Request Continuous Delay Estimate
    Model03-->>Ingest: Return Predicted Delay (Delta Days)
    Ingest->>SHAP: Extract Top Positive/Negative Risk Drivers
    SHAP-->>Ingest: Return SHAP Feature Attributions
    Ingest->>Dispatcher: Display Shipment Card on Control Tower

    Note over Dispatcher, Model02: Stage 2: Warehouse Dock Release & Dispatch Re-Scoring
    Dispatcher->>Ingest: Log Dock Release & Actual Dwell Time Event
    Ingest->>Model02: Request Dispatch Re-Scoring
    Model02-->>Ingest: High-Precision Risk Score (97.52% Accuracy)
    
    alt If Risk Score >= 0.50 OR Exception Detected
        Note over Ingest, ExcDesk: Stage 3: Exception Triggering & Triage
        Ingest->>ExcDesk: Create Exception (Status: OPEN, Severity: CRITICAL/HIGH)
        Dispatcher->>ExcDesk: Inspect Exception & Root Causes
        
        alt Supervisory Escalation Required
            Note over Dispatcher, Manager: Stage 4: Human-in-the-Loop Manager Escalation
            Dispatcher->>Manager: Click "Escalate to Manager" (Priority, Reason, Remarks)
            Manager->>Manager: Review Escalation, Assign Owner, Transition to UNDER_REVIEW
        end
        
        Note over ExcDesk, GenAI: Stage 5: GenAI 5-Part Resolution Recommendation
        ExcDesk->>GenAI: Request Structured Resolution Strategy
        GenAI-->>ExcDesk: Return 5-Part JSON (Summary, Causes, Options with Cost/SLA, Assumptions, Draft)
        ExcDesk->>CommHub: Stage Draft with Prompt Version (v1.0.0)
        
        Note over Manager, CommHub: Stage 6: Communication Sign-Off & Customer Notice
        Manager->>CommHub: Review AI Draft, Edit Final Text, Click APPROVE
        CommHub->>Consignee: Transmit Proactive Delay Advisory Email
        CommHub->>CommHub: Log to communication_logs (prompt_version='v1.0.0')
        
        Manager->>ExcDesk: Mark Exception RESOLVED
        Manager->>Manager: Mark Manager Escalation RESOLVED
    end

    Note over Dispatcher, Consignee: Stage 7: Milestone Tracking & Completion
    Dispatcher->>Ingest: Record Port Discharge & Final Proof of Delivery
    Ingest->>Ingest: Verify All Exceptions Closed
    Ingest->>Dispatcher: Transition Shipment Status to COMPLETED
```

---

## 2. Consignment Milestone Progression (Stages 1 through 8)

All shipments follow an immutable, validated 8-milestone lifecycle:

```mermaid
stateDiagram-v2
    [*] --> CREATED : Order placement & schema audit
    CREATED --> BOOKING_CONFIRMED : Carrier booking reference verified
    BOOKING_CONFIRMED --> READY_FOR_DISPATCH : Cargo packed & customs staged
    READY_FOR_DISPATCH --> DISPATCHED : Dock release event & Model 02 re-scoring
    DISPATCHED --> IN_TRANSIT : Ocean vessel underway / feeder transfer
    IN_TRANSIT --> ARRIVED_AT_DESTINATION : Port berth & container discharge
    ARRIVED_AT_DESTINATION --> OUT_FOR_DELIVERY : Final drayage / customs release
    OUT_FOR_DELIVERY --> DELIVERED : Consignee physical receipt
    DELIVERED --> COMPLETED : Final audit & exception closure
    COMPLETED --> [*]
```

---

## 3. Detailed Exception Resolution Lifecycle States

| State | Role Owner | Permitted Operational Actions |
| :--- | :--- | :--- |
| **OPEN** | Dispatcher / System | Automatically created when predicted risk $\ge 50\%$ or milestone anomaly triggered. Dispatcher inspects root causes and SHAP contributors. |
| **ASSIGNED** | Operations Manager | Manager assigns the exception to a senior logistics coordinator or regional terminal specialist. |
| **IN_PROGRESS** | Assigned Specialist | Specialist executes tactical remediation (carrier expedite, off-dock drayage shuttle, customs broker documentation resubmission). |
| **RESOLVED** | Operations Manager | Corrective action confirmed; delay mitigated or customer proactively notified. |
| **CLOSED** | System / Admin | Final delivery validated with zero outstanding liabilities. Closed automatically upon consignment completion. |

---

## 4. Manager Escalation & Governance Workflow

```mermaid
flowchart LR
    DispInit[Dispatcher clicks\n'Escalate to Manager'] --> Pending[Status: PENDING\nPriority Assigned]
    Pending --> Review[Manager reviews context\nStatus: UNDER_REVIEW]
    Review --> InProg[Manager assigns owner\nStatus: IN_PROGRESS]
    InProg --> Resolve[Manager records resolution notes\nStatus: RESOLVED]
```

1. **Dispatcher Initiation:** Accessible directly from Shipment Detail or Exception Detail pages. The dispatcher selects Priority (`LOW`, `MEDIUM`, `HIGH`, `URGENT`), enters the operational reason, and optionally appends context notes.
2. **Supervisory Review:** Operations Managers review all active escalations on the centralized **Manager Escalations Desk**. Managers have exclusive authority to assign ownership, update escalation status, and record binding resolution notes.
3. **Audit Trail Synchronization:** Every status change is captured with timestamped entries in `escalation_history`.
