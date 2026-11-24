import math
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db
from src.services.shipment_service import ShipmentService
from src.services.prediction_service import PredictionService
from src.models.shipment_model import Shipment
from src.models.customer_model import Customer
from src.models.product_model import Product
from src.models.reference_data_model import ReferenceData
from src.models.audit_log_model import AuditLog
from src.security.permissions import (
    roles_required, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, normalize_role
)
import os
from flask import send_file, current_app

shipment_bp = Blueprint('shipment_bp', __name__)

@shipment_bp.route('/sample-csv', methods=['GET'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def download_sample_csv():
    sample_path = os.path.join(current_app.config.get('BASE_DIR', ''), 'data', 'sample', 'sample_shipments.csv')
    if os.path.exists(sample_path):
        return send_file(sample_path, as_attachment=True, download_name='routemind_sample_shipments.csv', mimetype='text/csv')
    return "Sample CSV not found", 404

@shipment_bp.route('/import', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_ADMIN, ROLE_MANAGER)
def import_shipments():
    import_logs = ShipmentService.get_import_logs(limit=20)
    result = None

    if request.method == 'POST':
        uploaded_file = request.files.get('file')
        if not uploaded_file or uploaded_file.filename == '':
            flash('Please select a valid CSV file to upload.', 'danger')
            return redirect(url_for('shipment_bp.import_shipments'))

        if not uploaded_file.filename.lower().endswith('.csv'):
            flash('Invalid file format. Only .csv files are supported.', 'danger')
            return redirect(url_for('shipment_bp.import_shipments'))

        try:
            result = ShipmentService.import_csv(uploaded_file, uploaded_file.filename, user=current_user)

            # Audit log
            audit = AuditLog(
                user_id=current_user.id,
                action='SHIPMENT_CSV_IMPORTED',
                entity='SHIPMENT_IMPORT',
                entity_id=str(result.get('log_id', 0)),
                details=f"CSV import '{uploaded_file.filename}': {result['success_count']} success, {result['rejected_count']} rejected."
            )
            db.session.add(audit)
            db.session.commit()

            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'success', 'result': result})

            if result['rejected_count'] == 0:
                flash(f"Successfully imported {result['success_count']} consignments into the Control Tower database.", 'success')
            elif result['success_count'] > 0:
                flash(f"Partially imported: {result['success_count']} saved, {result['rejected_count']} rejected due to errors.", 'warning')
            else:
                flash(f"Import failed: all {result['rejected_count']} rows contained errors and were rejected.", 'danger')

            import_logs = ShipmentService.get_import_logs(limit=20)
        except Exception as e:
            flash(f"Import process failed: {str(e)}", 'danger')
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': str(e)}), 400

    return render_template('shipment_import.html', import_logs=import_logs, result=result)

def get_pagination_window(page: int, total_pages: int):
    """Generate a clean, bounded pagination window with ellipsis for large page counts."""
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
    pages = [1]
    if page <= 4:
        pages.extend([2, 3, 4, 5])
        pages.append('...')
        pages.append(total_pages)
    elif page >= total_pages - 3:
        pages.append('...')
        pages.extend(list(range(total_pages - 4, total_pages)))
        pages.append(total_pages)
    else:
        pages.append('...')
        pages.extend([page - 1, page, page + 1])
        pages.append('...')
        pages.append(total_pages)
    return pages


