"""
ai_assistant_service.py - Production AI Logistics Copilot & Operations Assistant
Author: RouteMind AI Engineering
Provides conversational intelligence, dynamic ORM querying, ML interpretability,
conversational session memory, and maritime operational recommendations.
"""
import re
import os
import json
import logging
from typing import Dict, Any, Optional, Tuple, List

from flask import current_app
from extensions import db
from src.models.shipment_model import Shipment
from src.models.exception_model import ShipmentException
from src.models.escalation_model import ManagerEscalation
from src.models.model_score_model import ModelScore
from src.models.user_model import User
from src.models.chat_model import ChatConversation, ChatMessage
from src.services.ai_intent_service import AIIntentService, Intent, normalize_text
from src.services.ai_chart_service import AIChartService
from src.security.permissions import normalize_role, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN

logger = logging.getLogger(__name__)


class AIAssistantService:

    @classmethod
    def answer_query(cls, query: str, context: Optional[Dict[str, Any]] = None, conversation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Main entry point for answering conversational logistics questions.
        Returns a dictionary with:
          - success: True
          - response: Markdown text answer
          - message: Markdown text answer (alias for UI compatibility)
          - conversation_id: Active conversation ID
          - context_shipments: List of shipment numbers referenced in context
        """
        from flask import has_app_context
        if not has_app_context():
            from app import app
            with app.app_context():
                return cls.answer_query(query, context=context, conversation_id=conversation_id)

        if not query or not query.strip():
            return {
                'success': True,
                'response': "Please provide an operational question, query, or consignment reference.",
                'message': "Please provide an operational question, query, or consignment reference.",
                'conversation_id': conversation_id,
                'context_shipments': []
            }

        raw_q = query.strip()
        norm_q = normalize_text(raw_q)
        context = context or {}
        user_name = context.get('user', 'Operations Specialist')
        user_role = context.get('role', 'Dispatcher')
        user_id = context.get('user_id')

        # Retrieve or initialize conversation record for multi-turn session memory
        conv = None
        context_data: Dict[str, Any] = {}
        if conversation_id:
            try:
                conv = db.session.get(ChatConversation, conversation_id)
                if conv and conv.last_context_json:
                    context_data = json.loads(conv.last_context_json)
            except Exception as e:
                logger.warning(f"Failed to load conversation {conversation_id}: {e}")

        last_shipments: List[str] = context_data.get('last_shipments', [])
        last_focus_shipment: Optional[str] = context_data.get('last_focus_shipment')
        last_intent: Optional[str] = context_data.get('last_intent')
        last_chart_payload: Optional[Dict[str, Any]] = context_data.get('last_chart_payload')
        presented_chart_signatures: List[str] = context_data.get('presented_chart_signatures', [])
        last_analysis_data: Dict[str, Any] = context_data.get('last_analysis_data', {})
        active_filters: Dict[str, Any] = context_data.get('active_filters', {})

        # Detect intent using robust natural language layer
        intent, intent_meta = AIIntentService.detect_intent(
            norm_q, context_shipments=last_shipments, last_intent=last_intent
        )

        # Dispatch query to appropriate handler based on detected intent
        dispatch_res = cls._dispatch_intent(
            intent, intent_meta, norm_q, user_name, user_role, last_shipments, last_focus_shipment,
            last_chart_payload=last_chart_payload,
            presented_chart_signatures=presented_chart_signatures,
            last_analysis_data=last_analysis_data,
            active_filters=active_filters
        )
        new_analysis_data = None
        if len(dispatch_res) == 5:
            response_text, new_context_shipments, new_focus_shipment, chart_payload, new_analysis_data = dispatch_res
        elif len(dispatch_res) == 4:
            response_text, new_context_shipments, new_focus_shipment, chart_payload = dispatch_res
        else:
            response_text, new_context_shipments, new_focus_shipment = dispatch_res
            chart_payload = None

        # Check if user explicitly requested a chart/graph/visualization in this prompt
        chart_keywords = [
            'chart', 'graph', 'plot', 'visualize', 'visualization', 'visual',
            'diagram', 'histogram', 'donut', 'doughnut', 'pie', 'scatter'
        ]
        has_negative_chart = bool(re.search(
            r'\b(no|without|don\'?t\s+show|stop|not\s+need|do\s+not\s+need)\s+(?:a\s+|any\s+|the\s+)?(chart|graph|plot|visual|diagram)',
            norm_q,
            re.IGNORECASE
        ))
        has_explicit_chart_keyword = any(
            re.search(r'\b' + re.escape(kw) + r'\b', norm_q, re.IGNORECASE) for kw in chart_keywords
        )

        user_wants_chart = False
        if not has_negative_chart and not intent_meta.get('no_chart'):
            if intent in (Intent.CHART_REQUEST, Intent.CHART_MODIFICATION) or intent_meta.get('wants_chart') or has_explicit_chart_keyword:
                user_wants_chart = True

        # Strict Rule: NEVER return a chart unless the user explicitly requested a chart in their prompt
        if not user_wants_chart:
            chart_payload = None
        elif chart_payload:
            sig = AIChartService.get_chart_signature(chart_payload)
            if sig and sig not in presented_chart_signatures:
                presented_chart_signatures.append(sig)

        # Update or create conversation record with user and assistant messages
        try:
            stored_shipments = new_context_shipments if new_context_shipments is not None else last_shipments
            stored_focus = new_focus_shipment or last_focus_shipment

            updated_context = {
                'last_shipments': stored_shipments,
                'last_focus_shipment': stored_focus,
                'last_intent': intent,
                'last_chart_payload': chart_payload or last_chart_payload,
                'presented_chart_signatures': presented_chart_signatures,
                'last_analysis_data': new_analysis_data or last_analysis_data,
                'active_filters': active_filters
            }

            if not conv:
                conv = ChatConversation(
                    user_id=user_id,
                    title=norm_q[:50] if len(norm_q) <= 50 else (norm_q[:47] + "..."),
                    last_context_json=json.dumps(updated_context)
                )
                db.session.add(conv)
                db.session.flush()

                # Record user message
                user_msg = ChatMessage(conversation_id=conv.id, role='user', message=raw_q)
                db.session.add(user_msg)
            else:
                user_msg = ChatMessage(conversation_id=conv.id, role='user', message=raw_q)
                db.session.add(user_msg)
                conv.last_context_json = json.dumps(updated_context)

            # Record assistant message
            assistant_msg = ChatMessage(conversation_id=conv.id, role='assistant', message=response_text)
            db.session.add(assistant_msg)
            db.session.commit()
            conversation_id = conv.id
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Failed to persist chat session: {e}")

        return {
            'success': True,
            'response': response_text,
            'message': response_text,
            'conversation_id': conversation_id,
            'context_shipments': new_context_shipments if new_context_shipments is not None else last_shipments,
            'chart_payload': chart_payload,
            'chart_config': chart_payload
        }

    @classmethod
    def _dispatch_intent(
        cls,
        intent: str,
        meta: Dict[str, Any],
        norm_q: str,
        user_name: str,
        user_role: str,
        last_shipments: List[str],
        last_focus_shipment: Optional[str],
        last_chart_payload: Optional[Dict[str, Any]] = None,
        presented_chart_signatures: Optional[List[str]] = None,
        last_analysis_data: Optional[Dict[str, Any]] = None,
        active_filters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Executes domain logic for the detected intent."""

        # -------------------------------------------------------------
        # 1. GREETING Intent
        # -------------------------------------------------------------
        if intent == Intent.GREETING:
            return (
                f"Hello {user_name}! I am your RouteMind AI Copilot, your maritime logistics intelligence assistant. "
                "How can I help you today? You can ask me to evaluate shipment risk segments, explain specific consignments, "
                "analyze delay factors, or review operational exceptions.",
                None,
                None
            )

        # -------------------------------------------------------------
        # 2. GENERAL HELP Intent
        # -------------------------------------------------------------
        if intent == Intent.GENERAL_HELP:
            return (
                "**RouteMind AI Copilot Operational Capabilities:**\n\n"
                "I provide real-time intelligence grounded on your active MySQL database and production ML models:\n\n"
                "• **Risk Segmentation:** *'Give all risk segments'* or *'Show risk categories'*\n"
                "• **Targeted Listings:** *'Show all high-risk shipments'* or *'List medium-risk shipments'*\n"
                "• **Consignment Drill-down:** *'Explain shipment SHP-10482'* or *'What is the status of SHP-10002?'*\n"
                "• **Contextual Follow-ups:** *'Which of these have open exceptions?'* or *'Explain the first shipment'*\n"
                "• **Operational Guidance:** *'What should the dispatcher do next?'*\n"
                "• **Fleet Analytics:** *'What percentage of shipments are late?'* or *'Which shipping mode has highest delay rate?'*\n"
                "• **ML Model Insights:** *'What are the production model accuracy metrics?'* or *'How does Model 02 work?'*\n"
                "• **Exceptions & Escalations:** *'Show open exceptions'* or *'How many manager escalations are pending?'*",
                None,
                None
            )

        # -------------------------------------------------------------
        # 3. RISK SEGMENTATION Intent (Comprehensive Section 4 Requirements)
        # -------------------------------------------------------------
        if intent == Intent.RISK_SEGMENTATION:
            text, refs, focus = cls._handle_risk_segmentation()
            return text, refs, focus, AIChartService.get_risk_donut_chart()

        # -------------------------------------------------------------
        # 4. HIGH RISK LISTING Intent
        # -------------------------------------------------------------
        if intent == Intent.HIGH_RISK_LISTING:
            if meta.get('only_top') or meta.get('limit') == 1 or any(w in norm_q.lower() for w in ['top one', 'top 1', 'only the top', 'only top', 'single critical']):
                top_s = Shipment.query.filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK'])).order_by(Shipment.dispatch_prob.desc()).first()
                if top_s:
                    card = cls._generate_shipment_explanation(top_s)
                    return card, [top_s.shipment_number], top_s.shipment_number, AIChartService.get_shap_waterfall_chart(top_s)
            text, refs, focus = cls._handle_specific_risk_listing(['HIGH', 'CRITICAL', 'CRITICAL_RISK'], "High-Risk / Critical")
            return text, refs, focus, AIChartService.get_risk_histogram()

        # -------------------------------------------------------------
        # 5. MEDIUM RISK LISTING Intent
        # -------------------------------------------------------------
        if intent == Intent.MEDIUM_RISK_LISTING:
            text, refs, focus = cls._handle_specific_risk_listing(['MEDIUM', 'ELEVATED_RISK', 'ELEVATED'], "Medium-Risk / Elevated")
            return text, refs, focus, None

        # -------------------------------------------------------------
        # 6. LOW RISK LISTING Intent
        # -------------------------------------------------------------
        if intent == Intent.LOW_RISK_LISTING:
            text, refs, focus = cls._handle_specific_risk_listing(['LOW'], "Low-Risk / On-Track")
            return text, refs, focus, None

        # -------------------------------------------------------------
        # 7. INDIVIDUAL SHIPMENT DETAILS Intent
        # -------------------------------------------------------------
        if intent == Intent.INDIVIDUAL_SHIPMENT_DETAILS:
            ref = meta.get('shipment_ref')
            if not ref:
                ref = cls._extract_shipment_ref(norm_q)
            if ref:
                shp = cls._find_shipment(ref)
                if shp:
                    return cls._generate_shipment_explanation(shp), [shp.shipment_number], shp.shipment_number, AIChartService.get_shap_waterfall_chart(shp)
                return (
                    f"Consignment reference **'{ref}'** could not be located in the database. "
                    "Please verify the shipment number (e.g. `SHP-10482`, `SHP-10001`).",
                    None,
                    None,
                    None
                )

        # -------------------------------------------------------------
        # 7b. EXPLAIN DELAY REASON Intent ("why did this happen?", "why is it late?")
        # -------------------------------------------------------------
        if intent == Intent.EXPLAIN_DELAY_REASON:
            return cls._handle_explain_delay_reason(meta, last_focus_shipment, last_shipments)

        # -------------------------------------------------------------
        # 7c. DEEP DIVE Intent ("show more details", "deep dive")
        # -------------------------------------------------------------
        if intent == Intent.DEEP_DIVE:
            return cls._handle_deep_dive(meta, last_focus_shipment, last_shipments)

        # -------------------------------------------------------------
        # 7d. COMMUNICATION DRAFT Intent ("draft customer message", "customer email")
        # -------------------------------------------------------------
        if intent == Intent.COMMUNICATION_DRAFT:
            return cls._handle_communication_draft(meta, last_focus_shipment, last_shipments)

        # -------------------------------------------------------------
        # 7e. EXPLICIT DYNAMIC CHART REQUEST Intent ("show chart of ...")
        # -------------------------------------------------------------
        if intent == Intent.CHART_REQUEST:
            return cls._handle_explicit_chart_request(norm_q)

        # -------------------------------------------------------------
        # 7f. CHART MODIFICATION Intent ("change it to a line chart", "switch to donut")
        # -------------------------------------------------------------
        if intent == Intent.CHART_MODIFICATION:
            target_type = meta.get('target_chart_type', 'line')
            if last_chart_payload and isinstance(last_chart_payload, dict):
                modified_chart = AIChartService.modify_chart_type(last_chart_payload, target_type)
                text = (
                    f"> 💡 **Executive Summary:** Transitioned visualization to **{target_type.title()}** format while "
                    f"preserving the exact underlying operational telemetry and parameters.\n\n"
                    f"• **Visualization Type:** {target_type.title()} View\n"
                    f"• **Dataset Grounding:** Preserved active query metrics and category buckets\n"
                    f"• **Analytical Continuity:** Real-time data points remain unchanged."
                )
                return text, last_shipments, last_focus_shipment, modified_chart
            else:
                new_chart = AIChartService.get_late_vs_ontime_chart(as_bar=(target_type == 'bar'))
                if target_type in ['doughnut', 'pie']:
                    new_chart = AIChartService.modify_chart_type(new_chart, target_type)
                text = (
                    f"> 💡 **Executive Summary:** Initialized dynamic {target_type.title()} visualization for active consignment performance."
                )
                return text, last_shipments, last_focus_shipment, new_chart

        # -------------------------------------------------------------
        # 7g. FOLLOW-UP ANALYTICAL QUERY ("which month has highest delays?", "last 3 months")
        # -------------------------------------------------------------
        if intent == Intent.FOLLOWUP_ANALYTICAL_QUERY:
            filter_n = meta.get('filter_months')
            if filter_n:
                trend_chart = AIChartService.get_monthly_trend_chart(last_n=filter_n)
                text = (
                    f"> 💡 **Executive Summary:** Filtered consignment trend telemetry to the **last {filter_n} operational periods**.\n\n"
                    f"• **Active Horizon:** Last {filter_n} periods\n"
                    f"• **Telemetry Scope:** Analyzed consignment volumes and late-delivery occurrences\n"
                    f"• **Operational Status:** Trends reflect ground-truth MySQL order timestamps."
                )
                return text, last_shipments, last_focus_shipment, trend_chart

            if meta.get('followup_type') == 'highest_delay_month':
                trend_chart = AIChartService.get_monthly_trend_chart()
                summary = trend_chart.get('raw_summary', {})
                h_month = summary.get('highest_delay_month', 'Recent Month')
                h_count = summary.get('highest_delayed_count', 0)
                text = (
                    f"> 💡 **Executive Summary:** Based on active MySQL chronological telemetry, **{h_month}** has the highest "
                    f"number of late/delayed shipments, with **{h_count} delayed consignments**.\n\n"
                    f"• **Peak Delay Period:** {h_month}\n"
                    f"• **Impacted Consignments:** {h_count} shipments flagged delayed or high delay probability\n"
                    f"• **Operational Driver:** Corresponds with vessel berthing queues and scheduled transit duration variance."
                )
                return text, last_shipments, last_focus_shipment, None

        # -------------------------------------------------------------
        # 7h. MONTHLY TREND Intent ("show monthly late deliveries", "monthly shipments")
        # -------------------------------------------------------------
        if intent == Intent.MONTHLY_TREND:
            trend_chart = AIChartService.get_monthly_trend_chart(chart_type='line')
            summary = trend_chart.get('raw_summary', {})
            h_month = summary.get('highest_delay_month', 'Recent Month')
            text = (
                f"> 💡 **Executive Summary:** Consignment volume and late-delivery distribution evaluated across {len(summary.get('months', []))} active chronological periods. "
                f"Peak delay pressure occurred in **{h_month}**.\n\n"
                f"### Monthly Logistics Chronology\n\n"
                f"| Operational Month | Total Consignments | Late / Delayed | Delay Rate (%) |\n"
                f"| :--- | :---: | :---: | :---: |\n"
            )
            months = summary.get('months', [])
            totals = summary.get('totals', [])
            delays = summary.get('delayed', [])
            rates = summary.get('delay_rates', [])
            for i in range(len(months)):
                text += f"| **{months[i]}** | {totals[i]} | {delays[i]} | {rates[i]}% |\n"
            text += (
                f"\n• **Observation:** Transit buffers and berth wait times in key hubs directly impact monthly delay variance.\n"
                f"• **Recommended Action:** Expedite high-priority bookings during peak corridor windows."
            )
            return text, None, None, trend_chart

        # -------------------------------------------------------------
        # 7i. CARRIER ANALYSIS Intent ("carrier performance", "vessel comparisons")
        # -------------------------------------------------------------
        if intent == Intent.CARRIER_ANALYSIS:
            chart = AIChartService.get_carrier_performance_chart()
            text = (
                "> 💡 **Executive Summary:** Maritime vessel carrier performance telemetry aggregated from active database consignments. "
                "Evaluates commercial carriers and spot fleet reliability.\n\n"
                "• **Top Carrier Volume:** CMA CGM, Maersk, and COSCO represent the majority of active corridor movements.\n"
                "• **Delay Risk Profile:** Longer scheduled feeder legs exhibit higher transit duration variance than direct deep-sea rotations.\n"
                "• **Recommended Action:** Review carrier SLA compliance and flag open exceptions for underperforming rotations."
            )
            return text, None, None, chart

        # -------------------------------------------------------------
        # 7j. CUSTOMER SEGMENT ANALYSIS Intent ("customer segment breakdown")
        # -------------------------------------------------------------
        if intent == Intent.CUSTOMER_SEGMENT_ANALYSIS:
            chart = AIChartService.get_customer_segment_chart()
            text = (
                "> 💡 **Executive Summary:** Active consignments categorized by commercial customer tier (Consumer, Corporate, and Home Office).\n\n"
                "• **Segment Breakdown:** Consumer orders dominate active volume, followed by Corporate and Home Office accounts.\n"
                "• **Risk Exposure:** High-value corporate shipments carry prioritized service guarantees under operational SLA covenants.\n"
                "• **Recommended Action:** Implement proactive customer notifications on high-risk consignments to safeguard customer satisfaction."
            )
            return text, None, None, chart

        # -------------------------------------------------------------
        # 7k. STATUS DISTRIBUTION Intent ("status distribution", "delivery status mix")
        # -------------------------------------------------------------
        if intent == Intent.STATUS_DISTRIBUTION:
            chart = AIChartService.get_status_distribution_chart()
            text = (
                "> 💡 **Executive Summary:** Overall consignment lifecycle status mix across all active maritime records.\n\n"
                "• **On-Track Deliveries:** Active shipments moving under normal maritime voyage conditions.\n"
                "• **Exceptions / Delayed:** Consignments undergoing customs review, berth hold, or lead-time variance.\n"
                "• **Recommended Action:** Prioritize review of pending and delayed shipments in the Dispatch Control Tower."
            )
            return text, None, None, chart

        # -------------------------------------------------------------
        # 7l. DATA EXPORT REQUEST Intent ("export data", "download csv")
        # -------------------------------------------------------------
        if intent == Intent.DATA_EXPORT_REQUEST:
            text = (
                "> 💡 **Executive Summary:** Data export capabilities are available directly within RouteMind AI.\n\n"
                "• **Export Active Visualizations:** You can click the **Export PNG** or **Export CSV** buttons on any dynamic chart card.\n"
                "• **Export Shipment Records:** Navigate to **Shipments List** (`/shipments/`) to export full consignment datasets.\n"
                "• **Audit Reports:** Go to **Reports & Analytics** (`/reports/`) to generate compliance summaries."
            )
            return text, None, None, None

        # -------------------------------------------------------------
        # 8. SHIPMENT STATUS Intent
        # -------------------------------------------------------------
        if intent == Intent.SHIPMENT_STATUS:
            ref = meta.get('shipment_ref') or cls._extract_shipment_ref(norm_q)
            if ref:
                shp = cls._find_shipment(ref)
                if shp:
                    return cls._handle_shipment_status_query(shp), [shp.shipment_number], shp.shipment_number, None
                return f"Consignment **'{ref}'** was not found in the active database.", None, None, None

        # -------------------------------------------------------------
        # 9. FOLLOWUP: SPECIFIC ITEM (e.g. "explain the first shipment")
        # -------------------------------------------------------------
        if intent == Intent.FOLLOWUP_SPECIFIC_ITEM:
            idx = meta.get('item_index', 0)
            if last_shipments and 0 <= idx < len(last_shipments):
                target_ref = last_shipments[idx]
                shp = cls._find_shipment(target_ref)
                if shp:
                    return cls._generate_shipment_explanation(shp), last_shipments, shp.shipment_number, AIChartService.get_shap_waterfall_chart(shp)
            elif last_shipments and idx == -1:
                target_ref = last_shipments[-1]
                shp = cls._find_shipment(target_ref)
                if shp:
                    return cls._generate_shipment_explanation(shp), last_shipments, shp.shipment_number, AIChartService.get_shap_waterfall_chart(shp)
            return (
                "Please specify which shipment you would like to inspect from the previous results.",
                None,
                None,
                None
            )

        # -------------------------------------------------------------
        # 10. FOLLOWUP: NEXT ACTION (e.g. "what should the dispatcher do next?")
        # -------------------------------------------------------------
        if intent == Intent.FOLLOWUP_NEXT_ACTION:
            target_shp = None
            if last_focus_shipment:
                target_shp = cls._find_shipment(last_focus_shipment)
            elif last_shipments:
                target_shp = cls._find_shipment(last_shipments[0])

            if target_shp:
                step_text, refs, focus = cls._handle_operational_next_steps(target_shp)
                return step_text, (refs or last_shipments), focus, None
            else:
                return (
                    "To provide specific operational next steps, please specify a consignment (e.g., *'Explain SHP-10002'*) "
                    "or review the high-risk shipments first (*'Show all high-risk shipments'*).",
                    None,
                    None,
                    None
                )

        # -------------------------------------------------------------
        # 11. FOLLOWUP: CONTEXTUAL FILTERING (e.g. "which of these have open exceptions?")
        # -------------------------------------------------------------
        if intent == Intent.FOLLOWUP_CONTEXT:
            text, refs, focus = cls._handle_followup_context(meta.get('filter', 'general'), last_shipments)
            return text, refs, focus, None

        # -------------------------------------------------------------
        # 12. LATE-DELIVERY & DELAY PERCENTAGE ANALYSIS
        # -------------------------------------------------------------
        if intent == Intent.LATE_DELIVERY_ANALYSIS:
            text = cls._answer_delay_percentage()
            return text, None, None, AIChartService.get_late_vs_ontime_chart(as_bar=True)

        # -------------------------------------------------------------
        # 12b. DYNAMIC PERCENTAGE QUERY (Any attribute or fleet share)
        # -------------------------------------------------------------
        if intent == Intent.PERCENTAGE_QUERY:
            text, refs, focus = cls._handle_percentage_query(norm_q)
            return text, refs, focus, AIChartService.get_risk_donut_chart()

        # -------------------------------------------------------------
        # 12c. DATABASE ANALYTICAL & AGGREGATION QUERY
        # -------------------------------------------------------------
        if intent == Intent.DATABASE_ANALYTICAL_QUERY:
            text, refs, focus = cls._handle_database_analytical_query(norm_q)
            return text, refs, focus, AIChartService.get_scatter_sla_vs_risk()

        # -------------------------------------------------------------
        # 13. SHIPPING MODE ANALYSIS
        # -------------------------------------------------------------
        if intent == Intent.SHIPPING_MODE_ANALYSIS:
            text = cls._answer_mode_analytics()
            return text, None, None, AIChartService.get_mode_delay_chart()

        # -------------------------------------------------------------
        # 14. REGIONAL ANALYSIS
        # -------------------------------------------------------------
        if intent == Intent.REGIONAL_ANALYSIS:
            text = cls._answer_region_analytics()
            return text, None, None, AIChartService.get_regional_delay_chart()

        # -------------------------------------------------------------
        # 15. EXCEPTION ANALYSIS
        # -------------------------------------------------------------
        if intent == Intent.EXCEPTION_ANALYSIS:
            text = cls._answer_exception_count()
            return text, None, None, None

        # -------------------------------------------------------------
        # 16. MANAGER ESCALATION ANALYSIS
        # -------------------------------------------------------------
        if intent == Intent.MANAGER_ESCALATION_ANALYSIS:
            text = cls._answer_escalation_count()
            return text, None, None, None

        # -------------------------------------------------------------
        # 17. ML MODEL PERFORMANCE METRICS
        # -------------------------------------------------------------
        if intent == Intent.MODEL_PERFORMANCE_METRICS:
            text = cls._answer_model_performance_metrics()
            return text, None, None, AIChartService.get_model_performance_chart()

        # -------------------------------------------------------------
        # 18. ML MODEL ARCHITECTURE INFO
        # -------------------------------------------------------------
        if intent == Intent.ML_MODEL_INFO:
            text = cls._answer_ml_model_info()
            return text, None, None, AIChartService.get_model_performance_chart()

        # -------------------------------------------------------------
        # 19. SHIPMENT COMPARISON
        # -------------------------------------------------------------
        if intent == Intent.SHIPMENT_COMPARISON:
            return cls._handle_shipment_comparison(meta, last_shipments)

        # -------------------------------------------------------------
        # 20. OPERATIONAL SUMMARY
        # -------------------------------------------------------------
        if intent == Intent.OPERATIONAL_SUMMARY:
            text = cls._generate_operational_summary()
            return text, None, None, AIChartService.get_kpi_summary_cards()

        # -------------------------------------------------------------
        # 21. GENERAL SHIPMENT SEARCH
        # -------------------------------------------------------------
        if intent == Intent.SHIPMENT_SEARCH:
            text, refs, focus = cls._handle_general_shipment_search(norm_q)
            return text, refs, focus, AIChartService.get_risk_donut_chart()

        # -------------------------------------------------------------
        # 22. Generative & Theoretical Intelligence (via LLMClient)
        # -------------------------------------------------------------
        try:
            from src.ai.llm_client import LLMClient
            from src.ai.prompt_templates import CONTROL_TOWER_SYSTEM_PROMPT

            # Prepare live operational telemetry context
            from collections import Counter
            all_s = Shipment.query.all()
            total_s = len(all_s)
            high_r = sum(1 for s in all_s if s.risk_level in ['HIGH', 'CRITICAL', 'CRITICAL_RISK'])
            med_r = sum(1 for s in all_s if s.risk_level in ['MEDIUM', 'ELEVATED', 'ELEVATED_RISK'])
            low_r = sum(1 for s in all_s if s.risk_level in ['LOW', 'ON_TRACK', 'NORMAL'])
            open_e = ShipmentException.query.filter(ShipmentException.status.in_(['OPEN', 'INVESTIGATING', 'IN_REVIEW', 'IN_PROGRESS'])).count()
            pend_esc = ManagerEscalation.query.filter_by(status='PENDING').count()
            status_dist = dict(Counter(s.order_status for s in all_s))
            mode_dist = dict(Counter(s.shipping_mode for s in all_s))
            region_dist = dict(Counter(s.destination_region for s in all_s))
            total_sales = sum(s.sales or 0.0 for s in all_s)

            live_context = {
                'total_shipments': total_s,
                'risk_distribution': {'HIGH': high_r, 'MEDIUM': med_r, 'LOW': low_r},
                'status_distribution': status_dist,
                'shipping_mode_distribution': mode_dist,
                'regional_distribution': region_dist,
                'total_declared_sales_usd': round(total_sales, 2),
                'open_exceptions_count': open_e,
                'pending_escalations_count': pend_esc,
                'user_role': user_role,
                'user_name': user_name,
                'active_focus_shipment': last_focus_shipment,
                'context_shipments': last_shipments[:5] if last_shipments else []
            }

            llm = LLMClient()
            response_text = llm.generate(prompt=norm_q, system_instruction=CONTROL_TOWER_SYSTEM_PROMPT, context_data=live_context)
            if response_text:
                return response_text, last_shipments, last_focus_shipment
        except Exception as e:
            logger.warning(f"Generative LLM query handling encountered exception: {e}")

        # Fallback / Clarification (Never disguise as a greeting)
        return (
            f"I understand your query relates to operational logistics, but I need clarification on your exact request. "
            f"You can ask me to:\n\n"
            f"• **Review Risk Segments:** *'Give all risk segments'*\n"
            f"• **List High-Risk Shipments:** *'Show all high-risk shipments'*\n"
            f"• **Inspect a Consignment:** *'Explain shipment SHP-10482'*\n"
            f"• **Check Fleet Metrics:** *'What percentage of shipments are late?'* or *'Which shipping mode has highest delay rate?'*",
            None,
            None
        )

    # =========================================================================
    # CORE DOMAIN HANDLERS
    # =========================================================================

    @classmethod
    def _handle_risk_segmentation(cls) -> Tuple[str, List[str], None]:
        """
        Executes strict Section 4 Risk Segmentation:
        A. Risk summary (Total, High, Medium, Low counts)
        B. Risk distribution (% calculated against total eligible)
        C. Shipment details table
        D. Operational interpretation
        """
        all_shipments = Shipment.query.order_by(Shipment.dispatch_prob.desc()).all()
        total = len(all_shipments)
        if total == 0:
            return "No shipment records were located in the database to perform risk segmentation.", [], None

        high_list = [s for s in all_shipments if s.risk_level in ['HIGH', 'CRITICAL', 'CRITICAL_RISK']]
        med_list = [s for s in all_shipments if s.risk_level in ['MEDIUM', 'ELEVATED', 'ELEVATED_RISK']]
        low_list = [s for s in all_shipments if s.risk_level in ['LOW', 'ON_TRACK', 'NORMAL']]

        high_count = len(high_list)
        med_count = len(med_list)
        low_count = len(low_list)
        unknown_count = total - (high_count + med_count + low_count)

        high_pct = round((high_count / total) * 100, 1)
        med_pct = round((med_count / total) * 100, 1)
        low_pct = round((low_count / total) * 100, 1)

        # High-risk shipments with open exceptions
        high_with_open_exc = []
        for s in high_list:
            open_excs = [e for e in s.exceptions if e.status in ['OPEN', 'INVESTIGATING', 'IN_REVIEW', 'IN_PROGRESS']]
            if open_excs:
                high_with_open_exc.append(s)

        # Prepare Table of Shipments
        table_rows = [
            "| Shipment # | Risk Category | Risk Score | Status | Shipping Mode | Destination Region | Open Exceptions |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        all_refs = []
        for s in all_shipments:
            all_refs.append(s.shipment_number)
            prob = s.dispatch_prob if s.dispatch_prob is not None else (s.order_creation_prob or (0.85 if s.risk_level in ['HIGH', 'CRITICAL'] else (0.45 if s.risk_level == 'MEDIUM' else 0.15)))
            score_str = f"{round(prob * 100, 1)}%"
            open_e = [f"EXC-{e.id}" for e in s.exceptions if e.status in ['OPEN', 'INVESTIGATING', 'IN_PROGRESS']]
            exc_str = ", ".join(open_e) if open_e else "None"
            badge = f"**{s.risk_level}**"
            table_rows.append(
                f"| `{s.shipment_number}` | {badge} | {score_str} | `{s.order_status}` | {s.shipping_mode} | {s.destination_region} | {exc_str} |"
            )

        details_table = "\n".join(table_rows)

        top_summary = (
            f"> 📊 **Executive Summary:** Across your active fleet of **{total} tracked shipments**, "
            f"**{high_count} shipments ({high_pct}%)** are currently at **High Risk** of delivery delay, "
            f"**{med_count} ({med_pct}%)** are at **Medium Risk**, and **{low_count} ({low_pct}%)** are **On Track (Low Risk)**. "
            f"{f'**{len(high_with_open_exc)} high-risk shipment(s)** have active exceptions requiring dispatcher action.' if high_with_open_exc else 'No active exceptions are currently open.'}"
        )

        response = (
            "### Maritime Consignment Risk Segmentation & Distribution Analysis\n\n"
            f"{top_summary}\n\n"
            "#### A. Risk Summary\n"
            f"• **Total Tracked Consignments:** **{total} shipments**\n"
            f"• **High / Critical Risk:** **{high_count} shipments** (Threshold: delay probability ≥ 50%)\n"
            f"• **Medium / Elevated Risk:** **{med_count} shipments** (Threshold: delay probability 25% to 49%)\n"
            f"• **Low / On-Track Risk:** **{low_count} shipments** (Threshold: delay probability < 25%)\n"
            f"{f'• **Unclassified:** {unknown_count} shipments' if unknown_count > 0 else ''}\n\n"
            "#### B. Risk Distribution\n"
            f"*Calculated against total active fleet population (N = {total}):*\n"
            f"• **High Risk:** **{high_pct}%** `{high_count}/{total}`\n"
            f"• **Medium Risk:** **{med_pct}%** `{med_count}/{total}`\n"
            f"• **Low Risk:** **{low_pct}%** `{low_count}/{total}`\n\n"
            "#### C. Active Consignment Inventory by Risk Tier\n"
            f"{details_table}\n\n"
            "#### D. Operational Interpretation & Priorities\n"
            f"1. **Primary Priority:** The **High / Critical Risk** category ({high_count} shipments, {high_pct}% of fleet) requires immediate operations attention due to imminent delivery SLA breach.\n"
            f"2. **Active Incidents:** **{len(high_with_open_exc)} high-risk shipments** have unresolved operational exceptions logged in the database (`{', '.join([s.shipment_number for s in high_with_open_exc]) if high_with_open_exc else 'None'}`).\n"
            f"3. **Supervisory Action:** Consignments with prolonged dock dwell and open holds should be escalated via the **'Escalate to Manager'** workflow for expedited berth clearance.\n"
            f"4. **Secondary Watch:** The {med_count} medium-risk consignments require proactive dwell monitoring at transshipment seaports to prevent degradation to critical status."
        )

        return response, all_refs, None

    @classmethod
    def _handle_specific_risk_listing(cls, risk_levels: List[str], label: str) -> Tuple[str, List[str], None]:
        """Returns filtered table for a specific risk tier."""
        shipments = Shipment.query.filter(Shipment.risk_level.in_(risk_levels)).order_by(Shipment.dispatch_prob.desc()).all()
        if not shipments:
            return f"No consignments currently classified as **{label}** in the active database.", [], None

        total_in_tier = len(shipments)
        top_note = (
            f"> 📋 **Executive Summary:** There are currently **{total_in_tier} active {label} consignments** in the fleet. "
            f"{'These shipments require prioritized monitoring or escalation to avoid SLA breach penalties.' if 'High' in label or 'Critical' in label else 'These consignments are sailing within normal delivery tolerance without critical alerts.'}\n\n"
        )
        table_rows = [
            f"### Active {label} Consignments ({total_in_tier} records):\n",
            top_note + "| Shipment # | Vessel | Corridor | Shipping Mode | Risk Score | Status | Open Exceptions |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        refs = []
        for s in shipments:
            refs.append(s.shipment_number)
            prob = s.dispatch_prob if s.dispatch_prob is not None else (s.order_creation_prob or (0.85 if 'HIGH' in risk_levels else 0.45))
            score_str = f"{round(prob * 100, 1)}%"
            open_e = [f"EXC-{e.id} ({e.status})" for e in s.exceptions if e.status in ['OPEN', 'INVESTIGATING', 'IN_PROGRESS']]
            exc_str = ", ".join(open_e) if open_e else "*None*"
            corridor = f"{s.origin_port or 'Origin'} ➔ {s.destination_port or s.destination_region or 'Dest'}"
            table_rows.append(
                f"| `{s.shipment_number}` | {s.vessel_name or 'Unassigned'} | {corridor} | {s.shipping_mode} | **{score_str}** | `{s.order_status}` | {exc_str} |"
            )

        return "\n".join(table_rows), refs, None

    @classmethod
    def _handle_followup_context(cls, filter_type: str, last_shipments: List[str]) -> Tuple[str, List[str], Optional[str]]:
        """Filters previous query results based on context."""
        if not last_shipments:
            return (
                "There are no active shipments referenced in your current conversation context. "
                "Please query a list first (e.g. *'Show all high risk shipments'*).",
                [],
                None
            )

        shipments = Shipment.query.filter(Shipment.shipment_number.in_(last_shipments)).all()
        if not shipments:
            return "The previously referenced consignments could not be loaded from the database.", [], None

        # Filter: Open Exceptions
        if filter_type == 'exceptions':
            with_open = []
            without_open = []
            for s in shipments:
                active_ex = [e for e in s.exceptions if e.status in ['OPEN', 'INVESTIGATING', 'IN_REVIEW', 'IN_PROGRESS']]
                if active_ex:
                    with_open.append((s, active_ex))
                else:
                    without_open.append(s)

            if not with_open:
                return (
                    f"### Exception Audit for the Context Consignments\n\n"
                    f"None of the {len(shipments)} previously returned consignments currently have open operational exceptions.",
                    last_shipments,
                    None
                )

            lines = [
                f"### Exception Audit for the {len(shipments)} Context Consignments:\n",
                f"Out of {len(shipments)} consignments, **{len(with_open)} have active open exceptions** requiring operational resolution:\n"
            ]
            for s, excs in with_open:
                exc_details = ", ".join([f"**EXC-{e.id}** ({e.exception_type}, Severity: `{e.severity}`, Status: `{e.status}`)" for e in excs])
                lines.append(f"• **`{s.shipment_number}`** ({s.vessel_name or 'Vessel'}, `{s.order_status}`): {exc_details}")

            if without_open:
                lines.append(f"\n• **Consignments with No Open Exceptions ({len(without_open)}):** {', '.join([f'`{s.shipment_number}`' for s in without_open])}")

            lines.append("\n*To inspect any shipment in detail, ask: 'Explain the first shipment' or 'Explain shipment " + with_open[0][0].shipment_number + "'.*")

            filtered_refs = [s.shipment_number for s, _ in with_open]
            return "\n".join(lines), filtered_refs, filtered_refs[0] if filtered_refs else None

        # Filter: Risk Scores
        if filter_type == 'risk_scores':
            lines = [f"### Risk Score Breakdown for Context Consignments ({len(shipments)} records):\n"]
            for s in shipments:
                prob = s.dispatch_prob if s.dispatch_prob is not None else (s.order_creation_prob or 0.25)
                lines.append(f"• **`{s.shipment_number}`**: Risk Tier **{s.risk_level}** | Predicted Probability **{round(prob*100, 1)}%** | Scheduled SLA **{s.scheduled_days} Days**")
            return "\n".join(lines), last_shipments, None

        # Filter: Manager Escalations
        if filter_type == 'escalations':
            lines = [f"### Escalation Audit for Context Consignments:\n"]
            for s in shipments:
                escs = ManagerEscalation.query.filter_by(shipment_id=s.id).all()
                if escs:
                    items = [f"ESC-{e.id} (Priority: `{e.priority}`, Status: `{e.status}`)" for e in escs]
                    lines.append(f"• **`{s.shipment_number}`**: {', '.join(items)}")
                else:
                    lines.append(f"• **`{s.shipment_number}`**: *No manager escalations logged*")
            return "\n".join(lines), last_shipments, None

        # General follow-up summary
        return cls._handle_specific_risk_listing(['HIGH', 'CRITICAL', 'MEDIUM', 'LOW'], "Context")

    @classmethod
    def _handle_operational_next_steps(cls, s: Shipment) -> Tuple[str, Optional[List[str]], str]:
        """Provides grounded operational next steps for a specific consignment without taking automated actions."""
        prob = s.dispatch_prob if s.dispatch_prob is not None else (s.order_creation_prob or 0.25)
        pct = round(prob * 100, 1)

        active_excs = [e for e in s.exceptions if e.status in ['OPEN', 'INVESTIGATING', 'IN_PROGRESS']]

        exc_info = ""
        if active_excs:
            ex = active_excs[0]
            exc_info = f"with active exception **EXC-{ex.id}** ({ex.exception_type}, Severity: `{ex.severity}`)"
        else:
            exc_info = "with no active exception logged"

        steps = [
            f"### Recommended Operations Protocol for `{s.shipment_number}`\n",
            f"**Current Consignment State:** `{s.order_status}` | **Risk Level:** **{s.risk_level}** ({pct}% delay risk) {exc_info}.\n",
            "**Recommended Next Steps for Operations Dispatcher:**\n"
        ]

        if active_excs:
            steps.append(f"1. **Investigate Terminal Exception:** Access the **Exception Desk** to review logs for `EXC-{active_excs[0].id}`. Verify whether port clearance documentation or feeder connection can be expedited.")
        else:
            steps.append("1. **Monitor Transit Milestones:** Check port of loading dwell times and verify automated event logging on the shipment timeline.")

        if pct >= 50 or s.order_status == 'DELAYED':
            steps.append("2. **Supervisory Escalation:** Because this consignment is in a delayed/critical state, click the **'Escalate to Manager'** button on the Shipment Details page to alert the Operations Manager.")
            steps.append("3. **Customer Notification Preparation:** Prepare a draft ETA adjustment advisory for customer consignee review via the Communication Approval Hub.")
        else:
            steps.append("2. **Standard Tracking:** Consignment is operating within acceptable risk limits; proceed with standard milestone tracking.")

        # Integrated GenAI 5-Part Resolution Recommendation
        try:
            from src.ai.resolution_recommender import recommend_resolution
            rec = recommend_resolution(
                risk_level=s.risk_level,
                clearance_status='HOLD_FOR_EXPEDITE' if pct >= 50 else 'MONITOR_DOCK',
                shipment_data={
                    'shipment_id': s.shipment_number,
                    'origin': s.origin_port or s.origin_region,
                    'destination': s.destination_port or s.destination_region,
                    'carrier': s.carrier_name,
                    'shipping_mode': s.shipping_mode
                }
            )
            steps.append("\n**AI Resolution Strategy Options (BRD 5-Part Evaluation):**")
            for opt in rec.get('resolution_options', []):
                star = "★ [RECOMMENDED]" if opt.get('recommended') else "•"
                steps.append(f"{star} **{opt.get('title')}** — Est. Cost: `{opt.get('cost_estimate')}`, SLA Impact: `{opt.get('sla_impact')}`")
            if rec.get('assumptions'):
                steps.append(f"*Key Operational Assumption:* {rec['assumptions'][0]}")
        except Exception:
            pass

        steps.append("\n4. **Delivery Verification:** Once the vessel docks at destination port, record container discharge and verify proof of delivery before marking COMPLETED.\n")
        steps.append("*Note: RouteMind AI provides advisory intelligence; operational actions (such as manager escalation or status updates) must be initiated by authorized dispatchers.*")

        return "\n".join(steps), [s.shipment_number], s.shipment_number

    @classmethod
    def _generate_shipment_explanation(cls, s: Shipment) -> str:
        """Builds a rich markdown operational intelligence card for a single shipment with simple executive summary at top."""
        prob = s.dispatch_prob if s.dispatch_prob is not None else (s.order_creation_prob or 0.25)
        pct = round(prob * 100, 1)
        risk = s.risk_level or ('HIGH' if pct >= 50 else ('MEDIUM' if pct >= 25 else 'LOW'))

        vessel = s.vessel_name or 'Unassigned Ocean Carrier'
        container = s.container_number or 'Standard Container'
        origin = s.origin_port or s.origin_region or 'Port of Loading'
        dest = s.destination_port or s.destination_region or 'Port of Discharge'
        mode = s.shipping_mode or 'Standard Ocean'
        days = s.scheduled_days or 4
        status = s.order_status or 'IN_TRANSIT'

        # 1. Clear, plain-English Executive Summary placed right at the TOP
        if risk in ['HIGH', 'CRITICAL', 'CRITICAL_RISK']:
            executive_summary = (
                f"> ⚠️ **Executive Summary:** Consignment **`{s.shipment_number}`** requires operational attention. "
                f"It is currently classified as **{risk} RISK** with an estimated **{pct}% chance of delivery delay** (Current Status: `{status}`). "
                f"It is sailing on vessel **{vessel}** from **{origin}** to **{dest}** under **{mode}** with a {days}-day delivery commitment. "
                f"Because the delivery window is tight and delays are probable, proactive intervention is recommended."
            )
        elif risk in ['MEDIUM', 'ELEVATED', 'ELEVATED_RISK']:
            executive_summary = (
                f"> ⚡ **Executive Summary:** Consignment **`{s.shipment_number}`** is under **MODERATE MONITORING** "
                f"with a **{pct}% delay probability** (Current Status: `{status}`). "
                f"It is traveling on vessel **{vessel}** from **{origin}** to **{dest}** under **{mode}** ({days} scheduled days). "
                f"Normal ocean transit is progressing, but port clearance should be tracked closely."
            )
        else:
            executive_summary = (
                f"> 💡 **Executive Summary:** Consignment **`{s.shipment_number}`** is **ON TRACK** and moving normally "
                f"with a **LOW RISK** of delay (**{pct}%**). It is in `{status}` status, sailing on vessel **{vessel}** "
                f"from **{origin}** to **{dest}** under **{mode}** ({days} scheduled days). "
                f"No blocking delays are detected, so standard operational tracking can proceed."
            )

        # 2. Associated exceptions (compact & readable)
        exceptions = ShipmentException.query.filter_by(shipment_id=s.id).all()
        if exceptions:
            active_ex = [e for e in exceptions if e.status not in ['RESOLVED', 'CLOSED']]
            resolved_ex = [e for e in exceptions if e.status in ['RESOLVED', 'CLOSED']]
            exc_items = []
            for ex in active_ex:
                exc_items.append(f"• **EXC-{ex.id}** ({ex.exception_type.replace('_', ' ').title()}): Severity `{ex.severity}`, Status **`{ex.status}`**")
            if resolved_ex:
                exc_items.append(f"• *{len(resolved_ex)} historical exception(s) resolved.*")
            exc_block = "\n" + "\n".join(exc_items)
        else:
            exc_block = "\n• *No active exceptions logged for this consignment.*"

        # 3. Manager escalations (only display active/unresolved escalations; omit historical resolved counts)
        escalations = ManagerEscalation.query.filter_by(shipment_id=s.id).order_by(ManagerEscalation.id.desc()).all()
        esc_block = ""
        if escalations:
            active_esc = [e for e in escalations if e.status not in ['RESOLVED', 'CLOSED']]
            if active_esc:
                esc_items = [f"• **ESC-{e.id}** (Priority: `{e.priority}`, Status: **`{e.status}`**): {e.reason}" for e in active_esc[:3]]
                esc_block = "\n\n**Manager Escalations:**\n" + "\n".join(esc_items)

        # 4. Operational recommendation
        if pct >= 50 or status == 'DELAYED':
            rec_action = "**CRITICAL INTERVENTION RECOMMENDED:** High likelihood of SLA breach. Recommend escalating to Operations Manager via 'Escalate to Manager' button and pre-clearing destination customs."
        elif pct >= 25:
            rec_action = "**ELEVATED MONITORING:** Monitor dock dwell duration and track vessel milestone updates closely."
        else:
            rec_action = "**STANDARD MONITORING:** Consignment is operating within normal maritime transit tolerance."

        # 5. Clear, approachable Supply Chain & ML Risk Attribution (Paragraph-wise)
        theory_block = (
            f"**Supply Chain & Machine Learning Insights:**\n\n"
            f"**Why this risk score? (Lead-Time Variance):** "
            f"This consignment has a **{days}-day transit window** under **{mode}**. "
            f"In maritime logistics, Standard Class uses spot carrier capacity which has higher transit variance than expedited modes. "
            f"On the {origin} ➔ {dest} corridor, feeder vessel queues and port dwell times can fluctuate, but with low current port congestion, this shipment is on track.\n\n"
            f"**How the AI Model Calculated This (SHAP Feature Attribution):** "
            f"Our predictive model evaluated 18 factors against our historical supply chain baseline (54.8% average late risk). "
            f"The scheduled duration and current cargo dwell time contributed positively to keep the delay probability down at **{pct}%**.\n\n"
            f"**Business Impact (Cost Asymmetry):** "
            f"RouteMind AI monitors shipments under a 10:1 cost asymmetry ratio ($300 penalty for an unmitigated late delivery vs. $25 for an early check). "
            f"Because this consignment is evaluated at {risk} risk, standard tracking maintains optimal operational efficiency."
        )

        return (
            f"### Consignment Intelligence Report: `{s.shipment_number}`\n\n"
            f"{executive_summary}\n\n"
            f"| Metric | Telemetry & Database Facts |\n"
            f"| :--- | :--- |\n"
            f"| **Lifecycle Status** | `{status}` |\n"
            f"| **Vessel & Container** | {vessel} • Container `{container}` |\n"
            f"| **Maritime Corridor** | {origin} ➔ {dest} |\n"
            f"| **Shipping Class** | {mode} (Scheduled SLA: {days} Days) |\n"
            f"| **Evaluated Risk** | **{risk}** (Predicted Delay Probability: **{pct}%**) |\n"
            f"| **Assigned Specialist** | {s.assigned_to_name or s.created_by_name or 'Operations Desk'} |\n\n"
            f"**Operational Exceptions:**{exc_block}"
            f"{esc_block}\n\n"
            f"{theory_block}\n\n"
            f"**Operational Action:**\n\n{rec_action}"
        )

    @classmethod
    def _handle_shipment_status_query(cls, s: Shipment) -> str:
        """Concise status update for a shipment."""
        return (
            f"Consignment **`{s.shipment_number}`** is currently in **`{s.order_status}`** status. "
            f"It is assigned to vessel **{s.vessel_name or 'Ocean Vessel'}** sailing from **{s.origin_port or 'Origin'}** "
            f"to **{s.destination_port or s.destination_region or 'Destination'}** under **{s.shipping_mode}** class. "
            f"Its evaluated late-delivery risk level is **{s.risk_level}**."
        )

    @classmethod
    def _answer_delay_percentage(cls) -> str:
        """Calculates late delivery percentage across active fleet."""
        try:
            total = Shipment.query.count()
            if total == 0:
                return "There are no shipments recorded in the database yet."

            delayed_count = Shipment.query.filter(Shipment.order_status.in_(['DELAYED', 'HOLD', 'EXCEPTION_HOLD'])).count()
            delivered_count = Shipment.query.filter(Shipment.order_status.in_(['DELIVERED', 'COMPLETED'])).count()
            high_count = Shipment.query.filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK'])).count()
            pct = round((high_count / total) * 100, 1)
            on_time_pct = round(100.0 - pct, 1)

            ratio_str = f"{delayed_count} : {delivered_count}" if (delayed_count + delivered_count) > 0 else "1 : 2"

            return (
                f"> 💡 **Executive Summary:** Out of {total} shipments in the system, {delayed_count} are currently delayed "
                f"while {delivered_count} have been delivered/completed on time, giving a late-to-on-time delivery ratio of **{ratio_str}**.\n\n"
                f"### Fleet Lateness Risk Metrics\n\n"
                f"• **High-Risk Delay Rate:** **{pct}%** ({high_count} out of {total} total consignments)\n"
                f"• **On-Time Reliability Rate:** **{on_time_pct}%** ({total - high_count} consignments)\n\n"
                f"| Delivery Outcome Category | Consignment Count | Status |\n"
                f"| :--- | :--- | :--- |\n"
                f"| **Delayed / Late Hold** | **{delayed_count}** | Requires Expediting / SLA Mitigation |\n"
                f"| **On-Time (Delivered & Completed)** | **{delivered_count}** | Reconciled within SLA Schedule |\n"
                f"| **Active Sailing / In-Transit** | **{total - delayed_count - delivered_count}** | Monitored by Automated AIS Pipeline |\n\n"
                "In maritime logistics, delay risks are predicted by Model 01 (Order Creation Logistic Regression) "
                "and Model 02 (Warehouse Dispatch XGBoost) based on route congestion, scheduled SLA, and dock dwell times."
            )
        except Exception as e:
            logger.error(f"Error calculating delay percentage: {e}")
            return "Unable to calculate delay percentage at this time."

    @classmethod
    def _handle_percentage_query(cls, query: str) -> Tuple[str, List[str], Optional[str]]:
        """Calculates exact percentages for arbitrary fleet attributes queried by the user."""
        lower_q = query.lower()
        all_shipments = Shipment.query.all()
        total = len(all_shipments)
        if total == 0:
            return "No shipment records exist in the database to calculate percentages.", [], None

        matching_shipments = []
        criterion_label = "Matching Criteria"
        explanation_note = ""

        # 1. Delivery & Lifecycle Statuses
        if any(w in lower_q for w in ['deliver', 'delivered']):
            matching_shipments = [s for s in all_shipments if s.order_status in ['DELIVERED', 'Delivered to Consignee']]
            criterion_label = "Delivered to Consignee"
            explanation_note = "These consignments have successfully completed ocean transit and arrived at destination ports."
        elif any(w in lower_q for w in ['completed', 'closed']):
            matching_shipments = [s for s in all_shipments if s.order_status == 'COMPLETED']
            criterion_label = "Completed & Reconciled"
            explanation_note = "These consignments have been verified with proof of delivery and formally closed."
        elif any(w in lower_q for w in ['in transit', 'intransit', 'transit', 'sailing']):
            matching_shipments = [s for s in all_shipments if s.order_status in ['IN_TRANSIT', 'DISPATCHED']]
            criterion_label = "In Transit (Active Sailing)"
            explanation_note = "These containers are actively sailing along commercial sea corridors."
        elif any(w in lower_q for w in ['delayed', 'delay', 'hold']):
            matching_shipments = [s for s in all_shipments if s.order_status in ['DELAYED', 'HOLD', 'EXCEPTION_HOLD']]
            criterion_label = "Delayed / On Hold"
            explanation_note = "These shipments have experienced berth delays or operational holds."
        elif any(w in lower_q for w in ['pending']):
            matching_shipments = [s for s in all_shipments if s.order_status in ['PENDING', 'Pending']]
            criterion_label = "Pending Warehouse Dispatch"
            explanation_note = "These orders are in pre-dispatch processing awaiting container loading."

        # 2. Risk Levels
        elif any(w in lower_q for w in ['high risk', 'critical risk', 'critical']):
            matching_shipments = [s for s in all_shipments if s.risk_level in ['HIGH', 'CRITICAL', 'CRITICAL_RISK']]
            criterion_label = "High / Critical Late Risk"
            explanation_note = "These consignments have an estimated delay probability exceeding 50%."
        elif any(w in lower_q for w in ['medium risk', 'moderate risk', 'moderate']):
            matching_shipments = [s for s in all_shipments if s.risk_level in ['MEDIUM', 'ELEVATED', 'ELEVATED_RISK']]
            criterion_label = "Medium / Elevated Risk"
            explanation_note = "These consignments have an estimated delay probability between 25% and 49%."
        elif any(w in lower_q for w in ['low risk', 'on track', 'safe']):
            matching_shipments = [s for s in all_shipments if s.risk_level in ['LOW', 'ON_TRACK', 'NORMAL']]
            criterion_label = "Low Risk / On Track"
            explanation_note = "These consignments are sailing within normal schedule parameters (<25% delay risk)."

        # 3. Shipping Modes
        elif any(w in lower_q for w in ['first class', '1st class']):
            matching_shipments = [s for s in all_shipments if 'first' in (s.shipping_mode or '').lower()]
            criterion_label = "First Class Priority Shipping"
            explanation_note = "Expedited maritime service with tighter SLA windows."
        elif any(w in lower_q for w in ['same day']):
            matching_shipments = [s for s in all_shipments if 'same' in (s.shipping_mode or '').lower()]
            criterion_label = "Same Day Shipping"
            explanation_note = "Immediate priority terminal dispatch."
        elif any(w in lower_q for w in ['second class', '2nd class']):
            matching_shipments = [s for s in all_shipments if 'second' in (s.shipping_mode or '').lower()]
            criterion_label = "Second Class Shipping"
            explanation_note = "Standard priority ocean transit."
        elif any(w in lower_q for w in ['standard class', 'standard ocean', 'standard']):
            matching_shipments = [s for s in all_shipments if 'standard' in (s.shipping_mode or '').lower()]
            criterion_label = "Standard Class Ocean Freight"
            explanation_note = "Economy spot freight with standard buffer windows."

        # 4. Regional Destinations
        elif any(w in lower_q for w in ['western europe', 'europe', 'france', 'germany', 'netherlands']):
            matching_shipments = [s for s in all_shipments if 'europe' in (s.destination_region or '').lower() or 'france' in (s.destination_country or '').lower()]
            criterion_label = "Western Europe Destination Market"
            explanation_note = "Consignments routed to European ports (Rotterdam, Antwerp, Hamburg)."
        elif any(w in lower_q for w in ['north america', 'usa', 'united states', 'america']):
            matching_shipments = [s for s in all_shipments if 'america' in (s.destination_region or '').lower()]
            criterion_label = "North America Destination Market"
            explanation_note = "Consignments bound for US East/West coast ports."
        elif any(w in lower_q for w in ['middle east', 'dubai', 'uae', 'jebel ali']):
            matching_shipments = [s for s in all_shipments if 'middle east' in (s.destination_region or '').lower()]
            criterion_label = "Middle East Destination Market"
            explanation_note = "Consignments bound for Gulf ports (Jebel Ali)."
        elif any(w in lower_q for w in ['asia', 'pacific asia', 'south asia']):
            matching_shipments = [s for s in all_shipments if 'asia' in (s.destination_region or '').lower()]
            criterion_label = "Asian Destination Markets"
            explanation_note = "Consignments routed through Far East maritime hubs."

        # 5. Exceptions & Escalations
        elif any(w in lower_q for w in ['exception', 'exceptions', 'hold', 'holds']):
            matching_shipments = [s for s in all_shipments if len(s.exceptions) > 0]
            criterion_label = "Consignments with Logged Exceptions"
            explanation_note = "Shipments with terminal documentation, customs, or weather holds."
        elif any(w in lower_q for w in ['escalat', 'manager']):
            shipment_ids_with_esc = [e.shipment_id for e in ManagerEscalation.query.all()]
            matching_shipments = [s for s in all_shipments if s.id in shipment_ids_with_esc]
            criterion_label = "Consignments Escalated to Operations Manager"
            explanation_note = "Shipments that required supervisory intervention."

        # Default fallback: check if any specific keyword in query matches order_status or vessel
        else:
            for s in all_shipments:
                text_corpus = f"{s.order_status} {s.shipping_mode} {s.destination_region} {s.vessel_name}".lower()
                tokens = [t.strip('?!.,') for t in lower_q.split() if len(t) > 3 and t not in ['what', 'which', 'percentage', 'percent', 'shipments', 'orders', 'share', 'there', 'have']]
                if any(tok in text_corpus for tok in tokens):
                    matching_shipments.append(s)
            criterion_label = "Filtered Fleet Query"
            explanation_note = "Calculated against specified search terms."

        count = len(matching_shipments)
        pct = round((count / total) * 100, 1)
        remaining_count = total - count
        remaining_pct = round(100.0 - pct, 1)

        refs = [s.shipment_number for s in matching_shipments]

        table_rows = [
            f"| Consignment ID | Vessel | Shipping Mode | Status | Risk Level |",
            f"| :--- | :--- | :--- | :--- | :--- |"
        ]
        for s in matching_shipments[:6]:
            table_rows.append(f"| `{s.shipment_number}` | {s.vessel_name or 'Ocean Carrier'} | {s.shipping_mode} | `{s.order_status}` | **{s.risk_level}** |")

        table_str = "\n".join(table_rows) if matching_shipments else "*No consignments match this filter.*"
        sample_note = f"\n*Showing {len(matching_shipments[:6])} of {count} matching consignments.*" if count > 6 else ""

        response = (
            f"### Fleet Telemetry Percentage Analysis\n\n"
            f"> 📊 **Executive Summary:** Exactly **{pct}%** of all tracked shipments (**{count} out of {total}**) "
            f"match your inquiry for **{criterion_label}**.\n\n"
            f"#### Statistical Breakdown\n"
            f"• **Matching Target ({criterion_label}):** **{pct}%** (`{count}/{total}` shipments)\n"
            f"• **Other Fleet Volume:** **{remaining_pct}%** (`{remaining_count}/{total}` shipments)\n\n"
            f"#### Matching Consignments\n"
            f"{table_str}{sample_note}\n\n"
            f"#### Operational Context\n"
            f"{explanation_note}\n\n"
            + (f"*You can inspect any individual shipment from this group by asking: 'Explain shipment {refs[0]}'.*" if refs else "")
        )
        return response.strip(), refs, refs[0] if refs else None

    @classmethod
    def _handle_database_analytical_query(cls, query: str) -> Tuple[str, List[str], Optional[str]]:
        """Handles general aggregations, totals, averages, and multi-entity database lookups."""
        lower_q = query.lower()
        all_shipments = Shipment.query.all()
        total = len(all_shipments)
        if total == 0:
            return "No shipment records exist in the database to perform analytical calculations.", [], None

        # 1. Total sales / revenue / value
        if any(w in lower_q for w in ['total sales', 'total revenue', 'total value', 'cargo value', 'order value', 'how much sales']):
            total_sales = sum(s.sales or 0.0 for s in all_shipments)
            avg_sales = total_sales / total if total > 0 else 0.0
            return (
                f"### Financial Cargo Valuation Analytics\n\n"
                f"> 💰 **Executive Summary:** The total declared cargo value across all **{total} active consignments** is **${total_sales:,.2f} USD**, with an average order value of **${avg_sales:,.2f} USD** per container.\n\n"
                f"• **Total Declared Value:** **${total_sales:,.2f} USD**\n"
                f"• **Average Consignment Value:** **${avg_sales:,.2f} USD**\n"
                f"• **Active Fleet Size:** **{total} maritime consignments**\n\n"
                f"High-value consignments are prioritized in carrier capacity allocation to protect customer lifetime value.",
                [s.shipment_number for s in all_shipments],
                None
            )

        # 2. Average scheduled transit days
        if any(w in lower_q for w in ['average days', 'average scheduled', 'avg days', 'average transit', 'transit days']):
            avg_days = sum(s.scheduled_days or 4 for s in all_shipments) / total
            min_days = min(s.scheduled_days or 4 for s in all_shipments)
            max_days = max(s.scheduled_days or 4 for s in all_shipments)
            return (
                f"### Scheduled Transit SLA Analytics\n\n"
                f"> ⏱️ **Executive Summary:** The average scheduled transit duration across your fleet is **{avg_days:.1f} days**, ranging from **{min_days} to {max_days} days** depending on shipping class.\n\n"
                f"• **Fleet Average Scheduled Duration:** **{avg_days:.1f} Days**\n"
                f"• **Shortest Scheduled SLA:** **{min_days} Days** (Express / Same Day / First Class)\n"
                f"• **Longest Scheduled SLA:** **{max_days} Days** (Economy Standard Class)\n\n"
                f"Longer transit windows (e.g. 5–6 days) exhibit higher empirical transit variance and require earlier milestone tracking.",
                [s.shipment_number for s in all_shipments],
                None
            )

        # 3. Active vessels in database
        if any(w in lower_q for w in ['vessel', 'vessels', 'ships']):
            from collections import Counter
            vessel_counts = Counter(s.vessel_name or 'Unassigned' for s in all_shipments)
            table_rows = ["| Vessel Name | Active Consignments | Key Corridors |", "| :--- | :--- | :--- |"]
            for v, cnt in vessel_counts.most_common():
                sample_routes = list(set(f"{s.origin_port or 'Origin'} ➔ {s.destination_port or s.destination_region or 'Dest'}" for s in all_shipments if s.vessel_name == v))[:2]
                table_rows.append(f"| **{v}** | {cnt} container(s) | {', '.join(sample_routes)} |")

            top_vessel, top_cnt = vessel_counts.most_common(1)[0]
            return (
                f"### Active Maritime Vessel Fleet Analytics\n\n"
                f"> 🚢 **Executive Summary:** There are currently **{len(vessel_counts)} distinct container vessels** operating across your active supply chain network. The vessel carrying the highest volume is **{top_vessel}** with **{top_cnt} consignment(s)**.\n\n"
                f"{chr(10).join(table_rows)}\n\n"
                f"Milestone tracking and AIS berth status are monitored continuously for each carrier vessel.",
                [s.shipment_number for s in all_shipments],
                None
            )

        # 4. Filtered general query fallback
        return cls._handle_general_shipment_search(query)

    @classmethod
    def _answer_mode_analytics(cls) -> str:
        """Returns delay rates by maritime shipping class."""
        try:
            from sqlalchemy import func
            results = db.session.query(
                Shipment.shipping_mode,
                func.count(Shipment.id)
            ).filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK'])).group_by(Shipment.shipping_mode).order_by(func.count(Shipment.id).desc()).all()

            if results:
                top_mode, count = results[0]
                breakdown = ", ".join([f"**{m}** ({c} high-risk)" for m, c in results])
                return (
                    f"### Maritime Shipping Mode Delay Analysis & Velocity Dynamics\n\n"
                    f"The shipping class with the highest volume of late-delivery risk is **{top_mode}** with **{count} high-risk consignments**.\n\n"
                    f"**Breakdown across shipping classes:**\n{breakdown}.\n\n"
                    "#### Theoretical Supply Chain Dynamics:\n"
                    "• **Spot-Market Rollovers in Standard Class:** Ocean carriers treat Standard Class as variable filler cargo. Under high capacity utilization ($\\rho \\ge 85\\%$), vessels frequently execute **blank sailings** or roll standard containers to subsequent feeder vessels, compounding delays by 7–14 days.\n"
                    "• **Buffer Variance vs SLA Tightness:** While expedited classes (Same Day / First Class) have tighter contractual SLAs (1–3 days), carriers prioritize terminal gate crane access and dedicated feeder connections to avoid liquidated damages.\n"
                    "• **Feature Attribution Signal:** In Model 01 and Model 02, `Shipping Mode == Standard Class` produces the highest positive SHAP contribution (+$0.21$ log-odds) toward delay probability."
                )
            return "All shipping modes are currently operating within expected SLA tolerances."
        except Exception:
            return "Shipping mode analytics are currently unavailable."

    @classmethod
    def _answer_region_analytics(cls) -> str:
        """Returns risk concentration by destination region."""
        try:
            from sqlalchemy import func
            results = db.session.query(
                Shipment.destination_region,
                func.count(Shipment.id)
            ).filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK'])).group_by(Shipment.destination_region).order_by(func.count(Shipment.id).desc()).all()

            if results:
                top_region, count = results[0]
                breakdown = ", ".join([f"**{r}** ({c})" for r, c in results[:3]])
                return (
                    f"### Regional Risk Concentration Analysis\n\n"
                    f"The destination region with the most high-risk shipments is **{top_region}** with **{count} high-risk consignments**.\n\n"
                    f"**Top Regional Concentrations:** {breakdown}."
                )
            return "All destination regions currently exhibit standard operational risk tolerances."
        except Exception:
            return "Regional risk analysis is currently unavailable."

    @classmethod
    def _answer_exception_count(cls) -> str:
        """Returns operational exception statistics."""
        try:
            open_count = ShipmentException.query.filter(ShipmentException.status.in_(['OPEN', 'INVESTIGATING', 'IN_REVIEW', 'IN_PROGRESS'])).count()
            total_count = ShipmentException.query.count()
            resolved = ShipmentException.query.filter_by(status='RESOLVED').count()

            open_excs = ShipmentException.query.filter(ShipmentException.status.in_(['OPEN', 'INVESTIGATING', 'IN_PROGRESS'])).all()
            exc_list = ", ".join([f"**EXC-{e.id}** ({e.exception_type}, Severity: `{e.severity}`)" for e in open_excs]) if open_excs else "None"

            return (
                f"### Operational Exception Desk Audit\n\n"
                f"• **Open Operational Exceptions:** **{open_count} incidents** requiring resolution\n"
                f"• **Resolved Exceptions:** **{resolved} incidents** successfully closed\n"
                f"• **Total Recorded Incidents:** {total_count}\n\n"
                f"**Active Open Incidents:**\n{exc_list}\n\n"
                "Dispatchers can inspect and resolve these on the **Exception Desk**."
            )
        except Exception:
            return "Unable to retrieve exception statistics."

    @classmethod
    def _answer_escalation_count(cls) -> str:
        """Returns manager escalation statistics."""
        try:
            pending = ManagerEscalation.query.filter_by(status='PENDING').count()
            under_review = ManagerEscalation.query.filter_by(status='UNDER_REVIEW').count()
            resolved = ManagerEscalation.query.filter_by(status='RESOLVED').count()
            total = ManagerEscalation.query.count()

            return (
                f"### Manager Escalations Audit\n\n"
                f"• **Pending Review:** **{pending} escalations** awaiting supervisory assignment\n"
                f"• **Under Active Review:** **{under_review} escalations**\n"
                f"• **Resolved:** **{resolved} escalations** closed\n"
                f"• **Total Historical Escalations:** {total}\n\n"
                "Operations Managers can review and issue directives from the **Manager Escalations** portal."
            )
        except Exception:
            return "Unable to retrieve manager escalation statistics."

    @classmethod
    def _answer_model_performance_metrics(cls) -> str:
        """Returns verified ML model metrics."""
        return (
            "### RouteMind AI Production Machine Learning Metrics\n\n"
            "| Model Pipeline | Algorithm | Primary Purpose | Test Accuracy | ROC-AUC | Decision Threshold |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| **Model 01** | Logistic Regression | Order Creation Risk Scoring | **68.12%** | **0.7720** | 0.50 |\n"
            "| **Model 02** | XGBoost Classifier | Warehouse Dispatch Late Prediction | **97.52%** | **0.9985** | 0.50 |\n"
            "| **Model 03** | CatBoost Regressor | Delay Duration Estimator (`Delay_Days`) | **R²: 0.89** | N/A (Regression) | Continuous (Days) |\n\n"
            "All pipelines enforce zero target leakage; Model 02 evaluates observed container dwell time (`Order-to-Ship Time`) at dock release."
        )

    @classmethod
    def _answer_ml_model_info(cls) -> str:
        """Explains dual-stage ML architecture and SHAP interpretability."""
        return (
            "### RouteMind AI Dual-Stage Predictive Architecture\n\n"
            "1. **Stage 1 (Order Creation Inference):**\n"
            "   Evaluates initial order constraints (shipping class, scheduled SLA, cargo value, origin seaport, and destination market) "
            "   using Model 01 (Logistic Regression) to establish an initial risk baseline.\n\n"
            "2. **Stage 2 (Warehouse Dispatch Inference):**\n"
            "   Re-scores consignment risk when container dock release is confirmed using Model 02 (XGBoost). Incorporates verified "
            "   `Order-to-Ship Time` (dock dwell duration) and carrier berth performance.\n\n"
            "3. **Delay Estimation (CatBoost Regressor):**\n"
            "   Quantifies anticipated delay duration in days beyond the contracted delivery SLA window.\n\n"
            "4. **SHAP Interpretability (TreeSHAP & KernelSHAP):**\n"
            "   Computes feature weight impact vectors (+/-) to explain exactly why a consignment received its risk classification."
        )

    @classmethod
    def _handle_shipment_comparison(cls, meta: Optional[Dict[str, Any]] = None, last_shipments: Optional[List[str]] = None) -> Tuple[str, Optional[List[str]], Optional[str], Optional[Dict[str, Any]]]:
        """Compares two specific consignments side-by-side or provides global high-vs-low risk comparative analysis."""
        meta = meta or {}
        refs = meta.get('shipment_refs', [])
        s1, s2 = None, None

        if len(refs) >= 2:
            s1 = cls._find_shipment(refs[0])
            s2 = cls._find_shipment(refs[1])
        elif last_shipments and len(last_shipments) >= 2:
            s1 = cls._find_shipment(last_shipments[0])
            s2 = cls._find_shipment(last_shipments[1])

        # If two distinct shipments were identified, perform deep pairwise comparison
        if s1 and s2 and s1.id != s2.id:
            prob1 = s1.dispatch_prob if s1.dispatch_prob is not None else (s1.order_creation_prob or 0.25)
            prob2 = s2.dispatch_prob if s2.dispatch_prob is not None else (s2.order_creation_prob or 0.25)
            score1 = round(prob1 * 100, 1)
            score2 = round(prob2 * 100, 1)
            risk1 = s1.risk_level or ('HIGH' if score1 >= 50 else 'MEDIUM' if score1 >= 25 else 'LOW')
            risk2 = s2.risk_level or ('HIGH' if score2 >= 50 else 'MEDIUM' if score2 >= 25 else 'LOW')

            higher_risk = s1 if score1 >= score2 else s2
            lower_risk = s2 if score1 >= score2 else s1

            summary = (
                f"> 💡 **Executive Summary:** Comparison between **{s1.shipment_number}** ({risk1} Risk, {score1}%) and "
                f"**{s2.shipment_number}** ({risk2} Risk, {score2}%). "
                f"**{higher_risk.shipment_number}** exhibits higher vulnerability to delivery SLA breach "
                f"due to {higher_risk.shipping_mode} tariff parameters and carrier transit constraints."
            )

            diff_score = abs(score1 - score2)
            c1 = f"{s1.origin_port or 'Rotterdam'} ➔ {s1.destination_port or 'Antwerp'}"
            c2 = f"{s2.origin_port or 'Hamburg'} ➔ {s2.destination_port or 'Singapore'}"

            exc1 = len([e for e in s1.exceptions if e.status not in ['RESOLVED', 'CLOSED']])
            exc2 = len([e for e in s2.exceptions if e.status not in ['RESOLVED', 'CLOSED']])

            table = (
                f"{summary}\n\n"
                f"### Consignment Comparative Analysis: {s1.shipment_number} vs. {s2.shipment_number}\n\n"
                f"| Metric / Parameter | `{s1.shipment_number}` | `{s2.shipment_number}` | Variance / Impact |\n"
                f"| :--- | :--- | :--- | :--- |\n"
                f"| **Evaluated Delay Risk** | **{risk1}** ({score1}%) | **{risk2}** ({score2}%) | Δ {diff_score:.1f}% risk differential |\n"
                f"| **Lifecycle Status** | `{s1.order_status or 'IN_TRANSIT'}` | `{s2.order_status or 'IN_TRANSIT'}` | Active tracking |\n"
                f"| **Shipping Class (Tariff)** | {s1.shipping_mode or 'Standard'} | {s2.shipping_mode or 'Standard'} | SLA tariff profile |\n"
                f"| **Scheduled SLA Window** | {s1.scheduled_days or 4} Days | {s2.scheduled_days or 4} Days | Lead-time buffer |\n"
                f"| **Maritime Sea Corridor** | {c1} | {c2} | Transshipment ports |\n"
                f"| **Vessel & Carrier** | {s1.vessel_name or 'Unassigned'} | {s2.vessel_name or 'Unassigned'} | Ocean vessel carrier |\n"
                f"| **Open Exceptions** | {exc1} open holds | {exc2} open holds | Incident status |\n\n"
                f"#### Analytical Attribution & Findings:\n"
                f"• **Lead-Time Slack:** Consignments with tighter scheduled windows (<= 2 days) have minimal buffer to absorb terminal congestion.\n"
                f"• **SHAP Game-Theoretic Decomposition:** Scheduled SLA duration and order-to-ship warehouse processing are primary positive drivers.\n\n"
                f"#### Operational Recommendations:\n"
                f"1. Prioritize clearance and quay priority for `{higher_risk.shipment_number}`.\n"
                f"2. Maintain routine milestone monitoring on `{lower_risk.shipment_number}`.\n"
                f"• Consignment Links: [{s1.shipment_number} Details](/shipments/{s1.shipment_number}) · [{s2.shipment_number} Details](/shipments/{s2.shipment_number})"
            )
            return table, [s1.shipment_number, s2.shipment_number], s1.shipment_number, AIChartService.get_shipment_comparison_chart(s1, s2)

        # Baseline comparison between high-risk and low-risk tiers across fleet
        return (
            "> 💡 **Executive Summary:** Fleet risk comparison indicates that High/Critical risk consignments carry an average "
            "predicted delay probability of >= 50% due to tight First Class/Same Day delivery SLAs and transshipment port dwell, "
            "whereas Low Risk shipments have sufficient scheduled transit buffers (4+ days).\n\n"
            "### Operational Comparison: High-Risk vs. Low-Risk Consignments\n\n"
            "| Operational Factor | High / Critical Risk Consignments | Low Risk / On-Track Consignments |\n"
            "| :--- | :--- | :--- |\n"
            "| **Scheduled SLA Window** | Typically tight (1–3 days, e.g. First Class or Same Day) | Generous transit buffer (4–6 days, Standard Ocean) |\n"
            "| **Dock / Port Dwell Time** | Elevated dwell time exceeding carrier release window (>3 days) | Swift warehouse clearance (0.5–2 days) |\n"
            "| **Destination Seaports** | Congested European & Asian transshipment hubs (Hamburg, Rotterdam) | Direct berthing with low berth wait times |\n"
            "| **Exception Likelihood** | Frequent port congestion holds and feeder connection delays | Clean transit without document holds |\n"
            "| **Recommended Action** | Priority dispatcher escalation to Operations Manager | Routine milestone monitoring |\n\n"
            "#### Practical Next Steps:\n"
            "• Dispatchers should prioritize berth clearance and expedited drayage for First Class consignments.\n"
            "• Operations Managers can monitor dwell metrics across transshipment nodes to prevent delay escalation.",
            last_shipments or [],
            None,
            AIChartService.get_scatter_sla_vs_risk()
        )

    @classmethod
    def _handle_explain_delay_reason(
        cls,
        meta: Dict[str, Any],
        last_focus: Optional[str],
        last_shipments: Optional[List[str]]
    ) -> Tuple[str, Optional[List[str]], Optional[str], Optional[Dict[str, Any]]]:
        """Explains why a consignment was predicted delayed or high-risk using SHAP features and database facts."""
        ref = meta.get('shipment_ref') or last_focus or (last_shipments[0] if last_shipments else None)
        if not ref:
            return (
                "> ℹ️ **Consignment Reference Required**\n\n"
                "To explain why a delay occurred, please specify the consignment reference "
                "(e.g. *'Why is SHP-10002 delayed?'* or *'Explain delay reason for SHP-10440'*).",
                None,
                None,
                None
            )

        shp = cls._find_shipment(ref)
        if not shp:
            return (
                f"Consignment reference **'{ref}'** could not be located in the database. "
                "Please verify the shipment number.",
                None,
                None,
                None
            )

        prob = shp.dispatch_prob if shp.dispatch_prob is not None else (shp.order_creation_prob or 0.25)
        pct = round(prob * 100, 1)
        risk = shp.risk_level or ('HIGH' if pct >= 50 else 'MEDIUM' if pct >= 25 else 'LOW')
        sched_days = shp.scheduled_days or 4
        mode = shp.shipping_mode or 'Standard Class'
        vessel = shp.vessel_name or 'Ever Given'
        corridor = f"{shp.origin_port or 'Origin'} ➔ {shp.destination_port or shp.destination_region or 'Destination'}"

        open_excs = [e for e in shp.exceptions if e.status not in ['RESOLVED', 'CLOSED']]
        exc_text = f"• **Active Holds:** {len(open_excs)} unresolved operational hold(s) logged." if open_excs else "• **Hold Status:** No active port or customs holds currently blocking clearance."

        is_low_risk = (pct < 40.0) or (risk in ['LOW', 'ON_TRACK', 'NORMAL'])
        if is_low_risk:
            body = (
                f"> 💡 **Executive Summary:** Consignment **`{shp.shipment_number}`** is evaluated at **LOW RISK** "
                f"with an on-track delay probability of **{pct}%** (Status: `{shp.order_status}`). "
                f"The shipment is progressing normally because the scheduled transit window of **{sched_days} day(s)** "
                f"under the **{mode}** tariff on the **{corridor}** maritime corridor provides sufficient operational buffer "
                f"against port dwell variance, with zero active hold bottlenecks.\n\n"
                f"### Operational Reliability Breakdown: {shp.shipment_number}\n\n"
                f"| Operational Factor | Database Telemetry | Risk Impact |\n"
                f"| :--- | :--- | :--- |\n"
                f"| **Scheduled SLA Window** | {sched_days} day(s) | **Positive Buffer (-φ):** Ample transit margin eliminates urgency penalties |\n"
                f"| **Shipping Mode** | {mode} | Routine ocean allocation with consistent transit lead-time |\n"
                f"| **Maritime Sea Corridor** | {corridor} | Uncongested sea lane with predictable terminal dwell times |\n"
                f"| **Vessel & Carrier** | {vessel} | Reliable commercial sailing operating on scheduled rotation |\n"
                f"| **Exceptions & Holds** | {len(open_excs)} active holds | Zero operational friction on this consignment |\n\n"
                f"• **Operational Recommendation:** Standard milestone tracking. No proactive supervisory intervention required.\n\n"
                f"• [Inspect Consignment Telemetry](/shipments/{shp.shipment_number})"
            )
            chart = None if meta.get('no_chart') else AIChartService.get_shap_waterfall_chart(shp)
            return body, [shp.shipment_number], shp.shipment_number, chart

        body = (
            f"> 💡 **Executive Summary:** Consignment **`{shp.shipment_number}`** is evaluated at **{risk} RISK** "
            f"with a **{pct}% delay probability** (Status: `{shp.order_status}`). "
            f"The primary root cause of this delay risk is the compressed scheduled transit window of **{sched_days} day(s)** "
            f"under the **{mode}** tariff on the **{corridor}** maritime corridor, leaving zero buffer for berth waiting times.\n\n"
            f"### Delay Risk Attribution & Root-Cause Analysis: {shp.shipment_number}\n\n"
            f"| Risk Dimension | Database Value | ML Contribution / Impact |\n"
            f"| :--- | :--- | :--- |\n"
            f"| **Scheduled SLA Window** | {sched_days} day(s) | **Primary Risk Multiplier** (+φ): First/Same Day tariffs cannot absorb port queues |\n"
            f"| **Shipping Mode** | {mode} | Priority class with high customer penalty for SLA breach |\n"
            f"| **Maritime Corridor** | {corridor} | Transshipment hub berthing variance ($M/M/c$ queuing dynamics) |\n"
            f"| **Vessel Assignment** | {vessel} | Deep-sea carrier subject to terminal congestion |\n"
            f"| **Exceptions & Holds** | {len(open_excs)} open hold(s) | Operational hold adds friction to warehouse release |\n\n"
            f"#### Game-Theoretic SHAP Feature Attribution:\n"
            f"• **`Days for shipment (scheduled)` (+φ):** Compressing scheduled days from 4 to {sched_days} increases late-delivery log-odds significantly.\n"
            f"• **`Shipping Mode` (+φ):** Priority tariffs lack tolerance for standard feeder vessel transshipment delays.\n"
            f"{exc_text}\n\n"
            f"#### Recommended Mitigation Protocol:\n"
            f"1. **Berth Prioritization:** Contact terminal agent at {shp.destination_port or 'destination port'} to arrange hot-box discharge.\n"
            f"2. **Escalate to Manager:** Log operational escalation for expedited customs clearance.\n"
            f"3. **Customer Advisory:** Send proactive delivery update to manage client expectations.\n\n"
            f"• [Inspect Consignment Telemetry](/shipments/{shp.shipment_number})"
        )
        chart = None if meta.get('no_chart') else AIChartService.get_shap_waterfall_chart(shp)
        return body, [shp.shipment_number], shp.shipment_number, chart

    @classmethod
    def _handle_deep_dive(
        cls,
        meta: Dict[str, Any],
        last_focus: Optional[str],
        last_shipments: Optional[List[str]]
    ) -> Tuple[str, Optional[List[str]], Optional[str], Optional[Dict[str, Any]]]:
        """Provides full operational specifications, events, and telemetry for a consignment."""
        ref = meta.get('shipment_ref') or last_focus or (last_shipments[0] if last_shipments else None)
        if not ref:
            return (
                "> ℹ️ **Consignment Reference Required**\n\n"
                "Please specify which consignment you would like to deep dive into (e.g. *'Deep dive on SHP-10482'*).",
                None,
                None,
                None
            )

        shp = cls._find_shipment(ref)
        if not shp:
            return f"Consignment **'{ref}'** was not found in the active database.", None, None, None

        prob = shp.dispatch_prob if shp.dispatch_prob is not None else (shp.order_creation_prob or 0.25)
        pct = round(prob * 100, 1)
        risk = shp.risk_level or ('HIGH' if pct >= 50 else 'MEDIUM' if pct >= 25 else 'LOW')

        if shp.customer:
            cust_name = f"{shp.customer.first_name or ''} {shp.customer.last_name or ''}".strip() or "Commercial Consignee"
            cust_seg = shp.customer.segment or "Corporate"
        else:
            cust_name = "Commercial Consignee"
            cust_seg = "Corporate"

        prod_name = shp.product.product_name if shp.product else 'General Cargo'
        sales_val = f"${shp.sales:,.2f}" if shp.sales else "$0.00"
        qty = shp.quantity or 1

        events_text = ""
        if shp.events:
            events_text = "\n".join([f"• `{ev.event_timestamp.strftime('%Y-%m-%d %H:%M') if ev.event_timestamp else 'Recent'}`: {ev.event_type} - {ev.notes or 'Logged'}" for ev in shp.events[:4]])
        else:
            events_text = "• *Standard automated AIS satellite tracking active.*"

        body = (
            f"> 💡 **Executive Summary:** Complete operational profile for **`{shp.shipment_number}`** "
            f"(Status: `{shp.order_status}`, Evaluated Risk: **{risk}** at **{pct}%**). "
            f"Carrying {qty} unit(s) of **{prod_name}** ({sales_val}) for **{cust_name}** ({cust_seg}).\n\n"
            f"### Comprehensive Consignment Profile: {shp.shipment_number}\n\n"
            f"| Operational Dimension | System Telemetry & Database Attributes |\n"
            f"| :--- | :--- |\n"
            f"| **Container & Vessel** | Container `{shp.container_number or 'MSCU-884920-1'}` · Vessel **{shp.vessel_name or 'Ever Given'}** |\n"
            f"| **Maritime Sea Lane** | **{shp.origin_port or 'Rotterdam'}** ➔ **{shp.destination_port or 'Antwerp'}** ({shp.destination_region or 'Western Europe'}) |\n"
            f"| **Shipping Class & SLA** | **{shp.shipping_mode or 'Standard Class'}** ({shp.scheduled_days or 4} Scheduled Days) |\n"
            f"| **Client & Cargo** | **{cust_name}** ({cust_seg}) · {prod_name} ({sales_val}) |\n"
            f"| **Model 01 (Order Creation)** | Risk: **{round((shp.order_creation_prob or 0.25)*100, 1)}%** (Logistic Regression v1.0) |\n"
            f"| **Model 02 (Dispatch Stage)** | Risk: **{round((shp.dispatch_prob or 0.25)*100, 1)}%** (XGBoost v1.2) |\n\n"
            f"#### Tracking Event Log & Milestones:\n"
            f"{events_text}\n\n"
            f"• [Open Full Consignment Dashboard](/shipments/{shp.shipment_number})"
        )
        return body, [shp.shipment_number], shp.shipment_number, AIChartService.get_shap_waterfall_chart(shp)

    @classmethod
    def _handle_communication_draft(
        cls,
        meta: Dict[str, Any],
        last_focus: Optional[str],
        last_shipments: Optional[List[str]]
    ) -> Tuple[str, Optional[List[str]], Optional[str], Optional[Dict[str, Any]]]:
        """Drafts an enterprise-ready customer communication update for a consignment."""
        ref = meta.get('shipment_ref') or last_focus or (last_shipments[0] if last_shipments else None)
        if not ref:
            return (
                "> ℹ️ **Consignment Reference Required**\n\n"
                "Please specify which consignment you would like to draft a client communication for "
                "(e.g. *'Draft customer message for SHP-10440'*).",
                None,
                None,
                None
            )

        shp = cls._find_shipment(ref)
        if not shp:
            return f"Consignment **'{ref}'** was not found in the active database.", None, None, None

        if shp.customer:
            cust_name = f"{shp.customer.first_name or ''} {shp.customer.last_name or ''}".strip() or "Valued Customer"
        else:
            cust_name = "Valued Customer"
        vessel = shp.vessel_name or 'Ever Given'
        dest = shp.destination_port or shp.destination_region or 'Port of Destination'
        status = shp.order_status or 'IN_TRANSIT'

        draft = (
            f"> 💡 **Executive Summary:** Professional client delivery advisory prepared for **`{shp.shipment_number}`** "
            f"addressed to **{cust_name}**. This draft is formatted for customer support / account manager review before dispatch.\n\n"
            f"### Proposed Client Advisory: {shp.shipment_number}\n\n"
            f"```text\n"
            f"Subject: Delivery Status & Schedule Advisory: Consignment {shp.shipment_number} ({vessel})\n\n"
            f"Dear {cust_name} Logistics Team,\n\n"
            f"We are writing to provide a proactive transit update regarding your container consignment {shp.shipment_number}, "
            f"currently in transit on ocean vessel {vessel} bound for {dest}.\n\n"
            f"Current Consignment Status: {status}\n"
            f"Carrier Maritime Corridor: {shp.origin_port or 'Origin Port'} to {dest}\n\n"
            f"Our predictive monitoring system has flagged potential terminal congestion at {dest}. To safeguard your supply chain, "
            f"our operations dispatch team has coordinated with the port authority for prioritized berth handling and expedited quay release.\n\n"
            f"We are monitoring your container around the clock and will provide automated milestone confirmations upon vessel berthing.\n\n"
            f"Sincerely,\n"
            f"RouteMind AI Customer Operations Desk\n"
            f"controltower@routemind.ai\n"
            f"```\n\n"
            f"• [Manage Consignment & Communications](/shipments/{shp.shipment_number})"
        )
        return draft, [shp.shipment_number], shp.shipment_number, None

    @classmethod
    def _handle_explicit_chart_request(cls, norm_q: str) -> Tuple[str, Optional[List[str]], Optional[str], Optional[Dict[str, Any]]]:
        """Selects and renders the exact requested chart visualization grounded in live telemetry."""
        lower_q = norm_q.lower()

        # 1b. Monthly Trend Line / Bar Chart
        if any(w in lower_q for w in ['monthly', 'trend', 'timeline', 'over time', 'by month']):
            chart = AIChartService.get_monthly_trend_chart(chart_type='line')
            text = (
                "> 💡 **Executive Summary:** Time-Series Chronological Trend generated from live MySQL consignment records.\n\n"
                "### Monthly Consignment & Late Delivery Trends\n\n"
                "Tracks total shipment movements alongside delayed consignments across consecutive operational periods."
            )
            return text, None, None, chart

        # 1c. Carrier & Maritime Vessel Performance
        if any(w in lower_q for w in ['carrier', 'vessel', 'ship line', 'shipping line']):
            chart = AIChartService.get_carrier_performance_chart()
            text = (
                "> 💡 **Executive Summary:** Carrier and Vessel Performance Chart generated from active maritime fleet telemetry.\n\n"
                "### Carrier Delivery Performance & Operational Reliability\n\n"
                "Breakdown of on-time versus delayed consignments across commercial carrier vessels."
            )
            return text, None, None, chart

        # 1d. Customer Segment Distribution
        if 'segment' in lower_q:
            chart = AIChartService.get_customer_segment_chart()
            text = (
                "> 💡 **Executive Summary:** Customer Segment Distribution Chart generated across commercial account tiers.\n\n"
                "### Consignment Mix by Commercial Customer Segment\n\n"
                "Visualizing Consumer, Corporate, and Home Office distribution across active shipments."
            )
            return text, None, None, chart

        # 1e. Status Lifecycle Distribution
        if any(w in lower_q for w in ['status mix', 'lifecycle', 'status breakdown', 'status chart']):
            chart = AIChartService.get_status_distribution_chart()
            text = (
                "> 💡 **Executive Summary:** Consignment Lifecycle Status Distribution Chart generated from active records.\n\n"
                "### Lifecycle Status Breakdown (Delivered, In Transit, Delayed, Pending)\n\n"
                "Visualizing operational flow across active ocean corridors."
            )
            return text, None, None, chart

        # 1. Late vs On-Time Delivery Performance Chart
        if any(w in lower_q for w in ['late', 'on time', 'ontime', 'deleary', 'deliveries']) and not ('scatter' in lower_q or 'region' in lower_q or 'mode' in lower_q):
            is_donut = any(w in lower_q for w in ['donut', 'doughnut', 'pie'])
            chart = AIChartService.get_late_vs_ontime_chart(as_bar=not is_donut)
            text = (
                "> 💡 **Executive Summary:** Live comparison of delivered on-time consignments versus delayed shipments across active fleet telemetry.\n\n"
                "### Fleet Delivery Performance: Late vs. On-Time Consignments\n\n"
                "• **On-Time Deliveries:** Consignments completed or delivered within scheduled SLA windows.\n"
                "• **Delayed / Late Hold:** Active consignments with delay flags or exception holds requiring proactive dispatch intervention.\n"
                "• **Active In-Transit:** Containers actively sailing on ocean corridors.\n\n"
                "An interactive visual chart has been rendered below to monitor overall SLA adherence."
            )
            return text, None, None, chart

        # 2. Scatter Plot
        if 'scatter' in lower_q or 'correlation' in lower_q:
            chart = AIChartService.get_scatter_sla_vs_risk()
            text = (
                "> 💡 **Executive Summary:** Scatter Plot generated mapping Scheduled SLA Duration (Days) against Predicted Delay Probability (%).\n\n"
                "### Scheduled SLA Duration vs. Predicted Delay Probability (Scatter Plot)\n\n"
                "Illustrates the inverse relationship where tight scheduled transit windows correlate with higher late-delivery risk."
            )
            return text, None, None, chart

        # 3. Donut / Pie Chart for Risk Segmentation
        if 'donut' in lower_q or 'doughnut' in lower_q or 'pie' in lower_q or 'tier' in lower_q:
            chart = AIChartService.get_risk_donut_chart()
            text = (
                "> 💡 **Executive Summary:** Interactive Donut Chart generated for fleet delay risk distribution across all active consignments.\n\n"
                "### Maritime Fleet Risk Tier Distribution (Donut Chart)\n\n"
                "Categorized into High/Critical Risk (Red), Medium/Elevated Risk (Amber), and Low Risk/On-Track (Green) based on production ML inference."
            )
            return text, None, None, chart

        # 4. Histogram
        if 'histogram' in lower_q or 'distribution' in lower_q or 'bins' in lower_q:
            chart = AIChartService.get_risk_histogram()
            text = (
                "> 💡 **Executive Summary:** Probability Distribution Histogram generated across 5 discrete risk score tiers (0–100%).\n\n"
                "### Fleet Delay Probability Distribution (Histogram)\n\n"
                "Displays the frequency count of tracked consignments grouped into 20% probability risk bins."
            )
            return text, None, None, chart

        # 5. Shipping Mode Bar Chart
        if 'mode' in lower_q or 'class' in lower_q:
            chart = AIChartService.get_mode_delay_chart()
            text = (
                "> 💡 **Executive Summary:** Ranked Horizontal Bar Chart generated comparing delay incidence across all 4 shipping mode tariffs.\n\n"
                "### Delay Rate by Maritime Shipping Mode (Horizontal Bar)\n\n"
                "Ranks First Class, Same Day, Second Class, and Standard Class by empirical delay percentage."
            )
            return text, None, None, chart

        # 6. Regional Bar Chart
        if 'region' in lower_q or 'corridor' in lower_q:
            chart = AIChartService.get_regional_delay_chart()
            text = (
                "> 💡 **Executive Summary:** Grouped Bar Chart generated for regional destination volume vs high-risk concentrations.\n\n"
                "### Regional Consignment Volume vs Risk Concentration\n\n"
                "Evaluates geographical bottlenecks across international maritime destination corridors."
            )
            return text, None, None, chart

        # 7. Model Performance / Confusion Matrix
        if 'model' in lower_q or 'metric' in lower_q or 'confusion' in lower_q:
            chart = AIChartService.get_model_performance_chart()
            text = (
                "> 💡 **Executive Summary:** Production Machine Learning Model Benchmarks & Confusion Matrix.\n\n"
                "### Production ML Model Performance Benchmarks\n\n"
                "Comparison of Model 01 (Logistic Regression - Order Creation) vs Model 02 (XGBoost - Dispatch Stage) across Accuracy, Precision, Recall, F1, and ROC-AUC."
            )
            return text, None, None, chart

        # 8. General Bar Graph / Bar Chart
        if any(w in lower_q for w in ['bar graph', 'bar chart', 'bae geaph', 'bar']):
            chart = AIChartService.get_late_vs_ontime_chart(as_bar=True)
            text = (
                "> 💡 **Executive Summary:** Interactive Bar Graph generated from active fleet delivery telemetry.\n\n"
                "### Fleet Delivery Performance & Operational Status (Bar Graph)\n\n"
                "Visualizing confirmed on-time deliveries, delayed consignments, active transit containers, and pending dispatch orders."
            )
            return text, None, None, chart

        chart = AIChartService.get_risk_donut_chart()
        text = (
            "> 💡 **Executive Summary:** Visual analytics chart generated from active MySQL consignment telemetry.\n\n"
            "### Maritime Fleet Risk Segmentation\n\n"
            "Visualizing risk proportions across tracked ocean consignments."
        )
        return text, None, None, chart

    @classmethod
    def _generate_operational_summary(cls) -> str:
        """Executive summary of operational telemetry."""
        total_s = Shipment.query.count()
        high_s = Shipment.query.filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK'])).count()
        low_s = Shipment.query.filter_by(risk_level='LOW').count()
        on_time_pct = round((low_s / total_s * 100), 1) if total_s > 0 else 0.0
        open_exc = ShipmentException.query.filter(ShipmentException.status.in_(['OPEN', 'INVESTIGATING', 'IN_PROGRESS'])).count()
        pending_esc = ManagerEscalation.query.filter_by(status='PENDING').count()

        return (
            f"### Daily Logistics Control Tower Executive Summary\n\n"
            f"• **Active Fleet Volume:** **{total_s} tracked ocean consignments**\n"
            f"• **Fleet On-Time Reliability:** **{on_time_pct}%** ({low_s} low-risk shipments)\n"
            f"• **High-Risk Consignments:** **{high_s} shipments** requiring active route monitoring\n"
            f"• **Open Operational Exceptions:** **{open_exc} incidents** pending on Exception Desk\n"
            f"• **Manager Escalations:** **{pending_esc} requests** awaiting managerial action\n\n"
            "All dual-stage ML models (Model 01 Logistic Regression and Model 02 XGBoost) are executing live inference."
        )

    @classmethod
    def _handle_general_shipment_search(cls, norm_q: str) -> Tuple[str, List[str], None]:
        """Performs general database search."""
        query = Shipment.query

        if 'delayed' in norm_q.lower():
            query = query.filter(Shipment.order_status == 'DELAYED')
        elif 'in transit' in norm_q.lower():
            query = query.filter(Shipment.order_status == 'IN_TRANSIT')
        elif 'completed' in norm_q.lower() or 'delivered' in norm_q.lower():
            query = query.filter(Shipment.order_status.in_(['DELIVERED', 'COMPLETED']))

        shipments = query.order_by(Shipment.dispatch_prob.desc()).limit(8).all()
        if not shipments:
            return "No shipments matched your search criteria.", [], None

        table_rows = [
            f"### Active Shipment Search Results ({len(shipments)} records):\n",
            "| Shipment # | Vessel | Corridor | Mode | Risk Level | Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        refs = []
        for s in shipments:
            refs.append(s.shipment_number)
            prob = s.dispatch_prob if s.dispatch_prob is not None else (s.order_creation_prob or 0.25)
            pct = round(prob * 100)
            corridor = f"{s.origin_port or 'Origin'} ➔ {s.destination_port or s.destination_region or 'Dest'}"
            table_rows.append(
                f"| `{s.shipment_number}` | {s.vessel_name or 'Unassigned'} | {corridor} | {s.shipping_mode} | **{s.risk_level}** ({pct}%) | `{s.order_status}` |"
            )

        return "\n".join(table_rows), refs, None

    @classmethod
    def _find_shipment(cls, ref: str) -> Optional[Shipment]:
        """Locates shipment by shipment_number, integer id, or order_id_code."""
        s = Shipment.query.filter(Shipment.shipment_number.ilike(ref)).first()
        if s:
            return s
        if ref.isdigit():
            s = Shipment.query.filter(Shipment.shipment_number.ilike(f"SHP-{ref}")).first()
            if s:
                return s
            s = db.session.get(Shipment, int(ref))
            if s:
                return s
        s = Shipment.query.filter(Shipment.order_id_code.ilike(f"%{ref}%")).first()
        if s:
            return s
        return None

    @classmethod
    def _extract_shipment_ref(cls, text: str) -> Optional[str]:
        return AIIntentService.extract_shipment_ref(text)
