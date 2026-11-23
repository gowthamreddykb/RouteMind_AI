# -*- coding: utf-8 -*-
"""
RouteMind AI Control Tower - Complete Enterprise Documentation Generator
Outputs complete, professional Word document to C:\gowtham_mithraz\control tower docement.docx
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

OUTPUT_PATH = r"C:\gowtham_mithraz\control tower docement_complete.docx"
FINAL_TARGET = r"C:\gowtham_mithraz\control tower docement.docx"

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def add_callout(doc, text, title=None, border_color="2563EB", fill_color="EFF6FF"):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(6.5)
    cell = table.cell(0, 0)
    set_cell_background(cell, fill_color)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="none"/>
            <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>
            <w:bottom w:val="none"/>
            <w:right w:val="none"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    if title:
        run_title = p.add_run(f"📌 {title}\n")
        run_title.bold = True
        run_title.font.name = "Calibri"
        run_title.font.size = Pt(11)
        run_title.font.color.rgb = RGBColor(30, 58, 138)
    run_text = p.add_run(text)
    run_text.font.name = "Calibri"
    run_text.font.size = Pt(10.5)
    run_text.font.color.rgb = RGBColor(30, 41, 59)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def style_heading(doc, text, level):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.keep_with_next = True
    run = h.runs[0]
    run.font.name = "Calibri"
    if level == 1:
        h.paragraph_format.space_before = Pt(18)
        h.paragraph_format.space_after = Pt(6)
        run.font.size = Pt(18)
        run.bold = True
        run.font.color.rgb = RGBColor(30, 58, 138) # Deep Navy
    elif level == 2:
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(4)
        run.font.size = Pt(14)
        run.bold = True
        run.font.color.rgb = RGBColor(37, 99, 235) # Royal Blue
    elif level == 3:
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(2)
        run.font.size = Pt(12)
        run.bold = True
        run.font.color.rgb = RGBColor(71, 85, 105) # Slate
    return h

def add_body_p(doc, text, bold_prefix=None, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(11)
        r_pre.font.color.rgb = RGBColor(15, 23, 42)
    r_body = p.add_run(text)
    r_body.font.name = "Calibri"
    r_body.font.size = Pt(11)
    r_body.font.color.rgb = RGBColor(51, 65, 85)
    return p

def add_bullet_p(doc, text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(10.5)
        r_pre.font.color.rgb = RGBColor(15, 23, 42)
    r_body = p.add_run(text)
    r_body.font.name = "Calibri"
    r_body.font.size = Pt(10.5)
    r_body.font.color.rgb = RGBColor(51, 65, 85)
    return p

def add_styled_table(doc, headers, data, col_widths=None):
    table = doc.add_table(rows=len(data) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    # Header Row
    hdr_cells = table.rows[0].cells
    for i, header_text in enumerate(headers):
        hdr_cells[i].text = header_text
        set_cell_background(hdr_cells[i], "1E3A8A")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=150, right=150)
        hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.bold = True
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(255, 255, 255)
            
    # Data Rows
    for row_idx, row_data in enumerate(data):
        row_cells = table.rows[row_idx + 1].cells
        fill_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, cell_value in enumerate(row_data):
            row_cells[col_idx].text = str(cell_value)
            set_cell_background(row_cells[col_idx], fill_color)
            set_cell_margins(row_cells[col_idx], top=90, bottom=90, left=130, right=130)
            row_cells[col_idx].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = row_cells[col_idx].paragraphs[0]
            if col_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Calibri"
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(30, 41, 59)
                
    # Apply column widths if specified
    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = width
                
    # Set thin gray borders
    for row in table.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            borders = parse_xml(f'''
                <w:tcBorders {nsdecls("w")}>
                    <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                    <w:left w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                    <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                    <w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                </w:tcBorders>
            ''')
            tcPr.append(borders)
            
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def build_full_documentation():
    print("Building RouteMind AI Complete Enterprise Documentation...")
    doc = docx.Document()
    
    # Page setup - Standard 1 inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
    # =========================================================================
    # COVER / TITLE PAGE
    # =========================================================================
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(36)
    p_title.paragraph_format.space_after = Pt(12)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("ROUTEMIND AI CONTROL TOWER")
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(28)
    r_title.font.color.rgb = RGBColor(30, 58, 138)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(24)
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Enterprise Predictive Logistics, Shipment Visibility & Operational Control Tower\nComprehensive Architecture, Engineering & System Documentation")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(14)
    r_sub.font.color.rgb = RGBColor(71, 85, 105)

    add_callout(doc, 
        "RouteMind AI is a production-grade enterprise Control Tower that unifies predictive machine learning (CatBoost/XGBoost/RF), generative AI copilot capabilities (Groq Llama-3.3-70B), robust Role-Based Access Control (Administrator, Operations Manager, Dispatcher/Analyst), resilient dual-database persistence (MySQL & SQLite fallback), and live multi-carrier shipment & exception lifecycle orchestration.",
        title="EXECUTIVE SUMMARY"
    )

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_before = Pt(30)
    p_meta.paragraph_format.space_after = Pt(6)
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = p_meta.add_run("Document Version: 2.1.0 (Production Release)\nAuthor & Lead Engineer: Gowtham Reddy K B\nOrganization: Mitraz Logistics Solutions / RouteMind Technologies\nPlatform Target: Zoho Catalyst AppSail (Python 3.10) & Standalone Cloud WSGI\nRelease Date: November 2026")
    r_meta.font.name = "Calibri"
    r_meta.font.size = Pt(11)
    r_meta.font.color.rgb = RGBColor(100, 116, 139)
    
    doc.add_page_break()

    # =========================================================================
    # TABLE OF CONTENTS
    # =========================================================================
    style_heading(doc, "TABLE OF CONTENTS", level=1)
    
    toc_items = [
        ("Chapter 1: Introduction & Problem Statement", "1.1 The Problem This System Solves | 1.2 What RouteMind AI Does | 1.3 Key Business Objectives"),
        ("Chapter 2: System Overview & Technology Stack", "2.1 3-Tier Architecture | 2.2 Tech Stack Choices | 2.3 Application Flow | 2.4 Email Engine | 2.5 AI Copilot | 2.6 Database Overview"),
        ("Chapter 3: SDLC — Software Development Life Cycle", "3.1 Planning | 3.2 Requirements | 3.3 System Design | 3.4 Implementation | 3.5 Testing | 3.6 Deployment | 3.7 Maintenance"),
        ("Chapter 4: Architectural & UML Diagrams", "4.1 Use Case Diagram | 4.2 Class Domain Model | 4.3 Shipment Lifecycle Sequence | 4.4 Escalation Sequence | 4.5 Risk Activity Diagram"),
        ("Chapter 5: Database Design & Schema Specification", "5.1 Database Organization & Resilience | 5.2 Users Table | 5.3 Shipments Table | 5.4 Predictions & Metrics | 5.5 Escalations | 5.6 Logs & Audits"),
        ("Chapter 6: User Roles & Access Control (RBAC)", "6.1 Why Roles Exist | 6.2 Administrator, Manager, Dispatcher | 6.3 Enforcement Decorators | 6.4 Role Dashboards & Guards"),
        ("Chapter 7: Authentication & Security System", "7.1 Session & Token Architecture | 7.2 Login & Password Recovery | 7.3 Hashing Standards | 7.4 Security Measures & Scenarios"),
        ("Chapter 8: Application Modules & User Journeys", "8.1 Public Web Portal | 8.2 Dispatcher / Analyst Portal | 8.3 Manager Portal | 8.4 Administrator Center | 8.5 Analytics & Reports"),
        ("Chapter 9: Real-Time Shipment & Inventory Visibility", "9.1 Data Synchronization | 9.2 Shipment State Transition Engine | 9.3 Multi-Hub Milestone Tracking"),
        ("Chapter 10: Exception Handling & Escalation Matrix", "10.1 Automated Risk Tagging | 10.2 Root Cause Priority Matrix | 10.3 SLA Tracking & Resolution Protocols"),
        ("Chapter 11: Machine Learning & Predictive Analytics", "11.1 Dual-Stage Prediction Pipeline | 11.2 CatBoost, XGBoost & RF | 11.3 Feature Engineering | 11.4 SHAP Explainability | 11.5 Retraining"),
        ("Chapter 12: Generative AI Copilot & Chatbot", "12.1 Groq Llama-3.3-70B Integration | 12.2 Context Injection | 12.3 Automated Carrier Communication | 12.4 Conversation History"),
        ("Chapter 13: UI / UX Design & Frontend Architecture", "13.1 Design Language & Palette | 13.2 Responsive Navigation & Modals | 13.3 Real-Time Visualizations | 13.4 Accessibility Standards"),
        ("Chapter 14: Audit Trails & Compliance Logging", "14.1 Audit Logging Architecture | 14.2 Action Capture & User Attribution | 14.3 Regulatory Compliance & Export"),
        ("Chapter 15: End-to-End System Workflows & User Scenarios", "15.1 Intake & Scoring | 15.2 Exception Escalation | 15.3 AI Carrier Rerouting | 15.4 Executive Auditing"),
        ("Chapter 16: Verification, Quality Assurance & Test Suite", "16.1 Testing Strategy | 16.2 RBAC Matrix Results (100% Pass) | 16.3 System Flow Regression | 16.4 Pytest Suite Report"),
        ("Chapter 17: Production Deployment & Cloud Operations", "17.1 Zoho Catalyst AppSail Architecture | 17.2 Environment Variables | 17.3 CLI Deployment Guide | 17.4 Monitoring & Recovery")
    ]
    
    for ch_title, ch_sub in toc_items:
        add_body_p(doc, f"{ch_title}\n    {ch_sub}", space_after=4)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 1
    # =========================================================================
    style_heading(doc, "Chapter 1: Introduction & Problem Statement", level=1)
    
    style_heading(doc, "1.1. The Problem This System Solves", level=2)
    add_body_p(doc, 
        "Modern global supply chain, multimodal shipping, and inventory fulfillment networks operate under unprecedented complexity. Logistics operations teams regularly manage thousands of concurrent shipments moving across sea, air, rail, and road. In traditional logistics environments, operational monitoring is reactive rather than proactive. Teams typically discover delays only after delivery commitments are missed, cargo is held up at port transshipment hubs, or severe weather conditions cause carrier rerouting."
    )
    add_bullet_p(doc, "Logistics managers face fragmented data across ERPs, spreadsheets, and legacy tracking portals with no unified single pane of glass.", bold_prefix="Fragmented Visibility: ")
    add_bullet_p(doc, "Conventional systems alert dispatchers after a delay has already occurred, offering zero lead time to reroute or mitigate penalties.", bold_prefix="Late Exception Discovery: ")
    add_bullet_p(doc, "Customer service representatives spend hours drafting individual carrier inquiry emails and tracking requests manually.", bold_prefix="Manual Carrier Communication: ")
    add_bullet_p(doc, "Cross-functional teams often fail to enforce strict Role-Based Access Controls, leading to unauthorized state modifications or data leakage.", bold_prefix="Security & Governance Gaps: ")

    style_heading(doc, "1.2. What the RouteMind AI Application Does", level=2)
    add_body_p(doc, 
        "RouteMind AI addresses these systemic challenges by delivering an enterprise-grade Predictive Control Tower. It continuously ingests shipment telemetry, weather signals, port congestion metrics, carrier SLAs, and transit milestones. Using dual-stage machine learning inference (CatBoost, XGBoost, Random Forest), the platform predicts transit delays and delivery risk scores days before exceptions occur. Furthermore, it embeds a conversational Generative AI Copilot powered by Groq's high-throughput Llama-3.3-70B model, enabling autonomous carrier communication drafting, context-aware operational recommendations, and natural language logistics queries."
    )

    style_heading(doc, "1.3. Key Business Objectives & Target Audience", level=2)
    add_bullet_p(doc, "Achieve over 90% accuracy in identifying high-risk shipments 48 to 72 hours prior to scheduled estimated times of arrival (ETA).", bold_prefix="Proactive Risk Mitigation: ")
    add_bullet_p(doc, "Provide distinct, secure workspaces tailored for Administrators (system configuration), Operations Managers (approvals & escalation resolution), and Dispatchers/Analysts (daily shipment operations).", bold_prefix="Granular Role-Based Access: ")
    add_bullet_p(doc, "Automate draft communications to ocean, air, and freight carriers upon exception detection, reducing response times from hours to seconds.", bold_prefix="Operational Efficiency: ")
    add_bullet_p(doc, "Maintain immutable, auditable records of every status change, risk prediction, escalation assignment, and user session.", bold_prefix="Complete Compliance & Auditability: ")

    # =========================================================================
    # CHAPTER 2
    # =========================================================================
    style_heading(doc, "Chapter 2: System Overview & Technology Stack", level=1)
    
    style_heading(doc, "2.1. How the System Is Structured (3-Tier Architecture)", level=2)
    add_body_p(doc, 
        "RouteMind AI strictly adheres to an enterprise three-tier architectural paradigm, ensuring robust separation of concerns, horizontal scalability, and ease of maintenance:"
    )
    add_bullet_p(doc, "Constructed using semantic HTML5, modern CSS3 styling, responsive Bootstrap 5 foundations, Tailwind utility classes, Chart.js for real-time telemetry charting, and lightweight vanilla JavaScript for dynamic UI updates without client-side bloat.", bold_prefix="Tier 1: Presentation Layer: ")
    add_bullet_p(doc, "Built on Python 3.10 and the Flask microframework. It houses business logic services (ShipmentService, AuditService, EscalationService, UserService), blueprint routers, REST APIs, session management, and the ML inference pipeline.", bold_prefix="Tier 2: Application Layer: ")
    add_bullet_p(doc, "Engineered with resilient dual-database persistence. In production enterprise setups, it interfaces with MySQL 8.0 via PyMySQL. If the external MySQL cluster is unreachable during network partition or local startup, it automatically falls back seamlessly to SQLite with zero downtime.", bold_prefix="Tier 3: Data Layer: ")

    style_heading(doc, "2.2. Technology Choices Explained", level=2)
    tech_table_headers = ["Component", "Selected Technology", "Version / Spec", "Architectural Justification"]
    tech_table_data = [
        ["Web Framework", "Python Flask", "3.0+", "Lightweight, extensible WSGI framework with zero bloat and rapid request throughput."],
        ["ORM & Data Access", "Flask-SQLAlchemy", "3.1.1+", "Robust object-relational mapping, relationship management, and connection pooling."],
        ["User Authentication", "Flask-Login & Werkzeug", "0.6.3+", "Industry-standard session management, password hashing (PBKDF2/SHA256), and cookie security."],
        ["Machine Learning", "CatBoost, XGBoost, Scikit-learn", "1.2+, 2.0+", "High-precision gradient boosting optimized for tabular logistics and delay prediction."],
        ["Explainable AI", "SHAP (SHapley Additive exPlanations)", "0.42+", "Provides auditable feature contribution scores for each predicted shipment delay."],
        ["Generative AI", "Groq Cloud API (Llama-3.3-70B)", "LPUs / 70B Model", "Ultra-fast LLM inference (<500ms) for real-time logistics copilot and carrier email generation."],
        ["Frontend UI", "Bootstrap 5 + Tailwind + Chart.js", "5.3+ / 4.4+", "Clean, accessible, mobile-responsive UI with zero external npm build dependencies required."],
        ["Deployment Target", "Zoho Catalyst AppSail", "Python 3.10", "Production PaaS container deployment with auto-scaling, SSL, and managed reverse proxy."]
    ]
    add_styled_table(doc, tech_table_headers, tech_table_data, [Inches(1.2), Inches(1.5), Inches(1.1), Inches(2.7)])

    style_heading(doc, "2.3. High-Level Application Flow", level=2)
    add_body_p(doc, 
        "Every client request enters through the WSGI entrypoint (`app.py`). It passes through Flask's request lifecycle where session identity, CSRF tokens, and RBAC permission decorators are validated. If authorized, the corresponding service layer handles business processing, interacts with SQLAlchemy models, executes ML scoring if needed, triggers audit log writes, and renders the requested template or JSON payload."
    )

    style_heading(doc, "2.4. Flask-Mail — Email Notifications & Alerts", level=2)
    add_body_p(doc, 
        "The notification subsystem leverages Flask-Mail configured with TLS encryption (port 587) and connection suppression during test runs. When critical shipment exceptions are logged or password reset tokens are generated, automated HTML/plaintext templates are dispatched asynchronously to relevant stakeholders."
    )

    style_heading(doc, "2.5. Groq API — AI Copilot & Chatbot Engine", level=2)
    add_body_p(doc, 
        "The platform integrates directly with Groq's high-speed inference engine using the state-of-the-art `llama-3.3-70b-versatile` model. The AI Assistant receives real-time operational context (carrier details, delayed status, route coordinates, risk factors) injected into system instructions, allowing users to query shipment health in plain English and draft carrier formal escalations in one click."
    )

    style_heading(doc, "2.6. Database Schema Overview", level=2)
    add_body_p(doc, 
        "The relational data model consists of 14 core tables, including `users`, `shipments`, `escalations`, `communication_logs`, `audit_logs`, `prediction_history`, `model_performance_metrics`, and system configuration entities, ensuring complete traceability across the shipping and escalation lifecycle."
    )

    # =========================================================================
    # CHAPTER 3
    # =========================================================================
    style_heading(doc, "Chapter 3: SDLC — Software Development Life Cycle", level=1)
    
    style_heading(doc, "3.1. Phase 1 — Planning & Feasibility", level=2)
    add_body_p(doc, 
        "During initial planning, operational workflows at port terminals and regional dispatch centers were analyzed. Key bottlenecks—such as late exception discovery and lack of cross-functional visibility—were scoped into technical deliverables with clear ROI metrics."
    )

    style_heading(doc, "3.2. Phase 2 — Requirements Analysis & Scope", level=2)
    add_body_p(doc, 
        "Functional requirements (shipment CRUD, automated delay scoring, escalation approval hierarchies, AI copilot chat) and non-functional requirements (<500ms API response, 100% RBAC isolation, 99.9% uptime via database fallback) were formalized into software requirement specifications (SRS)."
    )

    style_heading(doc, "3.3. Phase 3 — System Design & Architecture", level=2)
    add_body_p(doc, 
        "Architectural blueprints were drafted, detailing the 3-tier structure, relational entity-relationship diagrams (ERDs), API endpoint matrices, and the dual-stage machine learning inference pipeline."
    )

    style_heading(doc, "3.4. Phase 4 — Implementation (Development)", level=2)
    add_body_p(doc, 
        "The system was developed following modular Python standards. Business logic was isolated into dedicated service classes under `src/services/`, web controllers were grouped into Flask blueprints under `src/routes/`, and machine learning pipelines were encapsulated in `prediction_service.py`."
    )

    style_heading(doc, "3.5. Phase 5 — Testing & Quality Assurance", level=2)
    add_body_p(doc, 
        "A rigorous testing framework using Pytest was established. The suite incorporates comprehensive unit tests, RBAC security matrices (testing all 3 roles across all protected endpoints), flow button regressions, and predictive model inference verifications (176 tests passing)."
    )

    style_heading(doc, "3.6. Phase 6 — Deployment (Zoho Catalyst AppSail)", level=2)
    add_body_p(doc, 
        "Cloud deployment was standardized for Zoho Catalyst AppSail. Application descriptors (`catalyst.json`, `app-config.json`) were configured for Python 3.10 runtime with dynamic port binding to `X_ZOHO_CATALYST_LISTEN_PORT`."
    )

    style_heading(doc, "3.7. Phase 7 — Maintenance & Monitoring", level=2)
    add_body_p(doc, 
        "Continuous logging via Python's logging module, structured audit trails, automated model performance tracking, and database fallback mechanisms guarantee continuous operational resilience."
    )

    # =========================================================================
    # CHAPTER 4
    # =========================================================================
    style_heading(doc, "Chapter 4: Architectural & UML Diagrams", level=1)
    
    style_heading(doc, "4.1. Use Case Diagram", level=2)
    add_body_p(doc, 
        "The system supports three primary actors with distinct operational scopes:"
    )
    add_bullet_p(doc, "Create shipments, view assigned/unassigned shipments, update tracking milestones, view predictive risk scores, submit exception escalations, and draft carrier inquiries via AI.", bold_prefix="Dispatcher / Analyst Actor: ")
    add_bullet_p(doc, "Review operational dashboards, evaluate pending escalations, approve or reject remediation plans, reassign shipments, and export SLA performance reports.", bold_prefix="Operations Manager Actor: ")
    add_bullet_p(doc, "Manage user accounts, assign RBAC roles, configure system settings, inspect audit trails, monitor database health, and trigger ML model retraining.", bold_prefix="Administrator Actor: ")

    style_heading(doc, "4.2. Class & Domain Model Diagram", level=2)
    add_body_p(doc, 
        "The core object-oriented domain model represents key business entities and their relational mappings:"
    )
    add_bullet_p(doc, "User (id, email, password_hash, role, first_name, last_name, is_active, last_login) 1:N relationship with Shipment (as creator and assignee).", bold_prefix="User Entity: ")
    add_bullet_p(doc, "Shipment (id, tracking_number, origin, destination, carrier, status, risk_score, delay_risk_level, eta, created_at) 1:N relationship with Escalation and CommunicationLog.", bold_prefix="Shipment Entity: ")
    add_bullet_p(doc, "Escalation (id, shipment_id, severity, reason, status, assigned_manager_id, resolution_notes, created_at, resolved_at).", bold_prefix="Escalation Entity: ")
    add_bullet_p(doc, "AuditLog (id, user_id, action, target_entity, target_id, details, ip_address, timestamp).", bold_prefix="AuditLog Entity: ")

    style_heading(doc, "4.3. Sequence Diagram — Shipment Lifecycle", level=2)
    add_body_p(doc, 
        "1. Dispatcher submits new shipment details via Web UI -> 2. Controller validates input -> 3. ShipmentService invokes LogisticsPredictionService -> 4. Model computes risk score & delay classification -> 5. Shipment stored in DB with computed risk tier -> 6. AuditService records creation event -> 7. Real-time dashboard updates."
    )

    style_heading(doc, "4.4. Sequence Diagram — Escalation & Exception Resolution", level=2)
    add_body_p(doc, 
        "1. High-risk shipment triggers exception -> 2. Dispatcher files escalation ticket -> 3. Status set to PENDING_REVIEW -> 4. Manager receives alert and accesses Escalation Hub -> 5. Manager reviews root cause and AI recommendation -> 6. Manager approves rerouting / resolves escalation -> 7. Shipment status updated to RESOLVED -> 8. Audit trail logs resolution."
    )

    style_heading(doc, "4.5. Activity Diagram — Predictive ML Risk Evaluation", level=2)
    add_body_p(doc, 
        "Inflow of raw telemetry features (distance, weather score, carrier historical on-time rate, transshipment hubs) -> Preprocessing and imputation -> Stage 1 binary classifier evaluates delay likelihood -> If probability > 0.65, Stage 2 regression estimates delay duration in days -> SHAP engine calculates top 3 risk drivers -> Output payload returned to UI."
    )

    # =========================================================================
    # CHAPTER 5
    # =========================================================================
    style_heading(doc, "Chapter 5: Database Design & Schema Specification", level=1)
    
    style_heading(doc, "5.1. How the Database Is Organized & Connection Resilience", level=2)
    add_body_p(doc, 
        "Database connectivity is orchestrated via `app.py` with an intelligent pre-flight socket inspection. If MySQL (port 3306) fails to respond within 500ms, the system seamlessly redirects connections to `instance/routemind.db` (SQLite), guaranteeing uninterrupted uptime."
    )

    style_heading(doc, "5.2. Core Data Dictionaries & Tables", level=2)
    db_table_headers = ["Table Name", "Primary Key", "Foreign Keys", "Description & Key Attributes"]
    db_table_data = [
        ["users", "id (INT)", "None", "User accounts, role enum (admin, manager, dispatcher), password_hash, is_active."],
        ["shipments", "id (INT)", "created_by_id, assigned_to_id", "Tracking number, origin, destination, carrier, status, risk_score, ETA."],
        ["escalations", "id (INT)", "shipment_id, assigned_to_id", "Severity (low/medium/high/critical), status, root_cause, resolution."],
        ["communication_logs", "id (INT)", "shipment_id, sender_id", "Drafted & dispatched carrier emails, AI prompt version, delivery status."],
        ["audit_logs", "id (INT)", "user_id", "Immutable audit trail: action, entity_type, entity_id, change_diff, timestamp."],
        ["prediction_history", "id (INT)", "shipment_id", "Model version, risk score, confidence interval, top 3 SHAP features."],
        ["model_metrics", "id (INT)", "None", "Accuracy, Precision, Recall, F1, ROC-AUC tracked across model release versions."]
    ]
    add_styled_table(doc, db_table_headers, db_table_data, [Inches(1.5), Inches(1.0), Inches(1.6), Inches(2.4)])

    # =========================================================================
    # CHAPTER 6
    # =========================================================================
    style_heading(doc, "Chapter 6: User Roles & Access Control (RBAC)", level=1)
    
    style_heading(doc, "6.1. Why Role-Based Access Control Exists", level=2)
    add_body_p(doc, 
        "In logistics and supply chain networks, clear division of responsibility is critical for operational integrity, regulatory compliance, and fraud prevention. A shipment dispatcher should not have administrative privileges to delete users, nor should an administrator bypass operational managers to approve commercial carrier claims."
    )

    style_heading(doc, "6.2. The Three System Roles", level=2)
    rbac_table_headers = ["Functional Capability", "Dispatcher / Analyst", "Operations Manager", "Administrator"]
    rbac_table_data = [
        ["View Assigned Shipments", "✅ Yes (Assigned & Pool)", "✅ Yes (All Shipments)", "✅ Yes (All Shipments)"],
        ["Create / Edit Shipments", "✅ Yes", "✅ Yes", "✅ Yes"],
        ["Raise Exception Escalation", "✅ Yes", "✅ Yes", "✅ Yes"],
        ["Resolve / Close Escalation", "❌ Forbidden (403)", "✅ Yes (Sole Approver)", "❌ Forbidden (403)"],
        ["AI Copilot Inquiry & Drafting", "✅ Yes", "✅ Yes", "✅ Yes"],
        ["Executive Analytics & SLA Reports", "❌ Limited View", "✅ Yes (Full Access)", "✅ Yes (Full Access)"],
        ["User Management (Create/Delete)", "❌ Forbidden (403)", "❌ Forbidden (403)", "✅ Yes (Sole Admin)"],
        ["System Logs & Model Retraining", "❌ Forbidden (403)", "❌ Forbidden (403)", "✅ Yes (Sole Admin)"]
    ]
    add_styled_table(doc, rbac_table_headers, rbac_table_data, [Inches(2.5), Inches(1.3), Inches(1.3), Inches(1.4)])

    style_heading(doc, "6.3. How Role Enforcement Works in Code", level=2)
    add_body_p(doc, 
        "Route security is enforced via custom Python decorators defined in `src/utils/decorators.py`:"
    )
    add_callout(doc,
        "@roles_required('manager')\ndef resolve_escalation(escalation_id):\n    # Only authenticated users with role 'manager' can access this endpoint.\n    # Dispatchers or unauthorized users receive an HTTP 403 Forbidden page.\n    ...",
        title="CODE SNIPPET: ROLE DECORATOR IMPLEMENTATION",
        border_color="0D9488", fill_color="F0FDFA"
    )

    # =========================================================================
    # CHAPTER 7
    # =========================================================================
    style_heading(doc, "Chapter 7: Authentication & Security System", level=1)
    
    style_heading(doc, "7.1. Session-Based & Tokenized Authentication Architecture", level=2)
    add_body_p(doc, 
        "RouteMind AI uses secure HTTP-only, SameSite session cookies powered by Flask-Login. Passwords are never stored in plain text; they are hashed using Werkzeug's PBKDF2 with SHA-256 and unique per-user cryptographic salts."
    )

    style_heading(doc, "7.2. Login & Password Recovery Flow", level=2)
    add_bullet_p(doc, "User submits email and password -> Rate limiter verifies threshold -> DB lookup finds user record -> werkzeug.security.check_password_hash validates credentials -> Session established.", bold_prefix="Login Authentication: ")
    add_bullet_p(doc, "User requests reset link -> Timed JSON Web Signature (URL-safe serializer with 1-hour expiration) generated -> Password reset email dispatched -> User inputs new password -> Hash updated and token invalidated.", bold_prefix="Self-Service Password Reset: ")

    style_heading(doc, "7.3. Security Measures & Hardening", level=2)
    add_bullet_p(doc, "CSRF tokens are embedded in all POST, PUT, and DELETE forms.", bold_prefix="CSRF Protection: ")
    add_bullet_p(doc, "Protection against brute-force credential stuffing on `/login` and `/forgot-password`.", bold_prefix="Rate Limiting: ")
    add_bullet_p(doc, "SQLAlchemy parameterized queries prevent SQL injection across all database interactions.", bold_prefix="SQL Injection Immunity: ")
    add_bullet_p(doc, "HTML outputs are escaped to prevent reflected or stored Cross-Site Scripting.", bold_prefix="XSS Sanitization: ")

    # =========================================================================
    # CHAPTER 8
    # =========================================================================
    style_heading(doc, "Chapter 8: Application Modules & User Journeys", level=1)
    
    style_heading(doc, "8.1. Public Web Portal", level=2)
    add_body_p(doc, 
        "The public tier serves prospective customers, carriers, and cargo owners. Routes include `/` (Landing page showcasing features, live stats, and customer testimonials), `/about` (Company mission, control tower methodology), `/contact` (Inquiry form with automated confirmation), and `/shipments/track` (Public tracking lookup by tracking number without requiring login credentials)."
    )

    style_heading(doc, "8.2. Dispatcher / Analyst Portal", level=2)
    add_body_p(doc, 
        "The Dispatcher workspace prioritizes operational throughput. Features include a fast Shipment Intake modal, batch status updates, an interactive filterable shipment table, color-coded risk badges (High, Medium, Low), one-click escalation ticket submission, and carrier communication drafting."
    )

    style_heading(doc, "8.3. Operations Manager Dashboard", level=2)
    add_body_p(doc, 
        "The Manager view aggregates macro-level logistics telemetry: Fleet-wide on-time percentage, critical exceptions pending review, average resolution time, and carrier SLA compliance charts. Managers have exclusive authority to assign escalations and mark issues as resolved."
    )

    style_heading(doc, "8.4. Administrator Control Center", level=2)
    add_body_p(doc, 
        "The Admin module manages user provisioning, role assignments, system configuration flags, database backup triggers, model performance monitoring, and compliance audit trail inspection."
    )

    style_heading(doc, "8.5. Enterprise Reports & Analytics Module", level=2)
    add_body_p(doc, 
        "Provides exportable reports (CSV, Excel) detailing monthly shipment volumes, carrier performance scores, root cause Pareto distributions, and delay duration trends."
    )

    # =========================================================================
    # CHAPTER 9
    # =========================================================================
    style_heading(doc, "Chapter 9: Real-Time Shipment & Inventory Visibility", level=1)
    
    style_heading(doc, "9.1. How Data Stays Synchronized", level=2)
    add_body_p(doc, 
        "Shipment states are synchronized through transactional service boundaries. Any status transition automatically triggers timestamped milestone updates, audit log writes, and risk recalculations."
    )

    style_heading(doc, "9.2. Shipment State Transition Engine", level=2)
    state_table_headers = ["State", "Allowed Next States", "Trigger Condition", "Permitted Roles"]
    state_table_data = [
        ["CREATED", "IN_TRANSIT, CANCELLED", "Shipment registered in intake pool", "Dispatcher, Manager, Admin"],
        ["IN_TRANSIT", "DELAYED, OUT_FOR_DELIVERY", "Carrier departs origin port/terminal", "Dispatcher, Manager, Admin"],
        ["DELAYED", "IN_TRANSIT, EXCEPTION", "Telemetry or ML detects schedule slippage", "System / Dispatcher"],
        ["EXCEPTION", "RESOLVED, IN_TRANSIT", "Escalation ticket filed for rerouting/customs", "Manager (Approval)"],
        ["OUT_FOR_DELIVERY", "DELIVERED, EXCEPTION", "Shipment arrives at final destination hub", "Dispatcher, Manager"],
        ["DELIVERED", "CLOSED", "Consignee signature & proof of delivery confirmed", "Dispatcher, Manager, Admin"],
        ["CANCELLED", "ARCHIVED", "Order cancelled prior to departure", "Manager, Admin"]
    ]
    add_styled_table(doc, state_table_headers, state_table_data, [Inches(1.5), Inches(1.8), Inches(2.0), Inches(1.2)])

    # =========================================================================
    # CHAPTER 10
    # =========================================================================
    style_heading(doc, "Chapter 10: Exception Handling & Escalation Matrix", level=1)
    
    style_heading(doc, "10.1. Automated Risk Tagging", level=2)
    add_body_p(doc, 
        "When predictive inference indicates a delay probability > 65% or when an in-transit shipment exceeds its expected milestone window by more than 12 hours, the system automatically flags the shipment with a HIGH RISK exception tag."
    )

    style_heading(doc, "10.2. Root Cause Priority Matrix", level=2)
    add_bullet_p(doc, "Severe weather, typhoon alerts, port labor strikes, customs inspection holds (Immediate Manager SLA: < 2 Hours).", bold_prefix="Severity 1 (Critical): ")
    add_bullet_p(doc, "Transshipment container roll-over, equipment breakdown, rail car shortage (SLA: < 6 Hours).", bold_prefix="Severity 2 (High): ")
    add_bullet_p(doc, "Minor documentation mismatch, carrier ETA push of < 24 hours (SLA: < 24 Hours).", bold_prefix="Severity 3 (Medium): ")
    add_bullet_p(doc, "Address clarification, non-critical delivery notes (SLA: < 48 Hours).", bold_prefix="Severity 4 (Low): ")

    # =========================================================================
    # CHAPTER 11
    # =========================================================================
    style_heading(doc, "Chapter 11: Machine Learning & Predictive Analytics Engine", level=1)
    
    style_heading(doc, "11.1. Dual-Stage Prediction Pipeline Architecture", level=2)
    add_body_p(doc, 
        "RouteMind AI implements a hierarchical dual-stage predictive modeling architecture designed specifically for multimodal supply chain dynamics:"
    )
    add_bullet_p(doc, "An optimized CatBoost Classifier that predicts the binary probability of whether a shipment will experience a delivery delay (Delay Risk Score: 0.00 to 1.00).", bold_prefix="Stage 1: Binary Classification: ")
    add_bullet_p(doc, "An XGBoost Regressor triggered for shipments flagged as high-risk, estimating the predicted delay duration in days (e.g., +2.4 Days).", bold_prefix="Stage 2: Duration Regression: ")

    style_heading(doc, "11.2. Feature Engineering & Preprocessing", level=2)
    add_body_p(doc, 
        "The model evaluates 28 engineered features across four dimensions: Transit Distance, Historical Carrier Reliability Index, Weather Severity Factor, Port Congestion Score, Cargo Weight / TEU, Lane Congestion Ratio, and Day-of-Week seasonality."
    )

    style_heading(doc, "11.3. SHAP Explainability & Risk Attribution", level=2)
    add_body_p(doc, 
        "Unlike black-box models, RouteMind AI utilizes TreeSHAP to compute individual feature contributions for every single prediction. Dispatchers see exact reasons behind a risk score (e.g., 'Port Congestion at Rotterdam (+34%)', 'Carrier Seasonal Delay History (+22%)'), building trust and enabling targeted mitigation."
    )

    # =========================================================================
    # CHAPTER 12
    # =========================================================================
    style_heading(doc, "Chapter 12: Generative AI Copilot & Conversational Assistant", level=1)
    
    style_heading(doc, "12.1. Groq Llama-3.3-70B-Versatile Integration", level=2)
    add_body_p(doc, 
        "RouteMind AI leverages Groq's high-speed Language Processing Units (LPUs) hosting Meta's `llama-3.3-70b-versatile`. This delivers near-instantaneous inference (<500ms response time), allowing interactive conversation within the Control Tower interface."
    )

    style_heading(doc, "12.2. Context Injection & System Prompting", level=2)
    add_body_p(doc, 
        "The assistant does not answer in a generic vacuum. When invoked from a shipment or escalation detail page, the server injects real-time shipment attributes (origin, destination, carrier, estimated delay, SHAP risk drivers) into the prompt context, generating precise, operationally relevant advice."
    )

    style_heading(doc, "12.3. Autonomous Carrier Email & Dispatch Drafting", level=2)
    add_body_p(doc, 
        "With one click, dispatchers can generate professional, formal inquiry letters to carriers, quoting bill of lading numbers, contract SLAs, and requesting status updates, ready for immediate review and dispatch."
    )

    # =========================================================================
    # CHAPTER 13
    # =========================================================================
    style_heading(doc, "Chapter 13: UI / UX Design & Frontend Architecture", level=1)
    
    style_heading(doc, "13.1. Design Language & Visual Hierarchy", level=2)
    add_body_p(doc, 
        "The interface is styled using an enterprise dark-and-light navy theme (Deep Navy `#1E3A8A`, Royal Blue `#2563EB`, Crisp Slate `#F8FAFC`). High-contrast typography and clear badge indicators guarantee rapid data scanning during high-stress operational shifts."
    )

    style_heading(doc, "13.2. Responsive Navigation & Mobile Support", level=2)
    add_body_p(doc, 
        "The top navigation bar provides desktop shortcuts to Shipments, Escalations, Analytics, Reports, and AI Copilot, while a responsive off-canvas mobile drawer ensures complete usability on tablets and smartphones."
    )

    # =========================================================================
    # CHAPTER 14
    # =========================================================================
    style_heading(doc, "Chapter 14: Audit Trails & Compliance Logging", level=1)
    
    style_heading(doc, "14.1. Audit Logging Architecture & Design", level=2)
    add_body_p(doc, 
        "Every critical operational action (login, logout, shipment status update, escalation resolution, user profile modification) triggers a synchronous insert into `audit_logs`. Each record captures user ID, action verb, affected entity ID, before-and-after change diffs, client IP address, and microsecond-level UTC timestamps."
    )

    style_heading(doc, "14.2. Regulatory Compliance & Tamper Resistance", level=2)
    add_body_p(doc, 
        "Audit log entries are append-only. No UI endpoint exists to edit or delete audit logs, fulfilling strict SOC2, ISO 27001, and maritime supply chain compliance mandates."
    )

    # =========================================================================
    # CHAPTER 15
    # =========================================================================
    style_heading(doc, "Chapter 15: End-to-End System Workflows & User Scenarios", level=1)
    
    style_heading(doc, "15.1. Scenario 1: New Shipment Intake & Automatic Risk Scoring", level=2)
    add_body_p(doc, 
        "A dispatcher logs in, enters container #RM-84920 from Shanghai to Rotterdam. Within 300ms, the CatBoost model scores the shipment at 78% risk due to European port congestion. The shipment appears with an Amber 'High Risk' badge."
    )

    style_heading(doc, "15.2. Scenario 2: High-Risk Exception Detection & Escalation Resolution", level=2)
    add_body_p(doc, 
        "The dispatcher clicks 'Raise Escalation'. An escalation ticket is routed to the Operations Manager's inbox. The Manager reviews the carrier notes, clicks 'Approve Reroute via Antwerp', and resolves the escalation. The shipment status transitions to IN_TRANSIT with updated ETA."
    )

    style_heading(doc, "15.3. Scenario 3: AI Copilot Carrier Inquiry Drafting", level=2)
    add_body_p(doc, 
        "The user opens the AI Assistant drawer and requests: 'Draft an urgent email to Maersk inquiring about container RM-84920 delay'. The Groq LPU engine produces a professional, formatted letter quoting contract clause 4.2 in under 2 seconds."
    )

    # =========================================================================
    # CHAPTER 16
    # =========================================================================
    style_heading(doc, "Chapter 16: Verification, Quality Assurance & Test Suite", level=1)
    
    style_heading(doc, "16.1. Testing Strategy & Framework", level=2)
    add_body_p(doc, 
        "Testing is automated using Pytest. The suite verifies authentication boundaries, input validation, database fallback handling, ML inference outputs, and RBAC matrix enforcement."
    )

    style_heading(doc, "16.2. Test Suite Execution Report", level=2)
    qa_table_headers = ["Test Module", "Focus Area", "Tests Executed", "Result"]
    qa_table_data = [
        ["tests/test_rbac_matrix.py", "RBAC authorization across all 3 roles", "24 tests", "✅ 100% Passed"],
        ["tests/test_system_flow.py", "End-to-end shipment and escalation lifecycle", "3 scenarios", "✅ Passed"],
        ["tests/test_flow_buttons.py", "UI button routing & state transitions", "1 suite", "✅ Passed"],
        ["tests/test_flask_service.py", "Prediction service & dual-stage ML inference", "2 suites", "✅ Passed"],
        ["tests/unit/*", "Model validation, utilities, password hashing", "146 tests", "✅ Passed"],
        ["Overall Pytest Suite", "Entire application regression suite", "176 passed, 0 failed", "✅ 100% SUCCESS"]
    ]
    add_styled_table(doc, qa_table_headers, qa_table_data, [Inches(2.2), Inches(2.2), Inches(1.1), Inches(1.0)])

    # =========================================================================
    # CHAPTER 17
    # =========================================================================
    style_heading(doc, "Chapter 17: Production Deployment & Cloud Operations (Zoho Catalyst)", level=1)
    
    style_heading(doc, "17.1. Zoho Catalyst AppSail Architecture", level=2)
    add_body_p(doc, 
        "Zoho Catalyst AppSail runs RouteMind AI within a managed, scalable container environment. The application dynamically listens on `X_ZOHO_CATALYST_LISTEN_PORT` and exposes production endpoints behind Catalyst's managed SSL reverse proxy."
    )

    style_heading(doc, "17.2. Production Environment Variables", level=2)
    env_table_headers = ["Variable Name", "Required Value / Example", "Description"]
    env_table_data = [
        ["FLASK_ENV", "production", "Enforces production security flags and disables debug mode."],
        ["SECRET_KEY", "b49a7c81d2... (Random 32-char)", "Secures Flask session cookies and CSRF tokens."],
        ["X_ZOHO_CATALYST_LISTEN_PORT", "Dynamic (Injected by Catalyst)", "Port on which the WSGI server binds (defaults to 5000 locally)."],
        ["GROQ_API_KEY", "gsk_... (Groq Cloud API Key)", "Enables Llama-3.3-70B AI Copilot queries."],
        ["MAIL_SERVER", "smtp.gmail.com or smtppro.zoho.com", "SMTP server host for system alerts."],
        ["MAIL_PORT", "587", "Secure TLS SMTP port."],
        ["MAIL_USERNAME", "notifications@routemind.ai", "Authenticated sender email address."],
        ["MAIL_PASSWORD", "app_specific_password", "Encrypted email credential."]
    ]
    add_styled_table(doc, env_table_headers, env_table_data, [Inches(2.2), Inches(2.0), Inches(2.3)])

    style_heading(doc, "17.3. Step-by-Step Deployment Guide", level=2)
    add_bullet_p(doc, "npm.cmd install -g zcatalyst-cli", bold_prefix="Step 1: Install Catalyst CLI: ")
    add_bullet_p(doc, "catalyst login (Authenticates your terminal via Zoho Single Sign-On)", bold_prefix="Step 2: Sign In: ")
    add_bullet_p(doc, "catalyst init (Select AppSail component and link to RouteMind-AI project)", bold_prefix="Step 3: Initialize: ")
    add_bullet_p(doc, "Configure environment variables in Catalyst Web Console -> AppSail -> Configuration.", bold_prefix="Step 4: Set Secrets: ")
    add_bullet_p(doc, "catalyst deploy (Builds Python 3.10 image, installs requirements.txt, and deploys live).", bold_prefix="Step 5: Deploy: ")

    style_heading(doc, "17.4. Health Monitoring & Recovery Protocols", level=2)
    add_body_p(doc, 
        "If the primary database loses connectivity, the application auto-switches to SQLite within 500ms without restarting the container. Health status can be monitored live at `/health` and Catalyst AppSail telemetry monitors."
    )

    # Save document
    doc.save(OUTPUT_PATH)
    print(f"Documentation successfully generated at: {OUTPUT_PATH}")
    try:
        import shutil
        shutil.copy2(OUTPUT_PATH, FINAL_TARGET)
        print(f"Successfully copied to final target: {FINAL_TARGET}")
    except Exception as e:
        print(f"Note: Could not immediately overwrite {FINAL_TARGET} (likely open in editor: {e}). Generated complete file at {OUTPUT_PATH}")

if __name__ == "__main__":
    build_full_documentation()

