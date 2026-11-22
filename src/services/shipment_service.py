import datetime as dt
from extensions import db
from src.models.shipment_model import Shipment
from src.models.shipment_event_model import ShipmentEvent

class ShipmentService:
    @staticmethod
    def _apply_user_scope(q, user=None):
        if not user or not getattr(user, 'is_authenticated', False):
            return q
        from src.security.permissions import normalize_role, ROLE_ADMIN, ROLE_MANAGER
        role = normalize_role(getattr(user, 'role', ''))
        if role in [ROLE_ADMIN, ROLE_MANAGER]:
            return q
        return q.filter(
            (Shipment.assigned_to_name == user.username) |
            (Shipment.assigned_to_id == user.id) |
            (Shipment.created_by_id == user.id) |
            (Shipment.created_by_name == user.username) |
            (Shipment.assigned_to_name.is_(None)) |
            (Shipment.assigned_to_name == '')
        )

    @staticmethod
    def get_all(limit=100, risk_level=None, user=None):
        q = Shipment.query
        if user:
            q = ShipmentService._apply_user_scope(q, user)
        if risk_level:
            q = q.filter(Shipment.risk_level == risk_level)
        return q.order_by(Shipment.order_date.desc()).limit(limit).all()

    @staticmethod
    def count_for_user(user=None, risk_level=None, status_in=None):
        q = Shipment.query
        if user:
            q = ShipmentService._apply_user_scope(q, user)
        if risk_level:
            if isinstance(risk_level, list):
                q = q.filter(Shipment.risk_level.in_(risk_level))
            else:
                q = q.filter(Shipment.risk_level == risk_level)
        if status_in:
            q = q.filter(Shipment.order_status.in_(status_in))
        return q.count()

    @staticmethod
    def get_by_id(shipment_id, user=None):
        q = Shipment.query.filter(Shipment.id == shipment_id)
        if user:
            q = ShipmentService._apply_user_scope(q, user)
        return q.first()

    @staticmethod
    def get_by_number(shipment_number, user=None):
        q = Shipment.query.filter(Shipment.shipment_number == shipment_number)
        if user:
            q = ShipmentService._apply_user_scope(q, user)
        return q.first()

    @staticmethod
    def filter_and_paginate(search=None, status=None, vessel=None, risk=None, destination_region=None, page=1, per_page=10, user=None, **kwargs):
        from src.models.customer_model import Customer
        q = Shipment.query.outerjoin(Customer, Shipment.customer_id == Customer.id)
        if user:
            q = ShipmentService._apply_user_scope(q, user)

        dest_reg = destination_region or kwargs.get('destination_region')
        if dest_reg and dest_reg != 'All Regions':
            q = q.filter(Shipment.destination_region.ilike(f"%{dest_reg.strip()}%"))

        if search:
            s_term = f"%{search.strip()}%"
            q = q.filter(
                (Shipment.shipment_number.ilike(s_term)) |
                (Shipment.container_number.ilike(s_term)) |
                (Shipment.vessel_name.ilike(s_term)) |
                (Shipment.origin_port.ilike(s_term)) |
                (Shipment.destination_port.ilike(s_term)) |
                (Shipment.destination_region.ilike(s_term)) |
                (Customer.first_name.ilike(s_term)) |
                (Customer.last_name.ilike(s_term))
            )

        if status and status != 'All Status':
            st_upper = status.strip().upper()
            if st_upper == 'CREATED':
                q = q.filter(Shipment.order_status.in_(['CREATED', 'PENDING', 'ORDER_CREATED']))
            elif st_upper == 'BOOKING_CONFIRMED':
                q = q.filter(Shipment.order_status.in_(['BOOKING_CONFIRMED', 'BOOKED']))
            elif st_upper == 'READY_FOR_DISPATCH':
                q = q.filter(Shipment.order_status.in_(['READY_FOR_DISPATCH', 'READY']))
            elif st_upper == 'IN_TRANSIT':
                q = q.filter(Shipment.order_status.in_(['IN_TRANSIT', 'Ocean In-Transit', 'DELAYED', 'HOLD', 'EXCEPTION_HOLD']))
            elif st_upper == 'ARRIVED_AT_DESTINATION':
                q = q.filter(Shipment.order_status.in_(['ARRIVED_AT_DESTINATION', 'ARRIVED', 'ARRIVED_AT_PORT']))
            elif st_upper == 'DELIVERED':
                q = q.filter(Shipment.order_status.in_(['DELIVERED', 'Delivered to Consignee']))
            elif st_upper == 'COMPLETED':
                q = q.filter(Shipment.order_status == 'COMPLETED')
            else:
                q = q.filter(Shipment.order_status.ilike(f"%{status}%"))

        if vessel and vessel != 'All Vessels':
            q = q.filter(Shipment.vessel_name.ilike(f"%{vessel}%"))

        if risk and risk != 'All Risk Levels':
            if 'high' in risk.lower():
                q = q.filter(Shipment.risk_level.in_(['HIGH', 'CRITICAL', 'CRITICAL_RISK']))
            elif 'medium' in risk.lower() or 'mod' in risk.lower():
                q = q.filter(Shipment.risk_level.in_(['MEDIUM', 'ELEVATED_RISK']))
            elif 'low' in risk.lower() or 'track' in risk.lower():
                q = q.filter(Shipment.risk_level == 'LOW')

        total = q.count()
        items = q.order_by(Shipment.order_date.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    @staticmethod
    def update(shipment_id, data):
        s = Shipment.query.get(shipment_id)
        if not s:
            return None
        valid_cols = {c.name for c in Shipment.__table__.columns if c.name != 'id'}
        for k, v in data.items():
            if k in valid_cols and v != '':
                if k in ['scheduled_days', 'quantity']:
                    try: v = int(v)
                    except: pass
                elif k in ['sales', 'product_price', 'discount_rate']:
                    try: v = float(v)
                    except: pass
                setattr(s, k, v)
        db.session.commit()
        return s

    @staticmethod
    def create(data, user=None):
        import uuid
        from src.services.prediction_service import PredictionService

        # Filter valid model attributes
        valid_cols = {c.name for c in Shipment.__table__.columns}
        filtered = {k: v for k, v in data.items() if k in valid_cols and v != ''}

        if user and getattr(user, 'is_authenticated', False):
            if 'created_by_id' not in filtered:
                filtered['created_by_id'] = user.id
            if 'created_by_name' not in filtered:
                filtered['created_by_name'] = user.username
            if 'assigned_to_name' not in filtered and 'assigned_to' not in filtered:
                from src.security.permissions import ROLE_ADMIN, ROLE_MANAGER, normalize_role
                # Records should never be assigned to Admin and Manager
                if normalize_role(getattr(user, 'role', '')) in [ROLE_ADMIN, ROLE_MANAGER]:
                    from src.services.escalation_service import EscalationService
                    op_user = EscalationService.get_round_robin_user()
                    filtered['assigned_to_name'] = op_user.username if op_user else user.username
                    filtered['assigned_to_id'] = op_user.id if op_user else user.id
                else:
                    filtered['assigned_to_name'] = user.username
                    filtered['assigned_to_id'] = user.id

        # Auto-generate unique shipment number if missing
        if not filtered.get('shipment_number'):
            filtered['shipment_number'] = f"SHP-{uuid.uuid4().hex[:8].upper()}"

        # Safe type conversions
        if 'scheduled_days' in filtered and isinstance(filtered['scheduled_days'], str):
            try: filtered['scheduled_days'] = int(filtered['scheduled_days'])
            except: filtered['scheduled_days'] = 4
        if 'sales' in filtered and isinstance(filtered['sales'], str):
            try: filtered['sales'] = float(filtered['sales'])
            except: filtered['sales'] = 0.0
        if 'quantity' in filtered and isinstance(filtered['quantity'], str):
            try: filtered['quantity'] = int(filtered['quantity'])
            except: filtered['quantity'] = 1

        # Evaluate risk score automatically
        try:
            score_res = PredictionService.score_unified(data)
            if score_res:
                filtered['risk_level'] = score_res.get('overall_risk_level', 'LOW')
                filtered['dock_clearance_status'] = score_res.get('dock_clearance', 'CLEAR_FOR_TRANSIT')
                if score_res.get('order_creation'):
                    filtered['order_creation_prob'] = score_res['order_creation'].get('predicted_probability')
                if score_res.get('dispatch'):
                    filtered['dispatch_prob'] = score_res['dispatch'].get('predicted_probability')
        except Exception:
            pass

        shipment = Shipment(**filtered)
        db.session.add(shipment)
        db.session.commit()
        
        # log initial event
        evt = ShipmentEvent(
            shipment_id=shipment.id,
            event_type='ORDER_CREATED',
            notes='Initial order placed and risk scored in control tower'
        )
        db.session.add(evt)
        db.session.commit()
        return shipment

    @staticmethod
    def update_status(shipment_id, new_status, notes=None, wh_time=None):
        s = Shipment.query.get(shipment_id)
        if s:
            s.order_status = new_status
            evt = ShipmentEvent(
                shipment_id=s.id,
                event_type=new_status,
                warehouse_processing_time=wh_time,
                notes=notes
            )
            db.session.add(evt)
            db.session.commit()
        return s

    @staticmethod
    def get_import_logs(limit=20):
        from src.models.import_log_model import ShipmentImportLog
        return ShipmentImportLog.query.order_by(ShipmentImportLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def import_csv(file_stream, filename, user=None):
        import csv
        import io
        import uuid
        import json
        from src.models.import_log_model import ShipmentImportLog
        from src.services.prediction_service import PredictionService

        if isinstance(file_stream, bytes):
            text = file_stream.decode('utf-8', errors='replace')
            stream = io.StringIO(text)
        elif hasattr(file_stream, 'read'):
            raw = file_stream.read()
            if isinstance(raw, bytes):
                text = raw.decode('utf-8', errors='replace')
            else:
                text = str(raw)
            stream = io.StringIO(text)
        else:
            stream = io.StringIO(str(file_stream))

        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("The uploaded CSV file is empty or missing header columns.")

        # Normalize headers
        normalized_headers = {h.strip().lower(): h for h in reader.fieldnames if h}

        # Check required columns (flexible aliases)
        has_days = any(k in normalized_headers for k in ['days for shipment (scheduled)', 'scheduled_days', 'scheduled days', 'days_scheduled'])
        has_mode = any(k in normalized_headers for k in ['shipping mode', 'shipping_mode', 'mode'])
        has_region = any(k in normalized_headers for k in ['order region', 'destination_region', 'region'])

        if not (has_days and has_mode and has_region):
            missing = []
            if not has_days: missing.append("Days for shipment (scheduled)")
            if not has_mode: missing.append("Shipping Mode")
            if not has_region: missing.append("Order Region / Destination Region")
            raise ValueError(f"CSV missing mandatory operational columns: {', '.join(missing)}")

        total_rows = 0
        success_count = 0
        rejected_count = 0
        errors = []
        created_shipments = []
        seen_numbers = set()

        for idx, row in enumerate(reader, start=2): # line 2 is row 1 of data
            total_rows += 1
            row_clean = {k.strip(): (v.strip() if v else '') for k, v in row.items() if k}

            # Helper to retrieve value by multiple alias candidates
            def get_val(*candidates, default=None):
                for c in candidates:
                    for k, v in row_clean.items():
                        if k.lower() == c.lower() and v != '':
                            return v
                return default

            # 1. Shipment Number / ID
            shp_num = get_val('shipment_id', 'shipment_number', 'order_id', 'order id')
            if shp_num:
                # Check duplicate in current batch
                if shp_num in seen_numbers:
                    rejected_count += 1
                    errors.append({'row': idx, 'error': f"Duplicate shipment number '{shp_num}' within uploaded CSV file."})
                    continue
                # Check duplicate in database
                existing = Shipment.query.filter_by(shipment_number=shp_num).first()
                if existing:
                    rejected_count += 1
                    errors.append({'row': idx, 'error': f"Shipment '{shp_num}' already exists in database (ID: {existing.id})."})
                    continue
                seen_numbers.add(shp_num)
            else:
                shp_num = f"SHP-IMP-{uuid.uuid4().hex[:8].upper()}"
                seen_numbers.add(shp_num)

            # 2. Validate scheduled days
            raw_days = get_val('Days for shipment (scheduled)', 'scheduled_days', 'scheduled days', 'days_scheduled')
            try:
                scheduled_days = int(float(raw_days))
                if scheduled_days < 0 or scheduled_days > 60:
                    raise ValueError(f"Scheduled days must be between 0 and 60 (got {raw_days})")
            except Exception as e:
                rejected_count += 1
                errors.append({'row': idx, 'error': f"Invalid scheduled days: {e}"})
                continue

            # 3. Validate Shipping Mode
            shipping_mode = get_val('Shipping Mode', 'shipping_mode', 'mode', default='Standard Class')
            if not shipping_mode:
                rejected_count += 1
                errors.append({'row': idx, 'error': "Shipping mode cannot be blank."})
                continue

            # 4. Validate Destination Region
            destination_region = get_val('Order Region', 'destination_region', 'region', default='Western Europe')
            if not destination_region:
                rejected_count += 1
                errors.append({'row': idx, 'error': "Destination / Order region cannot be blank."})
                continue

            # 5. Sales & Quantity
            try:
                raw_sales = get_val('Sales', 'sales', default='100.0')
                sales = float(raw_sales)
                if sales < 0: raise ValueError("Sales cannot be negative")
            except Exception as e:
                rejected_count += 1
                errors.append({'row': idx, 'error': f"Invalid sales value: {e}"})
                continue

            try:
                raw_qty = get_val('Quantity', 'order item quantity', 'quantity', default='1')
                quantity = int(float(raw_qty))
                if quantity < 1: raise ValueError("Quantity must be >= 1")
            except Exception as e:
                rejected_count += 1
                errors.append({'row': idx, 'error': f"Invalid quantity value: {e}"})
                continue

            try:
                raw_price = get_val('Order Item Product Price', 'product_price', 'price', default=str(sales))
                product_price = float(raw_price)
            except Exception:
                product_price = sales

            market = get_val('Market', 'market', default='Europe')
            vessel_name = get_val('Vessel Name', 'vessel_name', default='MV Arctic Voyager')
            container_number = get_val('Container Number', 'container_number', default=f"MSKU{uuid.uuid4().hex[:7].upper()}")
            origin_port = get_val('Origin Port', 'origin_port', default='Rotterdam Gateway')
            destination_port = get_val('Destination Port', 'destination_port', default='Hamburg Haven')

            # Optional dock dwell time for Stage 2
            raw_dwell = get_val('Order-to-Ship Time', 'dwell_time', 'warehouse_processing_time')
            dwell_time = None
            if raw_dwell:
                try: dwell_time = float(raw_dwell)
                except: dwell_time = None

            # Prediction score
            pred_data = {
                'Days for shipment (scheduled)': scheduled_days,
                'Order Item Quantity': quantity,
                'Sales': sales,
                'Shipping Mode': shipping_mode,
                'Order Region': destination_region,
                'Market': market,
                'Type': 'DEBIT'
            }
            if dwell_time is not None:
                pred_data['Order-to-Ship Time'] = dwell_time

            risk_level = 'LOW'
            dock_clearance = 'CLEAR_FOR_TRANSIT'
            p1 = None
            p2 = None

            try:
                score_res = PredictionService.score_unified(pred_data)
                if score_res:
                    summary = score_res.get('control_tower_summary', {})
                    risk_level = summary.get('overall_risk_level', 'LOW')
                    dock_clearance = summary.get('recommended_action', 'CLEAR_FOR_TRANSIT')
                    p1 = summary.get('order_creation_probability')
                    p2 = summary.get('dispatch_probability')
            except Exception:
                pass

            user_id = user.id if user and getattr(user, 'is_authenticated', False) else None
            user_name = user.username if user and getattr(user, 'is_authenticated', False) else 'System Dispatcher'

            from src.security.permissions import ROLE_ADMIN, ROLE_MANAGER, normalize_role
            if user and normalize_role(getattr(user, 'role', '')) in [ROLE_ADMIN, ROLE_MANAGER]:
                from src.services.escalation_service import EscalationService
                op_user = EscalationService.get_round_robin_user()
                target_assignee_id = op_user.id if op_user else user_id
                target_assignee_name = op_user.username if op_user else user_name
            else:
                target_assignee_id = user_id
                target_assignee_name = user_name

            shp = Shipment(
                shipment_number=shp_num,
                scheduled_days=scheduled_days,
                shipping_mode=shipping_mode,
                destination_region=destination_region,
                market=market,
                sales=sales,
                quantity=quantity,
                product_price=product_price,
                vessel_name=vessel_name,
                container_number=container_number,
                origin_port=origin_port,
                destination_port=destination_port,
                order_status='IN_TRANSIT',
                risk_level=risk_level,
                dock_clearance_status=dock_clearance,
                order_creation_prob=p1,
                dispatch_prob=p2,
                created_by_id=user_id,
                created_by_name=user_name,
                assigned_to_id=target_assignee_id,
                assigned_to_name=target_assignee_name
            )
            db.session.add(shp)
            db.session.flush()

            evt = ShipmentEvent(
                shipment_id=shp.id,
                event_type='ORDER_CREATED',
                notes=f'Imported from CSV [{filename}] and risk evaluated in Control Tower'
            )
            db.session.add(evt)
            created_shipments.append(shp)
            success_count += 1

        db.session.commit()

        # Record import log
        status_label = 'SUCCESS' if rejected_count == 0 else ('PARTIAL' if success_count > 0 else 'FAILED')
        err_text = json.dumps(errors[:50]) if errors else None

        user_id = user.id if user and getattr(user, 'is_authenticated', False) else None
        user_name = user.username if user and getattr(user, 'is_authenticated', False) else 'System'

        import_log = ShipmentImportLog(
            filename=filename,
            total_rows=total_rows,
            success_count=success_count,
            rejected_count=rejected_count,
            status=status_label,
            error_summary=err_text,
            imported_by_id=user_id,
            imported_by_name=user_name
        )
        db.session.add(import_log)
        db.session.commit()

        return {
            'total_rows': total_rows,
            'success_count': success_count,
            'rejected_count': rejected_count,
            'status': status_label,
            'errors': errors,
            'log_id': import_log.id
        }

    @staticmethod
    def reassign_admin_manager_shipments():
        """Reassign any shipment currently assigned to Admin or Operations Manager to operational specialists."""
        from src.models.user_model import User
        from src.security.permissions import ROLE_ADMIN, ROLE_MANAGER, normalize_role
        from src.services.escalation_service import EscalationService

        assignable = EscalationService.get_assignable_users()
        if not assignable:
            return 0

        admin_manager_names = [u.username for u in User.query.all() if normalize_role(u.role) in [ROLE_ADMIN, ROLE_MANAGER]]
        admin_manager_ids = [u.id for u in User.query.all() if normalize_role(u.role) in [ROLE_ADMIN, ROLE_MANAGER]]

        shipments = Shipment.query.filter(
            (Shipment.assigned_to_id.in_(admin_manager_ids)) |
            (Shipment.assigned_to_name.in_(admin_manager_names))
        ).all()

        for idx, shp in enumerate(shipments):
            target_user = assignable[idx % len(assignable)]
            shp.assigned_to_id = target_user.id
            shp.assigned_to_name = target_user.username
        db.session.commit()
        return len(shipments)
