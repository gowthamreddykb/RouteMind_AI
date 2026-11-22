# RouteMind AI – Role-Based Access Control (RBAC) & Security Audit Report

**System Name:** RouteMind AI – Predictive Maritime Shipment Operations & Exception Management  
**Audit Date:** 18 November 2026  
**Auditor:** Application Security Architect & Compliance Officer  
**Scope:** Strict three-role permission enforcement across all Flask blueprints, endpoints, and UI views.  

---

## 1. Executive Summary

RouteMind AI implements a strict, multi-tiered Role-Based Access Control (RBAC) architecture built on `@login_required`, `@roles_required`, and contextual Jinja2 role evaluations. 

The application enforces **strictly three authorized operational roles**:
1. `Dispatcher` (Operations Analyst / Maritime Dispatcher)
2. `Operations Manager` (Operations Manager / Incident Supervisor)
3. `Administrator` (System & Model Governance Administrator)

No unauthorized roles (e.g. Super Admin, Customer, Guest, Vessel Manager) exist in the system. Role values are strictly mapped and persisted in the database; no UI role-switching dropdown is permitted. Deactivated accounts and unauthenticated requests are uniformly blocked and redirected.

---

## 2. Complete Role-Permission Matrix

| Route URL | Route Endpoint Name | HTTP Methods | Dispatcher | Operations Manager | Administrator | Inactive User | Unauthenticated | Test Result |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/login` | `auth_bp.login` | `GET`, `POST` | Allow | Allow | Allow | Block / Flash Warning | Allow (Public) | **PASS** |
| `/forgot-password` | `auth_bp.forgot_password` | `GET`, `POST` | Allow | Allow | Allow | Allow | Allow (Public) | **PASS** |
| `/logout` | `auth_bp.logout` | `GET` | Allow | Allow | Allow | Redirect | Redirect `/login` | **PASS** |
| `/` | `main_bp.index` | `GET` | **ALLOW** | **ALLOW** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/shipments/` | `shipment_bp.shipments` | `GET` | **ALLOW** | **ALLOW** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/shipments/<num>` | `shipment_bp.shipment_detail` | `GET` | **ALLOW** | **ALLOW** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/shipments/new` | `shipment_bp.new_shipment` | `GET`, `POST` | **ALLOW** | **ALLOW** | **DENIED (403)** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/shipments/<id>/edit` | `shipment_bp.edit_shipment` | `GET`, `POST` | **ALLOW** | **ALLOW** | **DENIED (403)** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/shipments/api/predict` | `shipment_bp.api_predict` | `POST` | **ALLOW** | **ALLOW** | **ALLOW** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/exceptions/` | `exception_bp.exceptions` | `GET` | **ALLOW** | **ALLOW** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/exceptions/api/create` | `exception_bp.api_create` | `POST` | **ALLOW** | **ALLOW** | **DENIED (403)** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/exceptions/api/assign` | `exception_bp.api_assign` | `POST` | **DENIED (403)** | **ALLOW** | **DENIED (403)** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/exceptions/api/add-note` | `exception_bp.api_add_note` | `POST` | **ALLOW** | **ALLOW** | **DENIED (403)** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/exceptions/api/resolve` | `exception_bp.api_resolve` | `POST` | **ALLOW (Assigned)** | **ALLOW** | **DENIED (403)** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/exceptions/api/escalate` | `exception_bp.api_escalate` | `POST` | **ALLOW (Assigned)** | **ALLOW** | **DENIED (403)** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/reports/` | `report_bp.reports` | `GET` | **ALLOW** | **ALLOW** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/reports/export` | `report_bp.export_report` | `GET` | **ALLOW** | **ALLOW** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/reports/export/shipment/<num>` | `report_bp.export_shipment_report` | `GET` | **ALLOW** | **ALLOW** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/ai-assistant/` | `ai_bp.ai_assistant` | `GET` | **ALLOW** | **ALLOW** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/ai-assistant/api/chat` | `ai_bp.api_chat` | `POST` | **ALLOW** | **ALLOW** | **ALLOW** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/ai/communications/` | `comm_bp.communications` | `GET` | **ALLOW** | **ALLOW** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/ai/communications/api/submit-draft` | `comm_bp.api_submit_draft` | `POST` | **ALLOW** | **ALLOW** | **DENIED (403)** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/ai/communications/api/approve` | `comm_bp.api_approve` | `POST` | **DENIED (403)** | **ALLOW** | **DENIED (403)** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/ai/communications/api/reject` | `comm_bp.api_reject` | `POST` | **DENIED (403)** | **ALLOW** | **DENIED (403)** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/ai/communications/api/request-changes` | `comm_bp.api_request_changes` | `POST` | **DENIED (403)** | **ALLOW** | **DENIED (403)** | 401 Unauthorized | 401 Unauthorized | **PASS** |
| `/users/` | `user_bp.users` | `GET` | **DENIED (403)** | **DENIED (403)** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/users/new` | `user_bp.new_user` | `GET`, `POST` | **DENIED (403)** | **DENIED (403)** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/users/<id>/edit` | `user_bp.edit_user` | `GET`, `POST` | **DENIED (403)** | **DENIED (403)** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/users/<id>/toggle-status` | `user_bp.toggle_user_status` | `POST` | **DENIED (403)** | **DENIED (403)** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/admin/` | `admin_bp.admin_settings` | `GET` | **DENIED (403)** | **DENIED (403)** | **ALLOW** | Redirect `/login` | Redirect `/login` | **PASS** |
| `/admin/thresholds` | `admin_bp.update_thresholds` | `POST` | **DENIED (403)** | **DENIED (403)** | **ALLOW** | 401 Unauthorized | 401 Unauthorized | **PASS** |

---

## 3. Security & Boundary Guarantees

1. **Separation of Duties:**
   - Administrators cannot alter live operational cargo records, create shipments, or dispatch customer SLA notices.
   - Operations Managers cannot modify model thresholds, create user accounts, or bypass audit logging.
   - Dispatchers cannot assign tickets across staff or approve communications for external dispatch.
2. **Deactivation & Inactive Account Isolation:**
   - Deactivated accounts fail authentication on `/login` with an immediate security warning. Active session cookies for deactivated accounts are invalidated on subsequent requests by Flask-Login user loader check.
3. **Sole Administrator Protection:**
   - Built-in database guard prevents deactivating or reassigning the role of the final active system Administrator.
4. **Automated RBAC Test Suite:**
   - Validated via `test_rbac_matrix.py` across all endpoints with simulated test user sessions.
   - **Result:** **100% Pass across all matrix tests.**
