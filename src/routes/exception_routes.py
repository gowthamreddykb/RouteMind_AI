from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from extensions import db
from src.services.exception_service import ExceptionService
from src.models.exception_model import ShipmentException
from src.models.exception_action_model import ExceptionAction
from src.models.user_model import User
from src.models.audit_log_model import AuditLog
from src.security.permissions import (
    roles_required, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, normalize_role
)

exception_bp = Blueprint('exception_bp', __name__)

@exception_bp.route('/')
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def exceptions():
    search = request.args.get('search', '').strip()
    severity = request.args.get('severity', '').strip()
    status = request.args.get('status', '').strip()
    assigned = request.args.get('assigned', '').strip()

    from src.models.shipment_model import Shipment
    from sqlalchemy import or_

    # Strictly filter exceptions: only show exceptions assigned to current_user OR associated with shipments created by / assigned to current_user
    user_clauses = [
        ShipmentException.assigned_to.ilike(current_user.username),
        Shipment.assigned_to_name.ilike(current_user.username),
        Shipment.created_by_name.ilike(current_user.username),
        Shipment.assigned_to_id == current_user.id,
        Shipment.created_by_id == current_user.id
    ]
    if getattr(current_user, 'full_name', None):
        user_clauses.append(ShipmentException.assigned_to.ilike(current_user.full_name))
        user_clauses.append(Shipment.assigned_to_name.ilike(current_user.full_name))
        user_clauses.append(Shipment.created_by_name.ilike(current_user.full_name))
    if getattr(current_user, 'email', None):
        user_clauses.append(ShipmentException.assigned_to.ilike(current_user.email))
        user_clauses.append(Shipment.assigned_to_name.ilike(current_user.email))
        user_clauses.append(Shipment.created_by_name.ilike(current_user.email))

    base_q = ShipmentException.query.join(Shipment, ShipmentException.shipment_id == Shipment.id).filter(or_(*user_clauses))
    q = base_q
    if search:
        s_term = f"%{search}%"
        q = q.filter((ShipmentException.exception_type.ilike(s_term)) | (ShipmentException.assigned_to.ilike(s_term)))
    if severity and severity != 'All Severity':
        sev_upper = severity.strip().upper()
        if sev_upper in ['URGENT', 'CRITICAL']:
            q = q.filter(ShipmentException.severity.in_(['CRITICAL', 'URGENT']))
        else:
            q = q.filter(ShipmentException.severity == sev_upper)
    if status and status != 'All Statuses':
        q = q.filter(ShipmentException.status == status)
    if assigned and assigned != 'All Assignments':
        q = q.filter(ShipmentException.assigned_to.ilike(f"%{assigned}%"))

    items = q.order_by(ShipmentException.created_at.desc()).all()

    user_role = normalize_role(current_user.role)
    can_assign = (user_role == ROLE_MANAGER)
    can_resolve = (user_role in [ROLE_MANAGER, ROLE_DISPATCHER])
    can_create = (user_role in [ROLE_DISPATCHER, ROLE_MANAGER])
    is_admin = (user_role == ROLE_ADMIN)

    total_count = base_q.count()
    open_count = base_q.filter(ShipmentException.status == 'OPEN').count()
    investigating_count = base_q.filter(ShipmentException.status.in_(['INVESTIGATING', 'IN_REVIEW', 'IN_PROGRESS'])).count()
    resolved_count = base_q.filter(ShipmentException.status == 'RESOLVED').count()

    # Assignable officers: strictly exclude Admin and Operations Manager roles
    officers = [u for u in User.query.filter_by(is_active=True).all() if normalize_role(u.role) not in [ROLE_ADMIN, ROLE_MANAGER]]

    return render_template(
        'exception_list.html',
        exceptions=items,
        total_count=total_count,
        open_count=open_count,
        investigating_count=investigating_count,
        resolved_count=resolved_count,
        officers=officers,
        search=search,
        severity=severity,
        status=status,
        assigned=assigned,
        can_assign=can_assign,
        can_resolve=can_resolve,
        can_create=can_create,
        is_admin=is_admin
    )

