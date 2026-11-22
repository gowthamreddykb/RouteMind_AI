import datetime as dt
from collections import defaultdict
from sqlalchemy import func
from extensions import db
from src.models.shipment_model import Shipment
from src.models.exception_model import ShipmentException
from src.models.escalation_model import ManagerEscalation

class ReportService:
    @staticmethod
    def get_kpis():
        total = Shipment.query.count()
        critical = Shipment.query.filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK'])).count()
        in_transit = Shipment.query.filter(Shipment.order_status.in_(['IN_TRANSIT', 'PENDING', 'Ocean In-Transit'])).count()
        delayed = Shipment.query.filter(Shipment.order_status.in_(['DELAYED', 'HOLD', 'EXCEPTION_HOLD'])).count()
        clear = Shipment.query.filter_by(dock_clearance_status='CLEAR_FOR_TRANSIT').count()
        on_time = Shipment.query.filter_by(risk_level='LOW').count()

        return {
            'total_shipments': total,
            'high_risk_count': critical,
            'in_transit_count': in_transit,
            'delayed_count': delayed,
            'on_track_count': clear,
            'on_time_count': on_time,
            'sla_compliance_rate': round(((total - critical) / max(total, 1)) * 100, 1),
            'model_01_accuracy': 68.12,
            'model_02_accuracy': 97.52
        }

    @staticmethod
    def get_chart_data():
        """Retrieve aggregated database metrics for dynamic Chart.js rendering."""
        # 1. Real Status Breakdown for Doughnut Chart
        in_transit = Shipment.query.filter(Shipment.order_status.in_(['IN_TRANSIT', 'PENDING', 'Ocean In-Transit'])).count()
        arrived = Shipment.query.filter(Shipment.order_status.in_(['DELIVERED', 'ARRIVED', 'ARRIVED_AT_PORT'])).count()
        delayed = Shipment.query.filter(Shipment.order_status.in_(['DELAYED', 'HOLD', 'EXCEPTION_HOLD'])).count()
        exceptions = ShipmentException.query.filter(ShipmentException.status.in_(['OPEN', 'INVESTIGATING', 'IN_PROGRESS'])).count()

        status_chart = {
            'labels': ['In Transit', 'Arrived / Delivered', 'Delayed / Hold', 'Open Exceptions'],
            'data': [in_transit, arrived, delayed, exceptions]
        }

        # 2. Real Delivery Performance over Recent Months
        # Group shipments by month name
        all_shipments = Shipment.query.all()
        month_scheduled = defaultdict(int)
        month_delivered = defaultdict(int)

        now = dt.datetime.now(dt.timezone.utc)
        # Generate last 6 month labels
        month_labels = []
        for i in range(5, -1, -1):
            m_date = now - dt.timedelta(days=i*30)
            m_label = m_date.strftime('%b')
            if m_label not in month_labels:
                month_labels.append(m_label)

        for s in all_shipments:
            d = s.order_date or s.created_at or now
            m_name = d.strftime('%b')
            month_scheduled[m_name] += 1
            if s.order_status in ['DELIVERED', 'ARRIVED'] or s.risk_level == 'LOW':
                month_delivered[m_name] += 1

        perf_chart = {
            'labels': month_labels,
            'scheduled': [month_scheduled.get(m, 0) for m in month_labels],
            'delivered': [month_delivered.get(m, 0) for m in month_labels]
        }

        # 3. Risk Distribution
        low_count = Shipment.query.filter_by(risk_level='LOW').count()
        med_count = Shipment.query.filter(Shipment.risk_level.in_(['MEDIUM', 'ELEVATED_RISK'])).count()
        high_count = Shipment.query.filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK'])).count()

        risk_dist = {
            'labels': ['Low Risk', 'Medium Risk', 'High / Critical Risk'],
            'data': [low_count, med_count, high_count]
        }

        # 4. Regional Breakdown
        reg_query = db.session.query(
            Shipment.destination_region,
            func.count(Shipment.id)
        ).group_by(Shipment.destination_region).all()
        regions = {r: c for r, c in reg_query if r}

        # 5. Shipping Mode Distribution
        mode_query = db.session.query(
            Shipment.shipping_mode,
            func.count(Shipment.id)
        ).group_by(Shipment.shipping_mode).all()
        modes = {m: c for m, c in mode_query if m}

        return {
            'status_chart': status_chart,
            'performance_chart': perf_chart,
            'risk_distribution': risk_dist,
            'regional_distribution': regions,
            'mode_distribution': modes
        }
