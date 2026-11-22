"""
dashboard_service.py - RouteMind AI Enterprise Dashboard Analytics Service
Provides high-performance, reusable SQL aggregations for live Control Tower charts.
Grounded strictly in actual MySQL database records, preventing duplicate counting
and honoring role-based access control.
"""
import urllib.parse
import datetime as dt
from collections import defaultdict, Counter
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import func, or_, and_, desc

from extensions import db
from src.models.shipment_model import Shipment
from src.models.model_score_model import ModelScore
from src.models.exception_model import ShipmentException
from src.models.user_model import User
from src.security.permissions import normalize_role, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN

# Standard 9 Maritime Lifecycle Statuses
LIFECYCLE_STATUSES = [
    ("CREATED", "Created"),
    ("BOOKING_CONFIRMED", "Booking Confirmed"),
    ("READY_FOR_DISPATCH", "Ready for Dispatch"),
    ("DISPATCHED", "Dispatched"),
    ("IN_TRANSIT", "In Transit"),
    ("ARRIVED_AT_DESTINATION", "Arrived at Destination"),
    ("OUT_FOR_DELIVERY", "Out for Delivery"),
    ("DELIVERED", "Delivered"),
    ("COMPLETED", "Completed"),
]

LIFECYCLE_KEYS = [k for k, _ in LIFECYCLE_STATUSES]

# Status alias normalization mapping raw DB entries to standard lifecycle stages
STATUS_ALIASES = {
    "PENDING": "CREATED",
    "ORDER_CREATED": "CREATED",
    "BOOKED": "BOOKING_CONFIRMED",
    "READY": "READY_FOR_DISPATCH",
    "DISPATCHED": "DISPATCHED",
    "IN_TRANSIT": "IN_TRANSIT",
    "OCEAN IN-TRANSIT": "IN_TRANSIT",
    "DELAYED": "IN_TRANSIT",
    "HOLD": "IN_TRANSIT",
    "EXCEPTION_HOLD": "IN_TRANSIT",
    "ARRIVED": "ARRIVED_AT_DESTINATION",
    "ARRIVED_AT_PORT": "ARRIVED_AT_DESTINATION",
    "ARRIVED_AT_DESTINATION": "ARRIVED_AT_DESTINATION",
    "OUT_FOR_DELIVERY": "OUT_FOR_DELIVERY",
    "DELIVERED": "DELIVERED",
    "DELIVERED TO CONSIGNEE": "DELIVERED",
    "COMPLETED": "COMPLETED",
}

# Configurable Risk Thresholds
RISK_CONFIG = {
    "LOW_MAX_PROB": 0.40,      # prob < 0.40 -> Low Risk
    "MED_MAX_PROB": 0.70,      # 0.40 <= prob < 0.70 -> Medium Risk
    "HIGH_MIN_PROB": 0.70      # prob >= 0.70 -> High Risk
}