@exception_bp.route('/api/add-note', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER)
def api_add_note():
    data = request.get_json(silent=True) or request.form
    exception_id = data.get('exception_id')
    note = data.get('note', '').strip()
    if not note:
        return jsonify({'status': 'error', 'message': 'Operational note cannot be blank.'}), 400

    ex = ShipmentException.query.get_or_404(exception_id)
    action = ExceptionAction(
        exception_id=ex.id,
        action_taken=note,
        taken_by=current_user.username
    )
    db.session.add(action)

    audit = AuditLog(
        user_id=current_user.id,
        action='EXCEPTION_NOTE_ADDED',
        entity='EXCEPTION',
        entity_id=str(ex.id),
        details=f"Note added by {current_user.username}: {note[:60]}"
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Operational note recorded persistently in database.'})

@exception_bp.route('/api/create', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER)
def api_create():
    """Dispatchers and Operations Managers can log operational exceptions."""
    data = request.get_json(silent=True) or request.form
    shipment_id = data.get('shipment_id')
    exception_type = data.get('exception_type') or data.get('type', 'BERTHING_HOLD')
    severity = data.get('severity', 'HIGH')

    ex = ExceptionService.create(
        shipment_id=shipment_id,
        exception_type=exception_type,
        severity=severity,
        assigned_to=data.get('assigned_to')
    )

    audit = AuditLog(
        user_id=current_user.id,
        action='EXCEPTION_CREATED',
        entity='EXCEPTION',
        entity_id=str(ex.id),
        details=f"Created {exception_type} on shipment #{shipment_id} ({severity}) by {current_user.username}"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'exception': ex.to_dict()})
    flash(f"Exception EXC-{ex.id:04d} created successfully.", 'success')
    return redirect(url_for('exception_bp.exceptions'))

@exception_bp.route('/api/assign', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER)
def api_assign():
    """Only Operations Managers can assign or reassign exceptions."""
    data = request.get_json(silent=True) or request.form
    exception_id = data.get('exception_id')
    assignee = data.get('assigned_to', current_user.username)

    # If assignee is an integer ID, map to username
    if str(assignee).isdigit():
        u = User.query.get(int(assignee))
        if u:
            assignee = u.username

    ex = ShipmentException.query.get_or_404(exception_id)
    old_assignee = ex.assigned_to
    ex.assigned_to = str(assignee)
    ex.status = 'INVESTIGATING'
    db.session.commit()

    # Log action
    action = ExceptionAction(
        exception_id=ex.id,
        action_taken=f"Reassigned from '{old_assignee}' to '{assignee}' by Manager {current_user.username}",
        taken_by=current_user.username
    )
    db.session.add(action)

    audit = AuditLog(
        user_id=current_user.id,
        action='EXCEPTION_ASSIGNED',
        entity='EXCEPTION',
        entity_id=str(ex.id),
        details=f"Reassigned from {old_assignee} to {assignee} by Manager {current_user.username}"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'exception': ex.to_dict()})
    flash(f"Exception EXC-{ex.id:04d} assigned to {assignee}.", 'info')
    return redirect(url_for('exception_bp.exceptions'))

@exception_bp.route('/api/resolve', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER, ROLE_DISPATCHER)
def api_resolve():
    """Managers can resolve any exception; Dispatchers can resolve authorized/assigned exceptions."""
    data = request.get_json(silent=True) or request.form
    exception_id = data.get('exception_id')

    ex = ShipmentException.query.get_or_404(exception_id)
    user_role = normalize_role(current_user.role)

    # Record-level authorization for Dispatcher
    if user_role == ROLE_DISPATCHER:
        if ex.assigned_to and current_user.username.lower() not in ex.assigned_to.lower():
            if request.is_json:
                return jsonify({'error': 'Unauthorized: Dispatchers may only resolve exceptions assigned to their scope.'}), 403
            abort(403)

    ex.status = 'RESOLVED'
    db.session.commit()

    audit = AuditLog(
        user_id=current_user.id,
        action='EXCEPTION_RESOLVED',
        entity='EXCEPTION',
        entity_id=str(ex.id),
        details=f"Resolved by {current_user.username} ({current_user.role})"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'exception': ex.to_dict(), 'message': 'Exception marked as resolved.'})
    flash(f"Exception EXC-{ex.id:04d} successfully resolved.", 'success')
    return redirect(url_for('exception_bp.exceptions'))

@exception_bp.route('/api/escalate', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER)
def api_escalate():
    data = request.get_json(silent=True) or request.form
    exception_id = data.get('exception_id')
    ex = ShipmentException.query.get_or_404(exception_id)

    ex.severity = 'CRITICAL'
    ex.status = 'INVESTIGATING'
    db.session.commit()

    audit = AuditLog(
        user_id=current_user.id,
        action='EXCEPTION_ESCALATED',
        entity='EXCEPTION',
        entity_id=str(ex.id),
        details=f"Escalated to CRITICAL by {current_user.username}"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'exception': ex.to_dict(), 'message': 'Exception escalated to Critical priority.'})
    flash(f"Exception EXC-{ex.id:04d} escalated to Critical severity.", 'warning')
    return redirect(url_for('exception_bp.exceptions'))

