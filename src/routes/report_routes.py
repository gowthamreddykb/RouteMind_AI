from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from src.security.permissions import roles_required, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN
from src.services.report_service import ReportService

report_bp = Blueprint('report_bp', __name__)

@report_bp.route('/')
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def reports():
    from src.models.shipment_model import Shipment
    kpis = ReportService.get_kpis()
    chart_data = ReportService.get_chart_data()
    shipments = Shipment.query.order_by(Shipment.order_date.desc()).limit(15).all()
    return render_template('reports.html', kpis=kpis, chart_data=chart_data, shipments=shipments)

@report_bp.route('/api/kpis')
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def api_kpis():
    return jsonify(ReportService.get_kpis())

@report_bp.route('/api/chart-data')
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def api_chart_data():
    return jsonify(ReportService.get_chart_data())

@report_bp.route('/export')
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def export_general_report():
    import json
    from flask import Response
    from src.models.shipment_model import Shipment
    kpis = ReportService.get_kpis()
    chart_data = ReportService.get_chart_data()
    shipments = [s.to_dict() for s in Shipment.query.all()]
    payload = {
        'generated_at': ReportService.get_kpis(),
        'kpis': kpis,
        'analytics': chart_data,
        'shipments_count': len(shipments),
        'shipments': shipments
    }
    return Response(
        json.dumps(payload, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=RouteMind_Operations_Report.json'}
    )

@report_bp.route('/export/shipment/<shipment_number>')
@login_required
@roles_required(ROLE_ADMIN)
def export_shipment(shipment_number):
    from src.models.shipment_model import Shipment
    from flask import Response
    import json
    s = Shipment.query.filter_by(shipment_number=shipment_number).first_or_404()
    export_payload = {
        'consignment_telemetry': s.to_dict(),
        'customer': f"{s.customer.first_name} {s.customer.last_name}" if s.customer else "N/A",
        'product': s.product.product_name if s.product else "N/A",
        'exceptions': [e.to_dict() for e in s.exceptions] if s.exceptions else [],
        'events': [e.to_dict() for e in s.events] if s.events else []
    }
    return Response(
        json.dumps(export_payload, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment;filename=Shipment_{shipment_number}_Report.json'}
    )
