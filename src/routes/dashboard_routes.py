"""
dashboard_routes.py - RouteMind AI Enterprise Dashboard Analytics Controller
Provides authenticated JSON API endpoints for Control Tower dynamic charts.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from src.services.dashboard_service import DashboardService
from src.security.permissions import roles_required, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN

dashboard_bp = Blueprint('dashboard_bp', __name__)


@dashboard_bp.route('/charts', methods=['GET'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def get_all_dashboard_charts():
    """Retrieve full dashboard analytics payload for all 4 charts."""
    start_date = request.args.get('start_date') or request.args.get('from')
    end_date = request.args.get('end_date') or request.args.get('to')
    exception_status = request.args.get('exception_status')

    payload = DashboardService.get_all_charts(
        start_date=start_date,
        end_date=end_date,
        exception_status=exception_status,
        user=current_user
    )
    return jsonify(payload), 200


@dashboard_bp.route('/chart/<chart_name>', methods=['GET'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def get_single_dashboard_chart(chart_name):
    """Retrieve or refresh a single chart with custom query parameters."""
    start_date = request.args.get('start_date') or request.args.get('from')
    end_date = request.args.get('end_date') or request.args.get('to')

    chart_name = (chart_name or '').lower().strip()

    if chart_name in ['status', 'status_overview', 'status_distribution', 'status_doughnut', 'shipment_status']:
        data = DashboardService.get_shipment_status_distribution(
            start_date=start_date,
            end_date=end_date,
            user=current_user
        )
    elif chart_name in ['destination', 'region', 'destination_region', 'volume', 'destination_volume', 'shipment_destination']:
        data = DashboardService.get_shipment_volume_by_destination_region(
            start_date=start_date,
            end_date=end_date,
            user=current_user
        )
    elif chart_name in ['risk', 'risk_distribution', 'shipment_risk']:
        data = DashboardService.get_shipment_risk_distribution(
            start_date=start_date,
            end_date=end_date,
            user=current_user
        )
    elif chart_name in ['exceptions', 'exception_priority', 'priority']:
        status_filter = request.args.get('status') or request.args.get('exception_status')
        data = DashboardService.get_exception_priority_analysis(
            status_filter=status_filter,
            start_date=start_date,
            end_date=end_date,
            user=current_user
        )
    else:
        return jsonify({
            'status': 'error',
            'error': f"Unknown chart identifier: '{chart_name}'",
            'valid_charts': ['destination_volume', 'status_overview', 'risk_distribution', 'exception_priority']
        }), 400

    return jsonify({
        'status': 'success',
        'chart': data
    }), 200