@exception_bp.route('/<int:exception_id>', methods=['GET'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def get_exception_detail(exception_id):
    ex = ShipmentException.query.get_or_404(exception_id)
    return jsonify({
        'status': 'success',
        'exception': ex.to_dict(),
        'shipment': ex.shipment.to_dict() if ex.shipment else None
    })

@exception_bp.route('/api/update-status', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER)
def api_update_status():
    data = request.get_json(silent=True) or request.form
    exception_id = data.get('exception_id')
    new_status = (data.get('status') or '').strip().upper()
    notes = (data.get('notes') or data.get('remarks') or '').strip()
    root_cause = (data.get('root_cause') or '').strip()

    valid_statuses = {'OPEN', 'ASSIGNED', 'INVESTIGATING', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'}
    if new_status not in valid_statuses:
        return jsonify({'status': 'error', 'message': f'Invalid status. Must be one of: {", ".join(sorted(valid_statuses))}'}), 400

    ex = ShipmentException.query.get_or_404(exception_id)
    old_status = ex.status
    ex.status = new_status
    db.session.commit()

    detail_parts = [f"Status updated from '{old_status}' to '{new_status}' by {current_user.username}"]
    if root_cause:
        detail_parts.append(f"Root Cause: {root_cause}")
    if notes:
        detail_parts.append(f"Notes: {notes}")
    action_note = " | ".join(detail_parts)

    action = ExceptionAction(
        exception_id=ex.id,
        action_taken=action_note[:250],
        taken_by=current_user.username
    )
    db.session.add(action)

    audit = AuditLog(
        user_id=current_user.id,
        action='EXCEPTION_STATUS_UPDATED',
        entity='EXCEPTION',
        entity_id=str(ex.id),
        details=action_note
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'exception': ex.to_dict(), 'message': f'Status changed to {new_status}.'})
    flash(f"Exception EXC-{ex.id:04d} updated to {new_status}.", 'success')
    return redirect(url_for('exception_bp.exceptions'))

@exception_bp.route('/api/update-priority', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER)
def api_update_priority():
    data = request.get_json(silent=True) or request.form
    exception_id = data.get('exception_id')
    new_priority = (data.get('priority') or data.get('severity') or '').strip().upper()

    valid_priorities = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
    if new_priority not in valid_priorities:
        return jsonify({'status': 'error', 'message': f'Invalid priority. Must be one of: {", ".join(sorted(valid_priorities))}'}), 400

    ex = ShipmentException.query.get_or_404(exception_id)
    old_priority = ex.severity
    ex.severity = new_priority
    db.session.commit()

    action = ExceptionAction(
        exception_id=ex.id,
        action_taken=f"Priority updated from '{old_priority}' to '{new_priority}' by {current_user.username}",
        taken_by=current_user.username
    )
    db.session.add(action)

    audit = AuditLog(
        user_id=current_user.id,
        action='EXCEPTION_PRIORITY_UPDATED',
        entity='EXCEPTION',
        entity_id=str(ex.id),
        details=f"Severity changed from {old_priority} to {new_priority} by {current_user.username}"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'exception': ex.to_dict(), 'message': f'Priority updated to {new_priority}.'})
    flash(f"Exception EXC-{ex.id:04d} priority changed to {new_priority}.", 'success')
    return redirect(url_for('exception_bp.exceptions'))

@exception_bp.route('/api/close', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER)
def api_close():
    data = request.get_json(silent=True) or request.form
    exception_id = data.get('exception_id')
    closing_notes = (data.get('notes') or data.get('remarks') or 'Closed and finalized.').strip()

    ex = ShipmentException.query.get_or_404(exception_id)
    ex.status = 'CLOSED'
    db.session.commit()

    action = ExceptionAction(
        exception_id=ex.id,
        action_taken=f"Exception closed by {current_user.username}. Notes: {closing_notes}"[:250],
        taken_by=current_user.username
    )
    db.session.add(action)

    audit = AuditLog(
        user_id=current_user.id,
        action='EXCEPTION_CLOSED',
        entity='EXCEPTION',
        entity_id=str(ex.id),
        details=f"Closed by {current_user.username}: {closing_notes}"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'exception': ex.to_dict(), 'message': 'Exception closed successfully.'})
    flash(f"Exception EXC-{ex.id:04d} closed.", 'info')
    return redirect(url_for('exception_bp.exceptions'))

