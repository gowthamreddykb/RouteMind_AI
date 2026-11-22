from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from extensions import db
from src.services.communication_service import CommunicationService
from src.models.shipment_model import Shipment
from src.models.communication_model import CommunicationLog
from src.models.audit_log_model import AuditLog
from src.security.permissions import (
    roles_required, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN,
    can_approve_communication, normalize_role
)

comm_bp = Blueprint('comm_bp', __name__)

@comm_bp.route('/')
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def communications():
    logs = CommunicationService.get_recent()
    recent_shipments = Shipment.query.filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK'])).limit(5).all()

    req_shipment_id = request.args.get('shipment_id')
    selected_shipment = None
    if req_shipment_id:
        try:
            selected_shipment = Shipment.query.get(int(req_shipment_id))
        except (ValueError, TypeError):
            selected_shipment = None

    if not selected_shipment and recent_shipments:
        selected_shipment = recent_shipments[0]

    user_role = normalize_role(current_user.role)
    is_manager = (user_role == ROLE_MANAGER)
    is_admin = (user_role == ROLE_ADMIN)
    is_dispatcher = (user_role == ROLE_DISPATCHER)

    return render_template(
        'ai_communications.html',
        logs=logs,
        high_risk_shipments=recent_shipments,
        target_shipment=selected_shipment,
        is_manager=is_manager,
        is_admin=is_admin,
        is_dispatcher=is_dispatcher
    )

@comm_bp.route('/api/approve', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER)
def api_approve():
    """Only Operations Managers can approve and dispatch operational notices."""
    data = request.get_json(silent=True) or request.form
    comm_id = data.get('comm_id')
    c = CommunicationLog.query.get(comm_id) if comm_id else None

    if c:
        shipment_id = c.shipment_id
    else:
        shipment_id = data.get('shipment_id')
        recipient = data.get('recipient', 'Customer Logistics Desk')
        subject = data.get('subject') or f"Operational Delay Advisory – Shipment #{shipment_id or 'BULK'}"
        body = data.get('body') or "Approved operational advisory dispatched to client operations desk."

        c = CommunicationService.log_communication(
            shipment_id=shipment_id,
            recipient=recipient,
            channel=data.get('channel', 'EMAIL'),
            subject=subject,
            body=body,
            prompt_version=data.get('prompt_version', 'v1.0.0')
        )

    audit = AuditLog(
        user_id=current_user.id,
        action='COMMUNICATION_APPROVED_AND_DISPATCHED',
        entity='COMMUNICATION_LOG',
        entity_id=str(c.id),
        details=f"Approved by Operations Manager {current_user.username} for shipment #{shipment_id}"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'communication': c.to_dict(), 'message': 'Communication approved and dispatched.'})
    flash('Communication approved and dispatched to customer.', 'success')
    return redirect(url_for('comm_bp.communications'))

@comm_bp.route('/api/reject', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER)
def api_reject():
    """Only Operations Managers can reject drafts."""
    data = request.get_json(silent=True) or request.form
    shipment_id = data.get('shipment_id')
    reason = data.get('reason', 'Draft rejected by Operations Manager. Revisions requested.')

    audit = AuditLog(
        user_id=current_user.id,
        action='COMMUNICATION_REJECTED',
        entity='SHIPMENT',
        entity_id=str(shipment_id),
        details=f"Draft rejected by Operations Manager {current_user.username}: {reason}"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'rejected', 'shipment_id': shipment_id, 'reason': reason})
    flash('Draft rejected and returned to dispatcher queue.', 'warning')
    return redirect(url_for('comm_bp.communications'))

@comm_bp.route('/api/request-changes', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER)
def api_request_changes():
    """Operations Managers can request edits/changes on customer drafts."""
    data = request.get_json(silent=True) or request.form
    shipment_id = data.get('shipment_id')
    notes = data.get('notes', 'Operations Manager requested adjustments to customer delay notice.')

    audit = AuditLog(
        user_id=current_user.id,
        action='COMMUNICATION_CHANGES_REQUESTED',
        entity='SHIPMENT',
        entity_id=str(shipment_id),
        details=f"Revision requested by Manager {current_user.username}: {notes}"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'changes_requested', 'shipment_id': shipment_id, 'notes': notes})
    flash('Revision request sent to dispatcher.', 'info')
    return redirect(url_for('comm_bp.communications'))

@comm_bp.route('/api/submit-draft', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER)
def api_submit_draft():
    """Dispatchers can prepare and submit communication drafts for manager review."""
    data = request.get_json(silent=True) or request.form
    shipment_id = data.get('shipment_id')

    audit = AuditLog(
        user_id=current_user.id,
        action='COMMUNICATION_DRAFT_SUBMITTED',
        entity='SHIPMENT',
        entity_id=str(shipment_id),
        details=f"Draft submitted for manager approval by {current_user.username} ({current_user.role})"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'submitted', 'shipment_id': shipment_id, 'message': 'Draft submitted for manager review.'})
    flash('Communication draft submitted for Operations Manager approval.', 'info')
    return redirect(url_for('comm_bp.communications'))

# Backward compatibility alias
@comm_bp.route('/api/send', methods=['POST'])
@login_required
def api_send():
    if not can_approve_communication(current_user):
        abort(403)
    return api_approve()
