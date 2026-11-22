"""
ai_intent_service.py - Natural Language Normalization & Intent Classification
Author: RouteMind AI Engineering
Provides typo tolerance, contextual resolution, and deterministic intent classification
across 20 core operational logistics intents.
"""
import re
from typing import Dict, Any, Optional, Tuple, List


class Intent:
    GREETING = "GREETING"
    GENERAL_HELP = "GENERAL_HELP"
    INDIVIDUAL_SHIPMENT_DETAILS = "INDIVIDUAL_SHIPMENT_DETAILS"
    SHIPMENT_SEARCH = "SHIPMENT_SEARCH"
    SHIPMENT_STATUS = "SHIPMENT_STATUS"
    RISK_SEGMENTATION = "RISK_SEGMENTATION"
    HIGH_RISK_LISTING = "HIGH_RISK_LISTING"
    MEDIUM_RISK_LISTING = "MEDIUM_RISK_LISTING"
    LOW_RISK_LISTING = "LOW_RISK_LISTING"
    LATE_DELIVERY_ANALYSIS = "LATE_DELIVERY_ANALYSIS"
    PERCENTAGE_QUERY = "PERCENTAGE_QUERY"
    DATABASE_ANALYTICAL_QUERY = "DATABASE_ANALYTICAL_QUERY"
    SHIPPING_MODE_ANALYSIS = "SHIPPING_MODE_ANALYSIS"
    REGIONAL_ANALYSIS = "REGIONAL_ANALYSIS"
    CUSTOMER_QUERY = "CUSTOMER_QUERY"
    EXCEPTION_ANALYSIS = "EXCEPTION_ANALYSIS"
    MANAGER_ESCALATION_ANALYSIS = "MANAGER_ESCALATION_ANALYSIS"
    ML_MODEL_INFO = "ML_MODEL_INFO"
    MODEL_PERFORMANCE_METRICS = "MODEL_PERFORMANCE_METRICS"
    SHIPMENT_COMPARISON = "SHIPMENT_COMPARISON"
    EXPLAIN_DELAY_REASON = "EXPLAIN_DELAY_REASON"
    DEEP_DIVE = "DEEP_DIVE"
    CHART_REQUEST = "CHART_REQUEST"
    CHART_MODIFICATION = "CHART_MODIFICATION"
    MONTHLY_TREND = "MONTHLY_TREND"
    CARRIER_ANALYSIS = "CARRIER_ANALYSIS"
    CUSTOMER_SEGMENT_ANALYSIS = "CUSTOMER_SEGMENT_ANALYSIS"
    STATUS_DISTRIBUTION = "STATUS_DISTRIBUTION"
    FOLLOWUP_ANALYTICAL_QUERY = "FOLLOWUP_ANALYTICAL_QUERY"
    DATA_EXPORT_REQUEST = "DATA_EXPORT_REQUEST"
    COMMUNICATION_DRAFT = "COMMUNICATION_DRAFT"
    OPERATIONAL_SUMMARY = "OPERATIONAL_SUMMARY"
    FOLLOWUP_CONTEXT = "FOLLOWUP_CONTEXT"
    FOLLOWUP_SPECIFIC_ITEM = "FOLLOWUP_SPECIFIC_ITEM"
    FOLLOWUP_NEXT_ACTION = "FOLLOWUP_NEXT_ACTION"
    UNKNOWN = "UNKNOWN"