@shipment_bp.route('/', methods=['GET'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def list_shipments():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    vessel = request.args.get('vessel', '').strip()
    risk = request.args.get('risk', '').strip()
    destination_region = request.args.get('destination_region', '').strip()
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    per_page = 10

    shipments, filtered_total = ShipmentService.filter_and_paginate(
        search=search, status=status, vessel=vessel, risk=risk, destination_region=destination_region, page=page, per_page=per_page,
        user=current_user
    )

    total_pages = max(1, math.ceil(filtered_total / per_page))
    page_numbers = get_pagination_window(page, total_pages)
    total_db_count = ShipmentService.count_for_user(current_user)
    in_transit_count = ShipmentService.count_for_user(current_user, status_in=['IN_TRANSIT', 'PENDING', 'Ocean In-Transit'])
    high_risk_count = ShipmentService.count_for_user(current_user, risk_level=['HIGH', 'CRITICAL', 'CRITICAL_RISK'])
    delayed_count = ShipmentService.count_for_user(current_user, status_in=['DELAYED', 'HOLD', 'EXCEPTION_HOLD'])

    vessels = [r.label.split(' (')[0] for r in ReferenceData.query.filter_by(category='VESSEL', is_active=True).all()]
    statuses = [r.label for r in ReferenceData.query.filter_by(category='SHIPMENT_STATUS', is_active=True).all()]

    user_role = normalize_role(getattr(current_user, 'role', ''))
    can_create = (user_role in [ROLE_DISPATCHER, ROLE_ADMIN])
    can_edit = (user_role in [ROLE_DISPATCHER, ROLE_ADMIN, ROLE_MANAGER])

    return render_template('shipment_list.html', 
                           shipments=shipments,
                           total_count=filtered_total,
                           total_db_count=total_db_count,
                           in_transit_count=in_transit_count,
                           high_risk_count=high_risk_count,
                           delayed_count=delayed_count,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           page_numbers=page_numbers,
                           search=search,
                           status=status,
                           vessel=vessel,
                           risk=risk,
                           destination_region=destination_region,
                           vessels=vessels,
                           statuses=statuses,
                           can_create=can_create,
                           can_edit=can_edit)

@shipment_bp.route('/new', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_ADMIN, ROLE_MANAGER)
def new_shipment():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form.to_dict()

        # Backend validations
        cust_id = data.get('customer_id')
        dest_reg = data.get('destination_region')
        if not cust_id and not data.get('customer_name'):
            if request.is_json:
                return jsonify({'status': 'error', 'message': 'Customer selection is required.'}), 400
            flash('Validation error: Customer must be specified.', 'danger')
            return redirect(url_for('shipment_bp.new_shipment'))

        s = ShipmentService.create(data, user=current_user)

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action='SHIPMENT_CREATED',
            entity='SHIPMENT',
            entity_id=str(s.id),
            details=f"Consignment {s.shipment_number} ({s.vessel_name or 'Sea Freight'}) created by {current_user.username} ({current_user.role})"
        )
        db.session.add(audit)
        db.session.commit()

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'success', 'shipment': s.to_dict()})
        flash(f"Consignment {s.shipment_number} created and committed to database successfully.", 'success')
        return redirect(f'/shipments/{s.shipment_number}')

    # GET: Load reference datasets from MySQL / SQLite
    customers = Customer.query.order_by(Customer.first_name).all()
    products = Product.query.order_by(Product.product_name).all()
    seaports = ReferenceData.query.filter_by(category='SEAPORT', is_active=True).all()
    vessels = ReferenceData.query.filter_by(category='VESSEL', is_active=True).all()
    container_types = ReferenceData.query.filter_by(category='CONTAINER_TYPE', is_active=True).all()
    shipping_classes = ReferenceData.query.filter_by(category='SHIPPING_CLASS', is_active=True).all()

    return render_template('shipment_form.html',
                           customers=customers,
                           products=products,
                           seaports=seaports,
                           vessels=vessels,
                           container_types=container_types,
                           shipping_classes=shipping_classes,
                           shipment=None)

