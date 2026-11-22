from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db
from src.models.user_model import User
from src.models.audit_log_model import AuditLog
from src.services.auth_service import AuthService
from src.security.permissions import roles_required, ROLE_ADMIN, normalize_role, ALL_ROLES

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/')
@login_required
@roles_required(ROLE_ADMIN)
def users():
    role_filter = request.args.get('role')
    status_filter = request.args.get('status')
    query = User.query

    if role_filter:
        query = query.filter_by(role=normalize_role(role_filter))
    if status_filter:
        is_act = (status_filter.lower() == 'active')
        query = query.filter_by(is_active=is_act)

    user_list = query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=user_list, current_role_filter=role_filter, current_status_filter=status_filter)

@user_bp.route('/new', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_ADMIN)
def new_user():
    if request.method == 'POST':
        data = request.form
        full_name = data.get('full_name', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        role = normalize_role(data.get('role', 'Dispatcher'))
        is_active = (data.get('status', 'active').lower() == 'active')

        # Validation
        if not username or not email or not password:
            flash('All required fields must be provided.', 'danger')
            return render_template('user_form.html', roles=ALL_ROLES)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('user_form.html', roles=ALL_ROLES)

        if role not in ALL_ROLES:
            flash('Invalid role selected. Only approved enterprise roles are permitted.', 'danger')
            return render_template('user_form.html', roles=ALL_ROLES)

        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" is already taken.', 'danger')
            return render_template('user_form.html', roles=ALL_ROLES)

        if User.query.filter_by(email=email).first():
            flash(f'Email "{email}" is already registered.', 'danger')
            return render_template('user_form.html', roles=ALL_ROLES)

        user = User(
            full_name=full_name or username.title(),
            username=username,
            email=email,
            role=role,
            is_active=is_active
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action='USER_CREATED',
            entity='USER',
            entity_id=str(user.id),
            details=f"Created user {user.username} with role {user.role}"
        )
        db.session.add(audit)
        db.session.commit()

        flash(f'User {user.username} created successfully with role {user.role}.', 'success')
        return redirect(url_for('user_bp.users'))

    return render_template('user_form.html', user=None, roles=ALL_ROLES)

@user_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_ADMIN)
def edit_user(user_id):
    target_user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        data = request.form
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        role = normalize_role(data.get('role', target_user.role))
        is_active = (data.get('status', 'active').lower() == 'active')

        if role not in ALL_ROLES:
            flash('Invalid role selection.', 'danger')
            return render_template('user_form.html', user=target_user, roles=ALL_ROLES)

        # Check duplicate email
        existing = User.query.filter(User.email == email, User.id != user_id).first()
        if existing:
            flash('Email already used by another account.', 'danger')
            return render_template('user_form.html', user=target_user, roles=ALL_ROLES)

        # Prevent admin deactivating self
        if target_user.id == current_user.id and not is_active:
            flash('Administrators cannot deactivate their own account.', 'warning')
            is_active = True

        # Prevent deactivating or demoting the last active Administrator
        if target_user.role in [ROLE_ADMIN, 'ADMIN'] and (not is_active or role != ROLE_ADMIN):
            active_admin_count = User.query.filter(User.role.in_([ROLE_ADMIN, 'ADMIN']), User.is_active == True).count()
            if active_admin_count <= 1:
                flash('Cannot deactivate or reassign the sole active system Administrator.', 'danger')
                return render_template('user_form.html', user=target_user, roles=ALL_ROLES)

        target_user.full_name = full_name or target_user.username.title()
        target_user.email = email
        target_user.role = role
        target_user.is_active = is_active

        new_password = data.get('password', '').strip()
        if new_password:
            target_user.set_password(new_password)

        db.session.commit()

        audit = AuditLog(
            user_id=current_user.id,
            action='USER_UPDATED',
            entity='USER',
            entity_id=str(target_user.id),
            details=f"Updated user {target_user.username}: role={target_user.role}, active={target_user.is_active}"
        )
        db.session.add(audit)
        db.session.commit()

        flash(f'User {target_user.username} updated successfully.', 'success')
        return redirect(url_for('user_bp.users'))

    return render_template('user_form.html', user=target_user, roles=ALL_ROLES)

@user_bp.route('/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@roles_required(ROLE_ADMIN)
def toggle_user_status(user_id):
    target_user = User.query.get_or_404(user_id)
    if target_user.id == current_user.id:
        if request.is_json:
            return jsonify({'error': 'Cannot deactivate own administrative account'}), 400
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('user_bp.users'))

    # Prevent deactivating the last active Administrator
    if target_user.role in [ROLE_ADMIN, 'ADMIN'] and target_user.is_active:
        active_admin_count = User.query.filter(User.role.in_([ROLE_ADMIN, 'ADMIN']), User.is_active == True).count()
        if active_admin_count <= 1:
            if request.is_json:
                return jsonify({'error': 'Cannot deactivate the sole active system Administrator.'}), 400
            flash('Cannot deactivate the sole active system Administrator.', 'danger')
            return redirect(url_for('user_bp.users'))

    target_user.is_active = not target_user.is_active
    db.session.commit()

    audit = AuditLog(
        user_id=current_user.id,
        action='USER_STATUS_TOGGLED',
        entity='USER',
        entity_id=str(target_user.id),
        details=f"Status set to {target_user.is_active}"
    )
    db.session.add(audit)
    db.session.commit()

    status_str = "activated" if target_user.is_active else "deactivated"
    if request.is_json:
        return jsonify({'status': 'success', 'user_id': user_id, 'is_active': target_user.is_active})
    flash(f"User {target_user.username} {status_str}.", 'info')
    return redirect(url_for('user_bp.users'))