TYPO_MAP = {
    r'\bsegements\b': 'segments',
    r'\bsegement\b': 'segment',
    r'\bsegmentz\b': 'segments',
    r'\bsegmnts\b': 'segments',
    r'\bsegmnt\b': 'segment',
    r'\bhigest\b': 'highest',
    r'\bhighes\b': 'highest',
    r'\bheighest\b': 'highest',
    r'\bhieghest\b': 'highest',
    r'\bgivet\b': 'give',
    r'\bcurrections?\b': 'corrections',
    r'\bckeck\b': 'check',
    r'\bshipements?\b': 'shipments',
    r'\bshipmnts?\b': 'shipments',
    r'\bshpmnts?\b': 'shipments',
    r'\bshpmnt\b': 'shipment',
    r'\bwhcih\b': 'which',
    r'\bwich\b': 'which',
    r'\bexcepions?\b': 'exceptions',
    r'\bexcepsions?\b': 'exceptions',
    r'\bexcaptions?\b': 'exceptions',
    r'\bexcaption\b': 'exception',
    r'\bdelayd\b': 'delayed',
    r'\bdlayed\b': 'delayed',
    r'\bdealyed\b': 'delayed',
    r'\bdalay(ed)?\b': 'delayed',
    r'\bmanger\b': 'manager',
    r'\bmanagr\b': 'manager',
    r'\besclat(e|ion|ed)?\b': 'escalation',
    r'\bcatgory\b': 'category',
    r'\bcategoreis\b': 'categories',
    r'\bdistribtion\b': 'distribution',
    r'\bdistrubution\b': 'distribution',
    r'\baccurcy\b': 'accuracy',
    r'\bacuracy\b': 'accuracy',
    r'\bprecent(age)?\b': 'percentage',
    r'\bstatuss?\b': 'status',
    r'\bstaus\b': 'status',
    r'\bcrtical\b': 'critical',
    r'\bfirst\s+shipment\b': 'first shipment',
    r'\bsecond\s+shipment\b': 'second shipment',
    r'\bdeleary\b': 'delivery',
    r'\bdelivary\b': 'delivery',
    r'\bdelary\b': 'delivery',
    r'\bbae\s+geaph\b': 'bar graph',
    r'\bgeaph\b': 'graph',
    r'\bgrph\b': 'graph',
    r'\bgraf\b': 'graph',
    r'\bchrt\b': 'chart',
    r'\bchrat\b': 'chart',
    r'\bcarht\b': 'chart',
    r'\bdetales\b': 'details',
    r'\bdetials\b': 'details',
    r'\bsuchivasion\b': 'situation',
    r'\bteh\b': 'the',
}