class DashboardService:

    @staticmethod
    def _apply_user_scope(query, model, user=None):
        """Apply RBAC data scoping. Dispatchers view assigned/created records; Managers/Admins view all."""
        if not user or not getattr(user, 'is_authenticated', False):
            return query

        role = normalize_role(getattr(user, 'role', ''))
        if role in [ROLE_MANAGER, ROLE_ADMIN]:
            return query

        username = (getattr(user, 'username', '') or '').strip()
        user_id = getattr(user, 'id', None)

        if model == Shipment:
            conditions = []
            if username:
                conditions.extend([
                    Shipment.created_by_name == username,
                    Shipment.assigned_to_name == username
                ])
            if user_id:
                conditions.extend([
                    Shipment.created_by_id == user_id,
                    Shipment.assigned_to_id == user_id
                ])
            if conditions:
                query = query.filter(or_(*conditions))

        elif model == ShipmentException:
            conditions = []
            if username:
                conditions.append(ShipmentException.assigned_to == username)
            if hasattr(ShipmentException, 'shipment') and (username or user_id):
                ship_conds = []
                if username:
                    ship_conds.extend([
                        Shipment.created_by_name == username,
                        Shipment.assigned_to_name == username
                    ])
                if user_id:
                    ship_conds.extend([
                        Shipment.created_by_id == user_id,
                        Shipment.assigned_to_id == user_id
                    ])
                if ship_conds:
                    query = query.join(Shipment, ShipmentException.shipment_id == Shipment.id).filter(
                        or_(or_(*conditions), or_(*ship_conds))
                    )
                    return query
            if conditions:
                query = query.filter(or_(*conditions))

        return query

    @staticmethod
    def _parse_dates(start_date=None, end_date=None) -> Tuple[Optional[dt.datetime], Optional[dt.datetime]]:
        s_dt, e_dt = None, None
        if start_date:
            try:
                if isinstance(start_date, str):
                    s_dt = dt.datetime.strptime(start_date[:10], '%Y-%m-%d')
                elif isinstance(start_date, (dt.date, dt.datetime)):
                    s_dt = dt.datetime.combine(start_date, dt.time.min) if isinstance(start_date, dt.date) else start_date
            except Exception:
                s_dt = None
        if end_date:
            try:
                if isinstance(end_date, str):
                    e_dt = dt.datetime.strptime(end_date[:10], '%Y-%m-%d') + dt.timedelta(days=1) - dt.timedelta(microseconds=1)
                elif isinstance(end_date, (dt.date, dt.datetime)):
                    e_dt = (dt.datetime.combine(end_date, dt.time.max) if isinstance(end_date, dt.date) else end_date)
            except Exception:
                e_dt = None
        return s_dt, e_dt

    # -------------------------------------------------------------------------
    # CHART 1: SHIPMENT VOLUME BY DESTINATION REGION (Vertical Bar Chart)
    # -------------------------------------------------------------------------
    @classmethod
    def get_shipment_volume_by_destination_region(cls, start_date=None, end_date=None, user=None) -> Dict[str, Any]:
        """
        Group actual shipment records by destination region.
        Vertical bar chart:
        - X-axis: Destination Regions
        - Y-axis: Number of Shipments
        - Counts in tooltips
        - Clickable bars navigating to filtered shipment list
        """
        s_dt, e_dt = cls._parse_dates(start_date, end_date)

        query = Shipment.query
        query = cls._apply_user_scope(query, Shipment, user)
        if s_dt:
            query = query.filter(Shipment.order_date >= s_dt)
        if e_dt:
            query = query.filter(Shipment.order_date <= e_dt)

        shipments = query.all()
        total_shipments = len(shipments)

        # Count by destination_region
        region_counter = Counter(
            (s.destination_region or 'Unspecified').strip() for s in shipments
        )

        # Sort regions descending by shipment volume
        sorted_regions = sorted(region_counter.items(), key=lambda kv: (-kv[1], kv[0]))

        labels = []
        counts = []
        percentages = []
        filter_urls = []

        for region, count in sorted_regions:
            pct = round((count / max(total_shipments, 1)) * 100, 1) if total_shipments > 0 else 0.0
            labels.append(region)
            counts.append(count)
            percentages.append(pct)
            # Both destination_region and search parameter for universal matching
            filter_urls.append(f"/shipments/?destination_region={urllib.parse.quote(region)}&search={urllib.parse.quote(region)}")

        return {
            "chart_id": "shipment_destination_volume",
            "chart_type": "bar",
            "title": "Shipment Volume by Destination Region",
            "subtitle": f"Total volume across {len(labels)} maritime destination regions ({total_shipments} consignments)",
            "x_axis_label": "Destination Region",
            "y_axis_label": "Number of Shipments",
            "labels": labels,
            "counts": counts,
            "percentages": percentages,
            "bar_color": "#4338CA",
            "bar_hover_color": "#3730A3",
            "filter_urls": filter_urls,
            "total_shipments": total_shipments,
            "empty": total_shipments == 0
        }

    # -------------------------------------------------------------------------
    # CHART 2: SHIPMENT STATUS OVERVIEW (Horizontal Bar Chart)
    # -------------------------------------------------------------------------
    @classmethod
    def get_shipment_status_overview(cls, start_date=None, end_date=None, user=None) -> Dict[str, Any]:
        """
        Horizontal bar chart displaying shipment counts for each actual status:
        Created, Booking Confirmed, Ready for Dispatch, Dispatched, In Transit,
        Arrived at Destination, Out for Delivery, Delivered, and Completed.
        Counts displayed beside each bar; clickable to filter shipment list.
        """
        s_dt, e_dt = cls._parse_dates(start_date, end_date)

        query = Shipment.query
        query = cls._apply_user_scope(query, Shipment, user)
        if s_dt:
            query = query.filter(Shipment.order_date >= s_dt)
        if e_dt:
            query = query.filter(Shipment.order_date <= e_dt)

        shipments = query.all()
        total_count = len(shipments)

        # Count by normalized lifecycle status
        status_counts = {k: 0 for k in LIFECYCLE_KEYS}
        for s in shipments:
            raw_s = (s.order_status or 'CREATED').strip().upper()
            norm_s = STATUS_ALIASES.get(raw_s, raw_s if raw_s in LIFECYCLE_KEYS else 'CREATED')
            status_counts[norm_s] += 1

        labels = []
        counts = []
        percentages = []
        filter_urls = []
        status_codes = []

        # Distinct colors for each lifecycle stage (slate, sky, amber, indigo, royal blue, purple, pink, emerald, teal)
        colors = [
            '#64748B',  # Created
            '#0EA5E9',  # Booking Confirmed
            '#F59E0B',  # Ready for Dispatch
            '#6366F1',  # Dispatched
            '#3B82F6',  # In Transit
            '#8B5CF6',  # Arrived at Destination
            '#EC4899',  # Out for Delivery
            '#10B981',  # Delivered
            '#059669',  # Completed
        ]

        for code, label in LIFECYCLE_STATUSES:
            cnt = status_counts.get(code, 0)
            pct = round((cnt / max(total_count, 1) * 100), 1) if total_count > 0 else 0.0
            labels.append(label)
            counts.append(cnt)
            percentages.append(pct)
            status_codes.append(code)
            filter_urls.append(f"/shipments/?status={code}")

        return {
            "chart_id": "shipment_status_overview",
            "chart_type": "horizontalBar",
            "title": "Shipment Status Overview",
            "subtitle": f"Live consignment volume across all nine lifecycle statuses ({total_count} total)",
            "x_axis_label": "Number of Shipments",
            "y_axis_label": "Lifecycle Status",
            "labels": labels,
            "status_codes": status_codes,
            "counts": counts,
            "percentages": percentages,
            "colors": colors,
            "filter_urls": filter_urls,
            "total_shipments": total_count,
            "empty": total_count == 0
        }

    # -------------------------------------------------------------------------
    # CHART 1: SHIPMENT STATUS DISTRIBUTION (Doughnut Chart)
    # -------------------------------------------------------------------------
    @classmethod
    def get_shipment_status_distribution(cls, start_date=None, end_date=None, user=None) -> Dict[str, Any]:
        """
        Doughnut chart displaying shipment distribution across all 9 maritime lifecycle stages.
        """
        res = cls.get_shipment_status_overview(start_date, end_date, user)
        res["chart_id"] = "shipment_status_distribution"
        res["chart_type"] = "doughnut"
        res["title"] = "Shipment Status Distribution"
        res["subtitle"] = "All nine maritime lifecycle stages (Click segment to filter)"
        return res

    # -------------------------------------------------------------------------
    # CHART 3: SHIPMENT RISK DISTRIBUTION (Vertical Bar Chart - Overall)
    # -------------------------------------------------------------------------
    @classmethod
    def get_shipment_risk_distribution(cls, start_date=None, end_date=None, user=None) -> Dict[str, Any]:
        """
        Overall shipment risk distribution for active consignments (vertical bar chart):
        - Three bars: Low Risk, Medium Risk, High Risk
        - Uses latest valid prediction for each active shipment (counted only once)
        - Shows shipment count and percentage for each risk category
        - Clickable bars filter matching shipments
        """
        s_dt, e_dt = cls._parse_dates(start_date, end_date)

        # 1. Active shipments only (not delivered or completed)
        active_q = Shipment.query.filter(
            Shipment.order_status.notin_(['DELIVERED', 'COMPLETED'])
        )
        active_q = cls._apply_user_scope(active_q, Shipment, user)
        if s_dt:
            active_q = active_q.filter(Shipment.order_date >= s_dt)
        if e_dt:
            active_q = active_q.filter(Shipment.order_date <= e_dt)

        active_shipments = active_q.all()
        total_active = len(active_shipments)
        active_ids = [s.id for s in active_shipments]

        if not active_ids:
            return {
                "chart_id": "shipment_risk_distribution",
                "chart_type": "bar",
                "title": "Shipment Risk Distribution",
                "subtitle": "Overall predicted risk across active consignments (0 active shipments)",
                "labels": ["Low Risk", "Medium Risk", "High Risk"],
                "risk_keys": ["LOW", "MEDIUM", "HIGH"],
                "counts": [0, 0, 0],
                "percentages": [0.0, 0.0, 0.0],
                "colors": ["#10B981", "#F59E0B", "#EF4444"],
                "filter_urls": [
                    "/shipments/?risk=Low+Risk",
                    "/shipments/?risk=Medium+Risk",
                    "/shipments/?risk=High+Risk"
                ],
                "total_active": 0,
                "empty": True
            }

        # 2. Query latest prediction per shipment across model_scores table (counted only once)
        subq = db.session.query(
            ModelScore.shipment_id,
            func.max(ModelScore.id).label('max_score_id')
        ).filter(
            ModelScore.shipment_id.in_(active_ids)
        ).group_by(ModelScore.shipment_id).subquery()

        latest_scores = db.session.query(ModelScore).join(
            subq, ModelScore.id == subq.c.max_score_id
        ).all()

        scored_map = {sc.shipment_id: sc for sc in latest_scores}

        # 3. Categorize each active shipment exactly once using consistent thresholds
        low_count, med_count, high_count = 0, 0, 0

        for s in active_shipments:
            score = scored_map.get(s.id)
            if score:
                risk = (score.risk_level or '').upper()
                prob = score.predicted_probability
            else:
                # Use latest probability from shipment record
                if s.dispatch_prob is not None:
                    prob = float(s.dispatch_prob)
                    risk = 'HIGH' if prob >= RISK_CONFIG["HIGH_MIN_PROB"] else ('MEDIUM' if prob >= RISK_CONFIG["LOW_MAX_PROB"] else 'LOW')
                elif s.order_creation_prob is not None:
                    prob = float(s.order_creation_prob)
                    risk = 'HIGH' if prob >= RISK_CONFIG["HIGH_MIN_PROB"] else ('MEDIUM' if prob >= RISK_CONFIG["LOW_MAX_PROB"] else 'LOW')
                else:
                    risk = (s.risk_level or 'LOW').upper()
                    prob = 0.25

            if risk in ['HIGH', 'CRITICAL', 'CRITICAL_RISK']:
                high_count += 1
            elif risk in ['MEDIUM', 'ELEVATED', 'ELEVATED_RISK']:
                med_count += 1
            else:
                low_count += 1

        total_assessed = low_count + med_count + high_count
        low_pct = round((low_count / max(total_assessed, 1)) * 100, 1)
        med_pct = round((med_count / max(total_assessed, 1)) * 100, 1)
        high_pct = round((high_count / max(total_assessed, 1)) * 100, 1)

        return {
            "chart_id": "shipment_risk_distribution",
            "chart_type": "bar",
            "title": "Shipment Risk Distribution",
            "subtitle": f"Overall predicted risk across {total_active} active consignments (Latest valid model inference)",
            "x_axis_label": "Risk Classification",
            "y_axis_label": "Active Consignments",
            "labels": ["Low Risk", "Medium Risk", "High Risk"],
            "risk_keys": ["LOW", "MEDIUM", "HIGH"],
            "counts": [low_count, med_count, high_count],
            "percentages": [low_pct, med_pct, high_pct],
            "colors": ["#10B981", "#F59E0B", "#EF4444"],
            "filter_urls": [
                "/shipments/?risk=Low+Risk",
                "/shipments/?risk=Medium+Risk",
                "/shipments/?risk=High+Risk"
            ],
            "total_active": total_active,
            "empty": total_active == 0
        }

    # -------------------------------------------------------------------------
    # CHART 4: EXCEPTION ANALYSIS BY PRIORITY (Horizontal Bar Chart - UNMODIFIED)
    # -------------------------------------------------------------------------
    @classmethod
    def get_exception_priority_analysis(cls, status_filter=None, start_date=None, end_date=None, user=None) -> Dict[str, Any]:
        """
        Group exceptions into Low, Medium, High, and Urgent priority.
        Horizontal bar chart. Filterable by exception status (All, Open, Investigating, Resolved).
        Preserved without modification.
        """
        s_dt, e_dt = cls._parse_dates(start_date, end_date)

        query = ShipmentException.query
        query = cls._apply_user_scope(query, ShipmentException, user)

        # Apply status filter if specified
        status_filter = (status_filter or '').strip().upper()
        if status_filter and status_filter != 'ALL':
            if status_filter in ['OPEN', 'UNASSIGNED']:
                query = query.filter(ShipmentException.status.in_(['OPEN', 'UNASSIGNED']))
            elif status_filter in ['INVESTIGATING', 'IN_PROGRESS', 'IN_REVIEW', 'ASSIGNED']:
                query = query.filter(ShipmentException.status.in_(['INVESTIGATING', 'IN_PROGRESS', 'IN_REVIEW', 'ASSIGNED']))
            elif status_filter in ['RESOLVED', 'CLOSED']:
                query = query.filter(ShipmentException.status.in_(['RESOLVED', 'CLOSED']))
            else:
                query = query.filter(ShipmentException.status == status_filter)

        if s_dt:
            query = query.filter(ShipmentException.created_at >= s_dt)
        if e_dt:
            query = query.filter(ShipmentException.created_at <= e_dt)

        exceptions = query.all()
        total_exceptions = len(exceptions)

        # Categorize into Low, Medium, High, Urgent
        priority_buckets = {
            "Low": 0,
            "Medium": 0,
            "High": 0,
            "Urgent": 0
        }

        priority_details = {
            "Low": [],
            "Medium": [],
            "High": [],
            "Urgent": []
        }

        for exc in exceptions:
            sev = (exc.severity or getattr(exc, 'priority', None) or 'MEDIUM').strip().upper()
            if sev in ['CRITICAL', 'URGENT']:
                b_name = "Urgent"
            elif sev == 'HIGH':
                b_name = "High"
            elif sev in ['MEDIUM', 'MODERATE']:
                b_name = "Medium"
            else:
                b_name = "Low"

            priority_buckets[b_name] += 1
            priority_details[b_name].append({
                "id": exc.id,
                "shipment_id": exc.shipment_id,
                "type": exc.exception_type,
                "status": exc.status,
                "created_at": exc.created_at.strftime('%Y-%m-%d %H:%M') if exc.created_at else 'N/A'
            })

        ordered_priorities = [
            ("Low", "#64748B", "/exceptions/?severity=LOW"),
            ("Medium", "#3B82F6", "/exceptions/?severity=MEDIUM"),
            ("High", "#F59E0B", "/exceptions/?severity=HIGH"),
            ("Urgent", "#E11D48", "/exceptions/?severity=CRITICAL")
        ]

        labels = [p[0] for p in ordered_priorities]
        colors = [p[1] for p in ordered_priorities]
        filter_urls = [p[2] for p in ordered_priorities]
        counts = [priority_buckets[p[0]] for p in ordered_priorities]
        percentages = [
            round((c / max(total_exceptions, 1)) * 100, 1) for c in counts
        ]

        active_status_label = status_filter if status_filter and status_filter != 'ALL' else 'All Statuses'

        return {
            "chart_id": "exception_priority_analysis",
            "chart_type": "horizontalBar",
            "title": "Exception Analysis by Priority",
            "subtitle": f"Priority distribution across {total_exceptions} recorded operational exceptions ({active_status_label})",
            "status_filter": status_filter or 'ALL',
            "labels": labels,
            "counts": counts,
            "percentages": percentages,
            "colors": colors,
            "filter_urls": filter_urls,
            "total_exceptions": total_exceptions,
            "empty": total_exceptions == 0
        }

    # -------------------------------------------------------------------------
    # MASTER PAYLOAD FOR ALL 4 CHARTS
    # -------------------------------------------------------------------------
    @classmethod
    def get_all_charts(cls, start_date=None, end_date=None, exception_status=None, user=None, **kwargs) -> Dict[str, Any]:
        """Aggregate all 4 charts in a single efficient payload."""
        st_dist = cls.get_shipment_status_distribution(start_date, end_date, user)
        dest_vol = cls.get_shipment_volume_by_destination_region(start_date, end_date, user)
        risk_dist = cls.get_shipment_risk_distribution(start_date, end_date, user)
        exc_prio = cls.get_exception_priority_analysis(exception_status, start_date, end_date, user)

        return {
            "status": "success",
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "charts": {
                "status_distribution": st_dist,
                "status": st_dist,
                "status_overview": st_dist,
                "destination_volume": dest_vol,
                "destination": dest_vol,
                "risk_distribution": risk_dist,
                "risk": risk_dist,
                "exception_priority": exc_prio,
                "exceptions": exc_prio
            }
        }
