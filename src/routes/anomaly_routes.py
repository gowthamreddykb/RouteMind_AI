from flask import Blueprint, render_template, jsonify, request
from src.services.anomaly_service import AnomalyService
from src.models.shipment_model import Shipment

anomaly_bp = Blueprint('anomaly_bp', __name__)

@anomaly_bp.route('/')
def anomalies():
    # Query database for anomalous shipments
    items = Shipment.query.filter(
        (Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK'])) | 
        (Shipment.dispatch_prob >= 0.40) | 
        (Shipment.order_creation_prob >= 0.40)
    ).order_by(Shipment.order_date.desc()).all()
    return render_template('anomaly_list.html', anomalies=items)

@anomaly_bp.route('/api/detect', methods=['POST'])
def api_detect():
    data = request.get_json(silent=True) or []
    return jsonify(AnomalyService.detect_anomalies(data))
