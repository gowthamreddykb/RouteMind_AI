import datetime as dt
from extensions import db
from src.models.escalation_model import ManagerEscalation, EscalationHistory
from src.models.shipment_model import Shipment
from src.models.audit_log_model import AuditLog

class EscalationService:

    @staticmethod
    def get_assignable_users():
        """Get active operational users, strictly excluding Admin and Operations Manager roles."""
        from src.models.user_model import User
        from src.security.permissions import ROLE_ADMIN, ROLE_MANAGER, normalize_role
        active_users = User.query.filter_by(is_active=True).order_by(User.id).all()
        # Strictly exclude Admin and Manager roles from record assignments
        assignable = [u for u in active_users if normalize_role(u.role) not in [ROLE_ADMIN, ROLE_MANAGER]]
        return assignable if assignable else active_users

    @staticmethod
    def get_round_robin_user():
        assignable = EscalationService.get_assignable_users()
        if not assignable:
            return None
        total_count = ManagerEscalation.query.count()
        return assignable[total_count % len(assignable)]

    @staticmethod
    def reassign_all_round_robin():
        """Reassign all escalations in the system to operational users (excluding Admin and Manager) using round-robin."""
        assignable = EscalationService.get_assignable_users()
        if not assignable:
            return 0

        escalations = ManagerEscalation.query.order_by(ManagerEscalation.id.asc()).all()
        for idx, esc in enumerate(escalations):
            target_user = assignable[idx % len(assignable)]
            esc.assigned_to_id = target_user.id
            esc.assigned_to_name = target_user.full_name or target_user.username
            
            # Record audit / history
            history = EscalationHistory(
                escalation_id=esc.id,
                action='ASSIGNED',
                performed_by='System (Round-Robin)',
                notes=f"Assigned to operational specialist {esc.assigned_to_name} via round-robin distribution."
            )
            db.session.add(history)
        db.session.commit()
        return len(escalations)

    @staticmethod
    def create_escalation(shipment_id, reason, priority='MEDIUM', dispatcher_remarks=None, user=None, exception_id=None):
        shipment = Shipment.query.get(shipment_id)
        if not shipment:
            raise ValueError(f"Shipment with ID {shipment_id} does not exist.")

        risk_score = float(getattr(shipment, 'risk_score', None) or getattr(shipment, 'dispatch_prob', None) or getattr(shipment, 'order_creation_prob', None) or 0.25)

        # Normalize priority
        priority = (priority or 'MEDIUM').strip().upper()
        if priority not in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            priority = 'MEDIUM'

        username = user.username if user else 'System Dispatcher'
        user_id = user.id if user else None

        # Round-robin assignment across all active enterprise users
        assigned_user = EscalationService.get_round_robin_user()
        assigned_to_id = assigned_user.id if assigned_user else None
        assigned_to_name = (assigned_user.full_name or assigned_user.username) if assigned_user else None

        escalation = ManagerEscalation(
            shipment_id=shipment.id,
            exception_id=exception_id,
            priority=priority,
            reason=reason.strip(),
            dispatcher_remarks=dispatcher_remarks.strip() if dispatcher_remarks else None,
            risk_score=risk_score,
            escalated_by_id=user_id,
            escalated_by_name=username,
            assigned_to_id=assigned_to_id,
            assigned_to_name=assigned_to_name,
            status='PENDING'
        )
        db.session.add(escalation)
        db.session.flush()

        history = EscalationHistory(
            escalation_id=escalation.id,
            action='ESCALATED',
            performed_by=username,
            notes=f"Escalated to Operations Manager with priority [{priority}]. Reason: {reason}"
        )
        db.session.add(history)

        if assigned_to_name:
            assign_hist = EscalationHistory(
                escalation_id=escalation.id,
                action='ASSIGNED',
                performed_by='System (Round-Robin)',
                notes=f"Auto-assigned to {assigned_to_name} via round-robin dispatch."
            )
            db.session.add(assign_hist)

        audit = AuditLog(
            user_id=user_id,
            action='SHIPMENT_ESCALATED_TO_MANAGER',
            entity='MANAGER_ESCALATION',
            entity_id=str(escalation.id),
            details=f"Consignment {shipment.shipment_identifier} (ID: {shipment.id}) escalated with priority {priority} by {username}. Assigned to {assigned_to_name}."
        )
        db.session.add(audit)
        db.session.commit()
        return escalation

    # Defined lifecycle state machine:
    # PENDING -> UNDER_REVIEW -> IN_PROGRESS -> RESOLVED
    # Reopen: RESOLVED -> UNDER_REVIEW
    ESC_FLOW = {
        'PENDING': ['UNDER_REVIEW', 'RESOLVED'],
        'UNDER_REVIEW': ['IN_PROGRESS', 'RESOLVED', 'PENDING'],
        'IN_PROGRESS': ['RESOLVED', 'UNDER_REVIEW'],
        'RESOLVED': ['UNDER_REVIEW', 'IN_PROGRESS']
    }

    @staticmethod
    def transition_status(escalation_id, new_status, user, remarks=None, resolution_notes=None, assigned_to_name=None):
        """Execute a validated lifecycle state transition from PENDING -> UNDER_REVIEW -> IN_PROGRESS -> RESOLVED."""
        escalation = ManagerEscalation.query.get(escalation_id)
        if not escalation:
            raise ValueError(f"Escalation #{escalation_id} not found.")

        new_status = (new_status or '').strip().upper()
        if new_status not in ['PENDING', 'UNDER_REVIEW', 'IN_PROGRESS', 'RESOLVED']:
            raise ValueError(f"Invalid escalation status: {new_status}")

        old_status = escalation.status
        if old_status != new_status:
            allowed = EscalationService.ESC_FLOW.get(old_status, ['PENDING', 'UNDER_REVIEW', 'IN_PROGRESS', 'RESOLVED'])
            if new_status not in allowed:
                raise ValueError(f"Invalid lifecycle progression from {old_status} to {new_status}. Allowed transitions: {', '.join(allowed)}")

        escalation.status = new_status
        username = (getattr(user, 'username', None) or getattr(user, 'full_name', None) or 'Operational Specialist')

        if remarks:
            escalation.manager_remarks = remarks.strip()

        # Handle Assigned Specialist if provided
        if assigned_to_name and assigned_to_name.strip():
            from src.models.user_model import User
            name_val = assigned_to_name.strip()
            target_u = User.query.filter((User.username.ilike(name_val)) | (User.full_name.ilike(name_val))).first()
            if target_u:
                escalation.assigned_to_id = target_u.id
                escalation.assigned_to_name = target_u.full_name or target_u.username
            else:
                escalation.assigned_to_name = name_val

        # Handle RESOLVED lifecycle stage
        if new_status == 'RESOLVED':
            escalation.resolved_at = dt.datetime.now(dt.timezone.utc)
            escalation.resolution_notes = (resolution_notes or remarks or escalation.resolution_notes or 'Issue investigated and operational mitigation successfully closed.').strip()
            # If linked to an open shipment exception, synchronize and resolve it as well
            if escalation.exception_id:
                from src.models.exception_model import ShipmentException
                exc = ShipmentException.query.get(escalation.exception_id)
                if exc and exc.status != 'RESOLVED':
                    exc.status = 'RESOLVED'
        elif old_status == 'RESOLVED' and new_status != 'RESOLVED':
            # Reopening escalation
            escalation.resolved_at = None

        # Build descriptive history note
        action_name = 'RESOLVED' if new_status == 'RESOLVED' else ('REOPENED' if old_status == 'RESOLVED' else 'LIFECYCLE_TRANSITION')
        note_parts = [f"Status changed from {old_status} to {new_status}."]
        if remarks:
            note_parts.append(f"Remarks: {remarks.strip()}")
        if new_status == 'RESOLVED' and escalation.resolution_notes:
            note_parts.append(f"Resolution: {escalation.resolution_notes}")
        if assigned_to_name:
            note_parts.append(f"Assigned to: {escalation.assigned_to_name}")

        history = EscalationHistory(
            escalation_id=escalation.id,
            action=action_name,
            performed_by=username,
            notes=' '.join(note_parts)
        )
        db.session.add(history)

        audit = AuditLog(
            user_id=getattr(user, 'id', None),
            action=f"ESCALATION_{action_name}",
            entity='MANAGER_ESCALATION',
            entity_id=str(escalation.id),
            details=f"Escalation #{escalation.id} transitioned from {old_status} to {new_status} by {username}."
        )
        db.session.add(audit)
        db.session.commit()
        return escalation

    @staticmethod
    def update_status(escalation_id, new_status, user, manager_remarks=None, resolution_notes=None):
        return EscalationService.transition_status(
            escalation_id=escalation_id,
            new_status=new_status,
            user=user,
            remarks=manager_remarks,
            resolution_notes=resolution_notes
        )

    @staticmethod
    def assign_escalation(escalation_id, assigned_to_name, user):
        return EscalationService.transition_status(
            escalation_id=escalation_id,
            new_status='UNDER_REVIEW',
            user=user,
            assigned_to_name=assigned_to_name
        )

    @staticmethod
    def resolve_escalation(escalation_id, resolution_notes, user, manager_remarks=None):
        return EscalationService.transition_status(
            escalation_id=escalation_id,
            new_status='RESOLVED',
            user=user,
            remarks=manager_remarks,
            resolution_notes=resolution_notes
        )

    @staticmethod
    def _apply_user_filter(query, user=None):
        """Filter escalations so users only see escalations assigned to them or created by them."""
        if not user or not getattr(user, 'is_authenticated', True):
            return query

        from sqlalchemy import or_
        user_filters = []
        user_id = getattr(user, 'id', None)
        username = getattr(user, 'username', None)
        full_name = getattr(user, 'full_name', None)
        email = getattr(user, 'email', None)

        if user_id:
            user_filters.append(ManagerEscalation.escalated_by_id == user_id)
            user_filters.append(ManagerEscalation.assigned_to_id == user_id)
        if username:
            user_filters.append(ManagerEscalation.escalated_by_name.ilike(username))
            user_filters.append(ManagerEscalation.assigned_to_name.ilike(username))
        if full_name:
            user_filters.append(ManagerEscalation.escalated_by_name.ilike(full_name))
            user_filters.append(ManagerEscalation.assigned_to_name.ilike(full_name))
        if email:
            user_filters.append(ManagerEscalation.escalated_by_name.ilike(email))
            user_filters.append(ManagerEscalation.assigned_to_name.ilike(email))

        if user_filters:
            query = query.filter(or_(*user_filters))
        return query

    @staticmethod
    def get_escalations(status=None, priority=None, limit=200, user=None):
        query = ManagerEscalation.query
        query = EscalationService._apply_user_filter(query, user)
        if status:
            query = query.filter(ManagerEscalation.status == status.upper())
        if priority:
            query = query.filter(ManagerEscalation.priority == priority.upper())
        return query.order_by(ManagerEscalation.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_kpis(user=None):
        base_query = EscalationService._apply_user_filter(ManagerEscalation.query, user)
        total = base_query.count()
        pending = base_query.filter(ManagerEscalation.status == 'PENDING').count()
        under_review = base_query.filter(ManagerEscalation.status == 'UNDER_REVIEW').count()
        in_progress = base_query.filter(ManagerEscalation.status == 'IN_PROGRESS').count()
        resolved = base_query.filter(ManagerEscalation.status == 'RESOLVED').count()
        return {
            'total': total,
            'pending': pending,
            'under_review': under_review,
            'in_progress': in_progress,
            'active': pending + under_review + in_progress,
            'resolved': resolved
        }