@shipment_bp.route('/<int:shipment_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_ADMIN, ROLE_MANAGER)
def edit_shipment(shipment_id):
    s = ShipmentService.get_by_id(shipment_id, user=current_user)
    if not s:
        flash("Consignment not found or not assigned to your account.", "warning")
        return redirect(url_for('shipment_bp.list_shipments'))
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form.to_dict()
        updated = ShipmentService.update(shipment_id, data)

        audit = AuditLog(
            user_id=current_user.id,
            action='SHIPMENT_UPDATED',
            entity='SHIPMENT',
            entity_id=str(s.id),
            details=f"Consignment {s.shipment_number} updated by {current_user.username}"
        )
        db.session.add(audit)
        db.session.commit()

        if request.is_json:
            return jsonify({'status': 'success', 'shipment': updated.to_dict()})
        flash(f"Consignment {s.shipment_number} updated successfully.", 'success')
        return redirect(f'/shipments/{s.shipment_number}')

    customers = Customer.query.order_by(Customer.first_name).all()
    products = Product.query.order_by(Product.product_name).all()
    seaports = ReferenceData.query.filter_by(category='SEAPORT', is_active=True).all()
    vessels = ReferenceData.query.filter_by(category='VESSEL', is_active=True).all()
    container_types = ReferenceData.query.filter_by(category='CONTAINER_TYPE', is_active=True).all()
    shipping_classes = ReferenceData.query.filter_by(category='SHIPPING_CLASS', is_active=True).all()

    return render_template('shipment_form.html',
                           customers=customers,
                           products=products,
                           seaports=seaports,
                           vessels=vessels,
                           container_types=container_types,
                           shipping_classes=shipping_classes,
                           shipment=s)

LIFECYCLE_MILESTONES = [
    {
        'step': 1,
        'key': 'CREATED',
        'aliases': ['CREATED', 'ORDER_CREATED', 'PENDING'],
        'default_note': 'Consignment order booked and registered in RouteMind AI.',
        'fraction': 0.00
    },
    {
        'step': 2,
        'key': 'BOOKING_CONFIRMED',
        'aliases': ['BOOKING_CONFIRMED', 'BOOKED'],
        'default_note': 'Maritime carrier booking confirmed & slot allocated.',
        'fraction': 0.12
    },
    {
        'step': 3,
        'key': 'READY_FOR_DISPATCH',
        'aliases': ['READY_FOR_DISPATCH', 'STAGED', 'READY'],
        'default_note': 'Container stuffed, verified, and staged at origin terminal quay.',
        'fraction': 0.25
    },
    {
        'step': 4,
        'key': 'DISPATCHED',
        'aliases': ['DISPATCHED', 'DOCK_DISPATCHED', 'DEPARTED'],
        'default_note': 'Container loaded aboard vessel and departed origin seaport.',
        'fraction': 0.40
    },
    {
        'step': 5,
        'key': 'IN_TRANSIT',
        'aliases': ['IN_TRANSIT', 'TRANSIT', 'OCEAN_TRANSIT', 'Ocean In-Transit'],
        'default_note': 'Vessel steaming along scheduled maritime passage.',
        'fraction': 0.62
    },
    {
        'step': 6,
        'key': 'ARRIVED_AT_DESTINATION',
        'aliases': ['ARRIVED_AT_DESTINATION', 'ARRIVED_AT_DESTINATION_PORT', 'ARRIVED', 'DISCHARGED'],
        'default_note': 'Vessel berthed and container discharged at destination port.',
        'fraction': 0.85
    },
    {
        'step': 7,
        'key': 'OUT_FOR_DELIVERY',
        'aliases': ['OUT_FOR_DELIVERY', 'CUSTOMS_CLEARED', 'DRAYAGE'],
        'default_note': 'Customs release granted & drayage transfer to consignee facility.',
        'fraction': 0.93
    },
    {
        'step': 8,
        'key': 'DELIVERED',
        'aliases': ['DELIVERED'],
        'default_note': 'Cargo delivered and signed off at consignee facility.',
        'fraction': 1.00
    },
    {
        'step': 9,
        'key': 'COMPLETED',
        'aliases': ['COMPLETED', 'CLOSED'],
        'default_note': 'Proof of delivery confirmed and operational lifecycle completed.',
        'fraction': 1.02
    }
]

def get_predicted_delivery_date(shipment):
    """
    Computes the predicted delivery date based on order_date, scheduled transit days,
    and ML delay risk probability / active exception hold duration.
    """
    import datetime as dt
    base_start = getattr(shipment, 'order_date', None) or getattr(shipment, 'created_at', None) or dt.datetime.now(dt.timezone.utc)
    sched_days = getattr(shipment, 'scheduled_days', None) or 4
    
    # ML delay inference adjustment
    prob = getattr(shipment, 'dispatch_prob', None) if getattr(shipment, 'dispatch_prob', None) is not None else getattr(shipment, 'order_creation_prob', None)
    risk = getattr(shipment, 'risk_level', None)
    order_status = getattr(shipment, 'order_status', '')
    
    # Active hold duration from unresolved exceptions
    active_excs = [e for e in getattr(shipment, 'exceptions', []) if e.status not in ['RESOLVED', 'CLOSED']]
    hold_days = len(active_excs) * 1.0
    
    delay_days = 0.0
    if order_status in ['DELAYED', 'HOLD', 'EXCEPTION_HOLD'] or risk in ['HIGH', 'CRITICAL', 'CRITICAL_RISK'] or (prob is not None and prob >= 0.50):
        delay_days = 1.5 + hold_days
    elif hold_days > 0:
        delay_days = hold_days

    if getattr(shipment, 'expected_arrival', None):
        return shipment.expected_arrival + dt.timedelta(days=delay_days)
        
    return base_start + dt.timedelta(days=sched_days + delay_days)

def build_milestone_cycle(shipment):
    import datetime as dt
    norm_status = str(getattr(shipment, 'order_status', '') or '').strip().upper().replace(' ', '_').replace('-', '_')
    
    current_step = 1
    found_step = False
    for m in LIFECYCLE_MILESTONES:
        for alias in m['aliases']:
            if norm_status == alias.upper():
                current_step = m['step']
                found_step = True
                break
        if found_step:
            break
            
    if not found_step:
        if 'TRANSIT' in norm_status:
            current_step = 5
        elif 'DISPATCH' in norm_status or 'DEPART' in norm_status:
            current_step = 4
        elif 'DELIVER' in norm_status:
            current_step = 8
        elif 'COMPLETE' in norm_status:
            current_step = 9

    # Calculate predicted delivery date and transit timeline
    base_start = getattr(shipment, 'order_date', None) or getattr(shipment, 'created_at', None) or dt.datetime.now(dt.timezone.utc)
    pred_delivery = get_predicted_delivery_date(shipment)
    total_transit = pred_delivery - base_start
    if total_transit.total_seconds() <= 0:
        total_transit = dt.timedelta(days=getattr(shipment, 'scheduled_days', None) or 4)
    
    events = getattr(shipment, 'events', []) or []
    event_map = {}
    for ev in events:
        ev_type = str(getattr(ev, 'event_type', '') or '').strip().upper().replace(' ', '_').replace('-', '_')
        if ev_type not in event_map:
            event_map[ev_type] = ev
            
    cycle = []
    for m in LIFECYCLE_MILESTONES:
        step = m['step']
        key = m['key']
        frac = m.get('fraction', 0.0)

        # Calculate milestone expected timestamp along predicted delivery schedule
        step_dt = base_start + dt.timedelta(seconds=total_transit.total_seconds() * frac)
        step_dt_str = step_dt.strftime('%d %b %H:%M')
        
        matched_ev = None
        for alias in m['aliases']:
            if alias.upper() in event_map:
                matched_ev = event_map[alias.upper()]
                break
                
        if current_step == 9:
            state = 'done'
        elif step < current_step:
            state = 'done'
        elif step == current_step:
            state = 'current'
        else:
            state = 'pending'
            
        if state == 'done':
            if matched_ev and matched_ev.event_timestamp:
                ts = matched_ev.event_timestamp.strftime('%d %b %H:%M')
                note = matched_ev.notes or m['default_note']
            else:
                ts = step_dt_str
                note = m['default_note']
        elif state == 'current':
            if matched_ev and matched_ev.event_timestamp:
                ts = matched_ev.event_timestamp.strftime('%d %b %H:%M')
            else:
                ts = 'Active Stage'
            note = (matched_ev.notes if matched_ev and matched_ev.notes else m['default_note'])
        else:
            # Pending upcoming stages dynamically update based on predicted delivery date!
            # Never show stale old test events or completed POD notes on upcoming stages
            ts = f"Est. {step_dt_str}"
            note = m['default_note']
            
        cycle.append({
            'step': step,
            'key': key,
            'state': state,
            'timestamp': ts,
            'notes': note,
            'estimated_time': step_dt
        })
        
    return cycle

@shipment_bp.route('/<identifier>')
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def shipment_detail(identifier):
    s = None
    if identifier.isdigit():
        s = ShipmentService.get_by_id(int(identifier), user=current_user)
    if not s:
        s = ShipmentService.get_by_number(identifier, user=current_user)
    if not s:
        user_list = ShipmentService.get_all(limit=1, user=current_user)
        s = user_list[0] if user_list else None

    if not s:
        flash("Consignment not found or not assigned to your account.", "warning")
        return redirect(url_for('shipment_bp.list_shipments'))

    user_role = normalize_role(getattr(current_user, 'role', ''))
    can_edit = (user_role in [ROLE_DISPATCHER, ROLE_ADMIN, ROLE_MANAGER])
    pred_delivery = get_predicted_delivery_date(s)
    milestone_cycle = build_milestone_cycle(s)

    # CatBoost Model 03 Delay Estimation
    from src.delay_prediction import predict_delay_api
    delay_res = predict_delay_api({
        'Days for shipment (scheduled)': s.scheduled_days or 4.0,
        'Order-to-Ship Time': getattr(s, 'warehouse_processing_time_days', 2.0) or 2.0,
        'Shipping Mode': s.shipping_mode or 'Standard Class',
        'Customer Segment': 'Consumer',
        'Order Region': s.destination_region or 'Western Europe'
    }, shipment_id=s.shipment_number)

    # SHAP feature explanations
    shap_features = []
    try:
        order_features = PredictionService.extract_order_creation_features_from_shipment(s)
        order_res = PredictionService.score_order_creation(order_features, shipment_id=s.id)
        raw_factors = order_res.get('top_risk_factors', [])
        for f in raw_factors:
            contrib = float(f.get('shap_contribution', 0.0))
            shap_features.append({
                'name': f.get('feature', 'Feature'),
                'value': str(f.get('feature_value', '')),
                'impact': f"{'+' if contrib >= 0 else ''}{contrib:.2f}",
                'direction': 'positive' if contrib >= 0 else 'negative',
                'weight_pct': min(100, max(15, int(abs(contrib) * 200)))
            })
    except Exception:
        pass

    return render_template(
        'shipment_detail.html',
        shipment=s,
        can_edit=can_edit,
        milestone_cycle=milestone_cycle,
        predicted_delivery_date=pred_delivery,
        delay_res=delay_res,
        shap_features=shap_features
    )

@shipment_bp.route('/<int:shipment_id>/update-status', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def update_shipment_status(shipment_id):
    s = ShipmentService.get_by_id(shipment_id, user=current_user)
    if not s:
        flash("Consignment not found or unauthorized.", "danger")
        return redirect(url_for('shipment_bp.list_shipments'))

    new_status = request.form.get('status') or (request.json.get('status') if request.is_json else None)
    notes = request.form.get('notes') or (request.json.get('notes') if request.is_json else None)

    if not new_status:
        if request.is_json:
            return jsonify({'status': 'error', 'message': 'Status is required'}), 400
        flash("Milestone status is required.", "warning")
        return redirect(url_for('shipment_bp.shipment_detail', identifier=shipment_id))

    ShipmentService.update_status(shipment_id, new_status, notes=notes)

    if request.is_json:
        return jsonify({'status': 'success', 'new_status': new_status})
    flash(f"Consignment milestone status updated to {new_status}.", "success")
    return redirect(url_for('shipment_bp.shipment_detail', identifier=shipment_id))

@shipment_bp.route('/<int:shipment_id>/confirm-delivery', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def confirm_delivery(shipment_id):
    import datetime as dt
    from src.models.shipment_event_model import ShipmentEvent
    s = ShipmentService.get_by_id(shipment_id, user=current_user)
    if not s:
        flash("Consignment not found or unauthorized.", "danger")
        return redirect(url_for('shipment_bp.list_shipments'))

    ref = request.form.get('delivery_confirmation_ref') or f"POD-{s.shipment_number[-6:]}"
    notes = request.form.get('notes') or "Cargo safely discharged and delivered at consignee facility."

    s.order_status = 'DELIVERED'
    s.actual_arrival = dt.datetime.now(dt.timezone.utc)

    evt = ShipmentEvent(
        shipment_id=s.id,
        event_type='DELIVERED',
        notes=f"Delivery confirmed with Ref: {ref}. {notes}"
    )
    db.session.add(evt)

    audit = AuditLog(
        user_id=current_user.id,
        action='DELIVERY_CONFIRMED',
        entity='SHIPMENT',
        entity_id=str(s.id),
        details=f"Delivery confirmed by {current_user.username} with Ref: {ref}"
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Delivery successfully confirmed for {s.shipment_number}.", "success")
    return redirect(url_for('shipment_bp.shipment_detail', identifier=shipment_id))

@shipment_bp.route('/<int:shipment_id>/complete', methods=['POST'])
@login_required
@roles_required(ROLE_MANAGER, ROLE_ADMIN)
def complete_shipment(shipment_id):
    from src.models.shipment_event_model import ShipmentEvent
    s = ShipmentService.get_by_id(shipment_id, user=current_user)
    if not s:
        flash("Consignment not found or unauthorized.", "danger")
        return redirect(url_for('shipment_bp.list_shipments'))

    # Check 1: Delivery must be confirmed first
    if s.order_status not in ['DELIVERED', 'COMPLETED']:
        flash(f"Cannot complete consignment: Consignment must be in 'DELIVERED' status first (currently: {s.order_status}).", "warning")
        return redirect(url_for('shipment_bp.shipment_detail', identifier=shipment_id))

    # Check 2: All exceptions must be resolved or closed
    open_exceptions = [ex for ex in s.exceptions if ex.status not in ['RESOLVED', 'CLOSED']]
    if open_exceptions:
        ex_refs = ", ".join([f"EXC-{ex.id:04d}" for ex in open_exceptions])
        flash(f"Cannot complete consignment: Open exceptions remaining ({ex_refs}). All exceptions must be resolved or closed prior to completion.", "danger")
        return redirect(url_for('shipment_bp.shipment_detail', identifier=shipment_id))

    s.order_status = 'COMPLETED'
    evt = ShipmentEvent(
        shipment_id=s.id,
        event_type='COMPLETED',
        notes="Lifecycle audit verified and consignment closed."
    )
    db.session.add(evt)

    audit = AuditLog(
        user_id=current_user.id,
        action='SHIPMENT_COMPLETED',
        entity='SHIPMENT',
        entity_id=str(s.id),
        details=f"Consignment completed and lifecycle closed by {current_user.username}"
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Consignment {s.shipment_number} successfully completed and closed.", "success")
    return redirect(url_for('shipment_bp.shipment_detail', identifier=shipment_id))

@shipment_bp.route('/api/predict', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN)
def api_predict():
    payload = request.get_json(silent=True) or {}
    res = PredictionService.score_unified(payload, payload.get('shipment_id'))
    return jsonify(res)