def normalize_text(text: str) -> str:
    """Normalizes spelling mistakes, contractions, and extra whitespace."""
    if not text:
        return ""
    clean = text.strip()
    # Normalize hyphens in common compounds
    clean = re.sub(r'\bhigh-risk\b', 'high risk', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bmedium-risk\b', 'medium risk', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\blow-risk\b', 'low risk', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bon-time\b', 'on time', clean, flags=re.IGNORECASE)
    # Normalize common typos case-insensitively

    for pattern, replacement in TYPO_MAP.items():
        clean = re.sub(pattern, replacement, clean, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', clean).strip()


class AIIntentService:

    @classmethod
    def detect_intent(cls, query: str, context_shipments: Optional[List[str]] = None, last_intent: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Classifies user query into one of the 20 canonical logistics operational intents.
        Returns (intent_name, intent_metadata).
        """
        norm_q = normalize_text(query)
        lower_q = norm_q.lower()
        meta: Dict[str, Any] = {'normalized_query': norm_q}

        # Check explicit negative chart preference
        neg_chart_signals = [
            'without graph', 'without the graph', 'without chart', 'without the chart',
            'without graphs', 'without charts', 'with out graph', 'with out the graph', 'with out the graphs',
            'no graph', 'no chart', 'no graphs', 'no charts', 'do not need graph', 'do not need any graph',
            'dont need graph', 'dont need any graph', 'i do not need any graph', 'do not need the graph',
            'not need graph', 'no visual', 'without visual', 'no image', 'without image', 'just text',
            'just need the explanation', 'just explain', 'only text'
        ]
        if any(term in lower_q for term in neg_chart_signals):
            meta['no_chart'] = True

        # Check dynamic chart modification commands
        mod_match = re.search(r'\b(?:change|switch|convert|make|show)\s+(?:it|this|the\s+chart|the\s+graph)?\s*(?:in)?to\s+(?:a\s+)?(line|bar|horizontal\s+bar|hbar|column|pie|donut|doughnut|area)\s*(?:chart|graph|plot)?\b', lower_q)
        if not mod_match and any(phrase in lower_q for phrase in ['change it to line', 'change to line', 'make it a line chart', 'change it to a line chart', 'switch to line', 'show as line', 'change it to bar', 'change to bar', 'switch to bar', 'change to donut', 'switch to donut']):
            for t_opt in ['line', 'bar', 'horizontal bar', 'donut', 'pie', 'area']:
                if t_opt in lower_q:
                    meta['target_chart_type'] = 'horizontalBar' if t_opt == 'horizontal bar' else t_opt
                    return Intent.CHART_MODIFICATION, meta
        elif mod_match:
            raw_t = mod_match.group(1).strip()
            meta['target_chart_type'] = 'horizontalBar' if 'horizontal' in raw_t or raw_t == 'hbar' else raw_t
            return Intent.CHART_MODIFICATION, meta

        # Check analytical follow-up questions referencing previous charts/analyses
        if re.search(r'\b(?:show\s+only\s+(?:the\s+)?last|only\s+(?:the\s+)?last)\s+(\d+|two|three|four|3|2|4)\s+months\b', lower_q) or 'last 3 months' in lower_q or 'last three months' in lower_q:
            m = re.search(r'(\d+|two|three|four)', lower_q)
            w_map = {'two': 2, 'three': 3, 'four': 4, '2': 2, '3': 3, '4': 4}
            meta['filter_months'] = w_map.get(m.group(1), 3) if m else 3
            return Intent.FOLLOWUP_ANALYTICAL_QUERY, meta

        if any(term in lower_q for term in ['which month has the highest', 'which month has highest', 'which month is highest', 'highest delay month', 'month with most delays', 'which month had the most', 'which month has the lowest']):
            meta['followup_type'] = 'highest_delay_month'
            return Intent.FOLLOWUP_ANALYTICAL_QUERY, meta

        # -------------------------------------------------------------
        # 1. GREETING Intent (Strictly isolated: only pure greetings)
        # -------------------------------------------------------------
        greeting_words = {'hi', 'hii', 'hiii', 'hello', 'hey', 'heyy', 'greetings', 'good morning', 'good afternoon', 'good evening', 'howdy', 'yo', 'hola'}
        tokens = [t.strip('!?,.') for t in lower_q.split()]
        if len(tokens) <= 3 and all(t in greeting_words or t in {'there', 'bot', 'copilot', 'assistant', 'team', 'routemind'} for t in tokens):
            return Intent.GREETING, meta

        # -------------------------------------------------------------
        # 2. Multi-Shipment & Comparison Extraction
        # -------------------------------------------------------------
        all_refs = cls.extract_all_shipment_refs(norm_q)
        if len(all_refs) >= 2 or ('compare' in lower_q and (len(all_refs) >= 1 or (context_shipments and len(context_shipments) >= 2))):
            meta['shipment_refs'] = all_refs if len(all_refs) >= 2 else (context_shipments[:2] if context_shipments and len(context_shipments) >= 2 else all_refs)
            return Intent.SHIPMENT_COMPARISON, meta

        # -------------------------------------------------------------
        # 2b. Extract explicit single shipment identifier
        # -------------------------------------------------------------
        shipment_ref = all_refs[0] if all_refs else cls.extract_shipment_ref(norm_q)
        if shipment_ref:
            meta['shipment_ref'] = shipment_ref
            if any(w in lower_q for w in ['why', 'reason', 'cause', 'what caused', 'factor']):
                return Intent.EXPLAIN_DELAY_REASON, meta
            if any(w in lower_q for w in ['more detail', 'deep dive', 'full breakdown', 'events', 'timeline']):
                return Intent.DEEP_DIVE, meta
            if any(w in lower_q for w in ['draft', 'customer message', 'email', 'communicate', 'notify customer']):
                return Intent.COMMUNICATION_DRAFT, meta
            if 'explain' in lower_q or 'detail' in lower_q or 'report' in lower_q:
                return Intent.INDIVIDUAL_SHIPMENT_DETAILS, meta
            if any(w in lower_q for w in ['status', 'where', 'delivered', 'arrived', 'location', 'reach']):
                return Intent.SHIPMENT_STATUS, meta
            return Intent.INDIVIDUAL_SHIPMENT_DETAILS, meta

        # -------------------------------------------------------------
        # 2c. Contextual Referrals without explicit ID: "why did this happen?", "why is this segment at low risk"
        # -------------------------------------------------------------
        is_why_risk = (
            any(w in lower_q for w in ['why', 'reason', 'what makes', 'how come', 'factor']) and
            any(r in lower_q for r in ['low risk', 'at low risk', 'is at low', 'low', 'high risk', 'delayed', 'late', 'medium risk', 'critical', 'on track', 'safe'])
        )
        if is_why_risk or any(w in lower_q for w in ['why did this happen', 'why is it late', 'why is this late', 'why is it delayed', 'what caused this', 'what caused the delay', 'why high risk', 'why this segment is at low risk', 'why this segment at low risk']):
            return Intent.EXPLAIN_DELAY_REASON, meta

        if any(w in lower_q for w in ['show more details', 'more details', 'deep dive', 'show full details']):
            return Intent.DEEP_DIVE, meta

        if any(w in lower_q for w in ['draft customer', 'draft message', 'customer email draft', 'communication draft']):
            return Intent.COMMUNICATION_DRAFT, meta


        # -------------------------------------------------------------
        # 3. Follow-up: Next Action / Recommended Action
        # (e.g. "what should the dispatcher do next?", "what next?", "recommended action")
        # -------------------------------------------------------------
        if any(w in lower_q for w in ['do next', 'what next', 'recommended action', 'next step', 'action required', 'should dispatcher do', 'what to do']):
            return Intent.FOLLOWUP_NEXT_ACTION, meta

        # -------------------------------------------------------------
        # 4. Follow-up: Specific item from previous list
        # (e.g. "explain the first shipment", "tell me about second one", "first shipment", "first one")
        # -------------------------------------------------------------
        first_match = re.search(r'\b(first|1st|second|2nd|third|3rd|fourth|4th|last)\s+(?:one|shipment|consignment|order|record)\b', lower_q)
        if (first_match or lower_q in ['first one', 'the first one', 'first', 'first shipment', '1st one']) and context_shipments:
            index_str = first_match.group(1).lower() if first_match else 'first'
            idx_map = {'first': 0, '1st': 0, 'second': 1, '2nd': 1, 'third': 2, '3rd': 2, 'fourth': 3, '4th': 3, 'last': -1}
            meta['item_index'] = idx_map.get(index_str, 0)
            return Intent.FOLLOWUP_SPECIFIC_ITEM, meta

        # -------------------------------------------------------------
        # 5. Follow-up: Contextual filtering on previous results
        # (e.g. "which of these have open exceptions?", "what about medium risk?", "show only high risk")
        # -------------------------------------------------------------
        context_signals = ['these', 'those', 'them', 'the shipments', 'of these', 'which of them', 'previous result', 'previous shipments']
        has_context_signal = any(sig in lower_q for sig in context_signals)

        if has_context_signal and context_shipments:
            if 'exception' in lower_q:
                return Intent.FOLLOWUP_CONTEXT, {'filter': 'exceptions', **meta}
            if 'escalat' in lower_q or 'manager' in lower_q:
                return Intent.FOLLOWUP_CONTEXT, {'filter': 'escalations', **meta}
            if 'risk' in lower_q or 'score' in lower_q or 'delay' in lower_q:
                return Intent.FOLLOWUP_CONTEXT, {'filter': 'risk_scores', **meta}
            return Intent.FOLLOWUP_CONTEXT, {'filter': 'general', **meta}

        # Context-dependent sub-filters when user says "show only high risk" after a segmentation query
        if ('show only' in lower_q or 'filter to' in lower_q or 'what about' in lower_q) and context_shipments:
            if 'high' in lower_q or 'critical' in lower_q:
                return Intent.HIGH_RISK_LISTING, meta
            if 'medium' in lower_q or 'moderate' in lower_q:
                return Intent.MEDIUM_RISK_LISTING, meta
            if 'low' in lower_q or 'on track' in lower_q:
                return Intent.LOW_RISK_LISTING, meta

        # -------------------------------------------------------------
        # 5b. Specific Single Risk Segment Requests (e.g. "give the highest risk segment", "show low risk segment")
        # -------------------------------------------------------------
        has_pct_signal = any(term in lower_q for term in ['percentage', 'percent', '%', 'proportion', 'share of', 'ratio', 'late vs', 'late versus']) or ('how many percent' in lower_q) or ('what percent' in lower_q)
        if not has_pct_signal and not any(w in lower_q for w in ['why', 'reason', 'how come', 'what makes']):
            if ('highest risk' in lower_q or 'high risk' in lower_q) and any(w in lower_q for w in ['segment', 'tier', 'category']):
                return Intent.HIGH_RISK_LISTING, meta
            if ('medium risk' in lower_q or 'moderate risk' in lower_q) and any(w in lower_q for w in ['segment', 'tier', 'category']):
                return Intent.MEDIUM_RISK_LISTING, meta
            if ('low risk' in lower_q or 'on track' in lower_q) and any(w in lower_q for w in ['segment', 'tier', 'category']):
                return Intent.LOW_RISK_LISTING, meta

        # -------------------------------------------------------------
        # 6. RISK SEGMENTATION Intent (Comprehensive Fleet Breakdown)
        # (e.g. "give all risk segments", "show risk categories", "risk distribution", "how are shipments divided by risk")
        # -------------------------------------------------------------
        is_risk_segment = (
            not has_pct_signal and
            not any(w in lower_q for w in ['why', 'reason', 'how come', 'what makes']) and
            (
                ('risk' in lower_q and any(w in lower_q for w in ['segments', 'categories', 'distribution', 'divided', 'breakdown', 'levels', 'situation', 'split'])) or
                ('all risk' in lower_q) or
                ('show low, medium and high' in lower_q) or
                ('risk summary' in lower_q) or
                ('how are shipments divided' in lower_q) or
                ('how many shipments are there in each risk' in lower_q)
            )
        )
        if is_risk_segment:
            return Intent.RISK_SEGMENTATION, meta

        # -------------------------------------------------------------
        # 7. Shipping Mode & Regional Concentrations (Check specific entity before risk tier listing)
        # -------------------------------------------------------------
        if ('mode' in lower_q or 'shipping class' in lower_q) and any(w in lower_q for w in ['highest', 'delay', 'rate', 'most', 'risk', 'analysis', 'breakdown', 'which']):
            return Intent.SHIPPING_MODE_ANALYSIS, meta

        if 'region' in lower_q and any(w in lower_q for w in ['most', 'highest', 'delay', 'risk', 'bottleneck', 'count', 'more delay', 'which']):
            return Intent.REGIONAL_ANALYSIS, meta

        # -------------------------------------------------------------
        # 8. Specific Risk Level Listings
        # -------------------------------------------------------------
        if not has_pct_signal:
            if 'high risk' in lower_q or 'critical risk' in lower_q or 'critical shipments' in lower_q or 'critical record' in lower_q or ('critical' in lower_q and any(w in lower_q for w in ['shipment', 'record', 'consignment', 'one', 'top'])):
                if any(w in lower_q for w in ['list', 'show', 'give', 'display', 'get', 'which', 'view', 'only', 'top']):
                    wants_top_one = bool(
                        re.search(r'\b(top\s+(?:one|1)|only\s+(?:the\s+)?top|single\s+highest|highest\s+risk\s+(?:one|record|shipment)|most\s+critical\s+(?:one|record|shipment))\b', lower_q) or
                        ('top record' in lower_q and 'only' in lower_q) or
                        ('top one' in lower_q) or
                        ('only the top' in lower_q) or
                        ('only top' in lower_q)
                    )
                    if wants_top_one:
                        meta['only_top'] = True
                        meta['limit'] = 1
                    return Intent.HIGH_RISK_LISTING, meta

            if 'medium risk' in lower_q or 'moderate risk' in lower_q:
                if any(w in lower_q for w in ['list', 'show', 'give', 'display', 'get', 'which', 'view', 'what about']):
                    return Intent.MEDIUM_RISK_LISTING, meta

            if 'low risk' in lower_q or 'on track' in lower_q or 'safe shipments' in lower_q:
                if any(w in lower_q for w in ['list', 'show', 'give', 'display', 'get', 'which', 'view', 'what about']):
                    return Intent.LOW_RISK_LISTING, meta

        # -------------------------------------------------------------
        # 9. Percentage & Ratio Queries (Late Risk & Arbitrary Attribute Percentages)
        # -------------------------------------------------------------
        if has_pct_signal:
            if any(w in lower_q for w in ['delay', 'late', 'on time', 'ontime', 'deleary', 'deliveries']) or ('high risk' in lower_q and not any(w in lower_q for w in ['deliver', 'transit', 'mode', 'class', 'region', 'europe', 'asia', 'customer'])):
                return Intent.LATE_DELIVERY_ANALYSIS, meta
            return Intent.PERCENTAGE_QUERY, meta

        # -------------------------------------------------------------
        # Database Analytical & Aggregation Queries (Average, Total, Counts)
        # -------------------------------------------------------------
        if any(term in lower_q for term in ['average', 'avg days', 'total sales', 'total revenue', 'total value', 'cargo value', 'order value', 'how much sales', 'list vessels', 'all vessels', 'show vessels']):
            return Intent.DATABASE_ANALYTICAL_QUERY, meta



        # -------------------------------------------------------------
        # 10. Manager Escalation Analysis
        # -------------------------------------------------------------
        if 'escalat' in lower_q or ('manager' in lower_q and any(w in lower_q for w in ['attention', 'review', 'pending', 'require', 'need'])):
            return Intent.MANAGER_ESCALATION_ANALYSIS, meta

        # -------------------------------------------------------------
        # 11. Exception Analysis
        # -------------------------------------------------------------
        if 'exception' in lower_q:
            return Intent.EXCEPTION_ANALYSIS, meta

        # -------------------------------------------------------------
        # 12. ML Model Architecture & Performance Metrics
        # -------------------------------------------------------------
        if any(term in lower_q for term in ['accuracy', 'roc auc', 'roc-auc', 'auc score', 'precision', 'model metrics']) or ('model' in lower_q and 'accuracy' in lower_q):
            return Intent.MODEL_PERFORMANCE_METRICS, meta

        if any(term in lower_q for term in ['model', 'logistic regression', 'xgboost', 'catboost', 'delay model', 'dual-stage', 'shap']):
            return Intent.ML_MODEL_INFO, meta

        # -------------------------------------------------------------
        # 13. Shipment Comparison
        # -------------------------------------------------------------
        if 'compare' in lower_q or ('difference' in lower_q and ('high' in lower_q or 'risk' in lower_q or 'predicted' in lower_q)):
            return Intent.SHIPMENT_COMPARISON, meta

        # -------------------------------------------------------------
        # 14b. Monthly and Chronological Trends
        # -------------------------------------------------------------
        if any(term in lower_q for term in ['monthly late deliveries', 'monthly late delivery', 'monthly shipments', 'monthly delay', 'monthly trends', 'monthly trend', 'month wise', 'by month', 'yearly trend', 'date wise trend', 'trend over time']):
            return Intent.MONTHLY_TREND, meta

        # -------------------------------------------------------------
        # 14c. Carrier and Vessel Performance
        # -------------------------------------------------------------
        if any(term in lower_q for term in ['carrier', 'vessel']) and any(w in lower_q for w in ['performance', 'delay', 'comparison', 'which', 'breakdown', 'rate', 'highest', 'most']):
            return Intent.CARRIER_ANALYSIS, meta

        # -------------------------------------------------------------
        # 14d. Customer Segment Distribution
        # -------------------------------------------------------------
        if 'segment' in lower_q:
            return Intent.CUSTOMER_SEGMENT_ANALYSIS, meta

        # -------------------------------------------------------------
        # 14e. Status & Lifecycle Distribution
        # -------------------------------------------------------------
        if any(w in lower_q for w in ['status distribution', 'status breakdown', 'delivery status mix', 'status mix', 'lifecycle status', 'proportion of delivered']):
            return Intent.STATUS_DISTRIBUTION, meta

        # -------------------------------------------------------------
        # 14f. Data Export Requests
        # -------------------------------------------------------------
        if any(w in lower_q for w in ['export data', 'download csv', 'export chart', 'export to csv', 'download table', 'export report']):
            return Intent.DATA_EXPORT_REQUEST, meta

        # -------------------------------------------------------------
        # 14. Customer-related Queries
        # -------------------------------------------------------------
        if 'customer' in lower_q or 'consignee' in lower_q:
            return Intent.CUSTOMER_QUERY, meta

        # -------------------------------------------------------------
        # 15. Operational Summary
        # -------------------------------------------------------------
        if any(term in lower_q for term in ['summary', 'overview', 'today', 'daily status', 'control tower status', 'all details', 'full details', 'entire status']):
            return Intent.OPERATIONAL_SUMMARY, meta

        # -------------------------------------------------------------
        # 15b. Explicit Dynamic Visualizations & Chart Requests
        # -------------------------------------------------------------
        chart_signals = ['chart', 'graph', 'plot', 'visualiz', 'histogram', 'diagram', 'donut', 'doughnut', 'pie', 'scatter']
        if not meta.get('no_chart') and any(term in lower_q for term in chart_signals):
            return Intent.CHART_REQUEST, meta

        # -------------------------------------------------------------
        # 16. General Help
        # -------------------------------------------------------------
        if any(term in lower_q for term in ['help', 'what can you do', 'how to use', 'commands', 'capabilities']):
            return Intent.GENERAL_HELP, meta

        # -------------------------------------------------------------
        # 17. General Shipment Listing / Search
        # -------------------------------------------------------------
        if any(term in lower_q for term in ['show all shipments', 'list shipments', 'find shipments', 'delayed shipments', 'in transit shipments']):
            return Intent.SHIPMENT_SEARCH, meta

        return Intent.UNKNOWN, meta

    @classmethod
    def extract_shipment_ref(cls, text: str) -> Optional[str]:
        """Extracts standard shipment references or numeric IDs."""
        # Match SHP-XXXXX or SHP-10482
        m = re.search(r'\b(SHP-[A-Za-z0-9\-]+)\b', text, re.IGNORECASE)
        if m:
            return m.group(1).upper()

        # Match "shipment 10482", "order 10482", "consignment 10482"
        m2 = re.search(r'(?:shipment|consignment|order|ref|id)\s*#?\s*([0-9]{3,7})', text, re.IGNORECASE)
        if m2:
            return f"SHP-{m2.group(1)}" if not m2.group(1).startswith("SHP-") else m2.group(1)

        # Standalone 5-digit number commonly representing an ID
        m3 = re.search(r'\b(10[0-9]{3})\b', text)
        if m3:
            return f"SHP-{m3.group(1)}"

        return None

    @classmethod
    def extract_all_shipment_refs(cls, text: str) -> List[str]:
        """Extracts all distinct shipment references or numeric IDs present in text."""
        found = []
        # SHP-XXXXX
        for m in re.finditer(r'\b(SHP-[A-Za-z0-9\-]+)\b', text, re.IGNORECASE):
            ref = m.group(1).upper()
            if ref not in found:
                found.append(ref)
        # shipment 10001
        for m in re.finditer(r'(?:shipment|consignment|order|ref|id)\s*#?\s*([0-9]{3,7})', text, re.IGNORECASE):
            num = m.group(1)
            ref = num if num.upper().startswith("SHP-") else f"SHP-{num}"
            if ref not in found:
                found.append(ref)
        # 5-digit 10xxx
        for m in re.finditer(r'\b(10[0-9]{3})\b', text):
            ref = f"SHP-{m.group(1)}"
            if ref not in found:
                found.append(ref)
        return found
