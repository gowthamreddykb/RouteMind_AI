from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from extensions import db
from src.services.escalation_service import EscalationService
from src.models.escalation_model import ManagerEscalation
from src.models.shipment_model import Shipment
from src.security.permissions import (
    roles_required, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, normalize_role
)

escalation_bp = Blueprint('escalation_bp', __name__)

def user_can_access_escalation(escalation, user):
    """Check if the user is either the creator or the assigned owner of the escalation."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    user_id = user.id
    username = (user.username or '').strip().lower()
    full_name = (getattr(user, 'full_name', None) or '').strip().lower()
    email = (getattr(user, 'email', None) or '').strip().lower()

    by_id = escalation.escalated_by_id
    by_name = (escalation.escalated_by_name or '').strip().lower()
    to_id = escalation.assigned_to_id
    to_name = (escalation.assigned_to_name or '').strip().lower()

    is_creator = (by_id == user_id) or (username and by_name == username) or (full_name and by_name == full_name) or (email and by_name == email)
    is_assignee = (to_id == user_id) or (username and to_name == username) or (full_name and to_name == full_name) or (email and to_name == email)
    return is_creator or is_assignee

@escalation_bp.route('/')
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def index():
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    
    # Strictly filter escalations: only show escalations assigned to or created by current_user
    escalations = EscalationService.get_escalations(
        status=status_filter, 
        priority=priority_filter,
        user=current_user
    )
    kpis = EscalationService.get_kpis(user=current_user)
    
    user_role = normalize_role(current_user.role)
    is_manager = (user_role == ROLE_MANAGER)
    is_admin = (user_role == ROLE_ADMIN)
    is_dispatcher = (user_role == ROLE_DISPATCHER)
    assignable_users = EscalationService.get_assignable_users()
    
    return render_template(
        'manager_escalations.html',
        escalations=escalations,
        kpis=kpis,
        current_status=status_filter,
        current_priority=priority_filter,
        is_manager=is_manager,
        is_admin=is_admin,
        is_dispatcher=is_dispatcher,
        assignable_users=assignable_users
    )

@escalation_bp.route('/<int:escalation_id>', methods=['GET'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def get_escalation(escalation_id):
    escalation = ManagerEscalation.query.get_or_404(escalation_id)
    user_role = normalize_role(current_user.role)
    if not user_can_access_escalation(escalation, current_user) and user_role not in [ROLE_MANAGER, ROLE_ADMIN]:
        abort(403)
    return jsonify(escalation.to_dict())

@escalation_bp.route('/create', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def create():
    data = request.get_json(silent=True) or request.form
    shipment_id = data.get('shipment_id')
    reason = (data.get('reason') or '').strip() or "Operational risk escalation for supervisory review"
    priority = (data.get('priority') or 'HIGH').strip()
    remarks = (data.get('dispatcher_remarks') or data.get('remarks') or '').strip() or None
    exception_id = data.get('exception_id')

    if not shipment_id:
        if request.is_json:
            return jsonify({'error': 'Shipment ID is required.'}), 400
        flash('Shipment ID is required.', 'danger')
        return redirect(request.referrer or url_for('escalation_bp.index'))

    try:
        escalation = EscalationService.create_escalation(
            shipment_id=int(shipment_id),
            reason=reason,
            priority=priority,
            dispatcher_remarks=remarks,
            user=current_user,
            exception_id=int(exception_id) if exception_id else None
        )
        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': f'Shipment escalated to Operations Manager successfully with ID #{escalation.id}.',
                'escalation': escalation.to_dict()
            }), 201
        flash(f'Shipment successfully escalated to Operations Manager (ID #{escalation.id}).', 'success')
        return redirect(url_for('escalation_bp.index'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(f'Failed to escalate shipment: {e}', 'danger')
        return redirect(request.referrer or url_for('escalation_bp.index'))

@escalation_bp.route('/<int:escalation_id>/transition', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER, ROLE_ADMIN)
def transition(escalation_id):
    target_esc = ManagerEscalation.query.get_or_404(escalation_id)
    user_role = normalize_role(current_user.role)
    if not user_can_access_escalation(target_esc, current_user) and user_role not in [ROLE_MANAGER, ROLE_ADMIN]:
        abort(403)

    data = request.get_json(silent=True) or request.form
    new_status = data.get('status')
    remarks = data.get('remarks') or data.get('manager_remarks')
    resolution_notes = data.get('resolution_notes')
    assigned_to_name = data.get('assigned_to_name') or data.get('assigned_to')

    if not new_status:
        if request.is_json:
            return jsonify({'error': 'Target status is required.'}), 400
        flash('Target status is required.', 'danger')
        return redirect(request.referrer or url_for('escalation_bp.index'))

    try:
        escalation = EscalationService.transition_status(
            escalation_id=escalation_id,
            new_status=new_status,
            user=current_user,
            remarks=remarks,
            resolution_notes=resolution_notes,
            assigned_to_name=assigned_to_name
        )
        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': f'Escalation #{escalation_id} successfully transitioned to {new_status}.',
                'escalation': escalation.to_dict()
            })
        flash(f'Escalation #{escalation_id} updated to {new_status}.', 'success')
        return redirect(url_for('escalation_bp.index'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(f'Failed to transition escalation: {e}', 'danger')
        return redirect(request.referrer or url_for('escalation_bp.index'))

@escalation_bp.route('/<int:escalation_id>/update-status', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER)
def update_status(escalation_id):
    target_esc = ManagerEscalation.query.get_or_404(escalation_id)
    user_role = normalize_role(current_user.role)
    if not user_can_access_escalation(target_esc, current_user) and user_role not in [ROLE_MANAGER, ROLE_ADMIN]:
        abort(403)

    data = request.get_json(silent=True) or request.form
    new_status = data.get('status')
    manager_remarks = data.get('manager_remarks') or data.get('remarks')
    resolution_notes = data.get('resolution_notes')

    if not new_status:
        if request.is_json:
            return jsonify({'error': 'Status is required.'}), 400
        flash('Status is required.', 'danger')
        return redirect(request.referrer or url_for('escalation_bp.index'))

    try:
        escalation = EscalationService.update_status(
            escalation_id=escalation_id,
            new_status=new_status,
            user=current_user,
            manager_remarks=manager_remarks,
            resolution_notes=resolution_notes
        )
        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': f'Escalation #{escalation_id} updated to {new_status}.',
                'escalation': escalation.to_dict()
            })
        flash(f'Escalation #{escalation_id} status updated to {new_status}.', 'success')
        return redirect(url_for('escalation_bp.index'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(f'Failed to update status: {e}', 'danger')
        return redirect(request.referrer or url_for('escalation_bp.index'))

@escalation_bp.route('/<int:escalation_id>/assign', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER, ROLE_ADMIN)
def assign(escalation_id):
    target_esc = ManagerEscalation.query.get_or_404(escalation_id)
    user_role = normalize_role(current_user.role)
    if not user_can_access_escalation(target_esc, current_user) and user_role not in [ROLE_MANAGER, ROLE_ADMIN]:
        abort(403)

    data = request.get_json(silent=True) or request.form
    assigned_to_name = data.get('assigned_to_name') or data.get('assigned_to')

    if not assigned_to_name:
        if request.is_json:
            return jsonify({'error': 'Assigned responsibility name is required.'}), 400
        flash('Assigned responsibility name is required.', 'danger')
        return redirect(request.referrer or url_for('escalation_bp.index'))

    try:
        escalation = EscalationService.assign_escalation(
            escalation_id=escalation_id,
            assigned_to_name=assigned_to_name,
            user=current_user
        )
        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': f'Escalation #{escalation_id} assigned to {assigned_to_name}.',
                'escalation': escalation.to_dict()
            })
        flash(f'Escalation #{escalation_id} assigned to {assigned_to_name}.', 'success')
        return redirect(url_for('escalation_bp.index'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(f'Failed to assign escalation: {e}', 'danger')
        return redirect(request.referrer or url_for('escalation_bp.index'))

@escalation_bp.route('/<int:escalation_id>/resolve', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER)
def resolve(escalation_id):
    target_esc = ManagerEscalation.query.get_or_404(escalation_id)
    user_role = normalize_role(current_user.role)
    if not user_can_access_escalation(target_esc, current_user) and user_role not in [ROLE_MANAGER, ROLE_ADMIN]:
        abort(403)

    data = request.get_json(silent=True) or request.form
    resolution_notes = data.get('resolution_notes') or data.get('notes')
    manager_remarks = data.get('manager_remarks')

    if not resolution_notes:
        resolution_notes = 'Issue investigated and operational mitigation successfully closed.'

    try:
        escalation = EscalationService.resolve_escalation(
            escalation_id=escalation_id,
            resolution_notes=resolution_notes,
            user=current_user,
            manager_remarks=manager_remarks
        )
        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': f'Escalation #{escalation_id} resolved successfully.',
                'escalation': escalation.to_dict()
            })
        flash(f'Escalation #{escalation_id} marked as RESOLVED.', 'success')
        return redirect(url_for('escalation_bp.index'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(f'Failed to resolve escalation: {e}', 'danger')
        return redirect(request.referrer or url_for('escalation_bp.index'))
