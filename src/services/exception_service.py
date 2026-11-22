import datetime as dt
from extensions import db
from src.models.exception_model import ShipmentException
from src.models.exception_action_model import ExceptionAction

class ExceptionService:
    @staticmethod
    def get_assignable_users():
        """Get active operational users, strictly excluding Admin and Operations Manager roles."""
        from src.models.user_model import User
        from src.security.permissions import ROLE_ADMIN, ROLE_MANAGER, normalize_role
        active_users = User.query.filter_by(is_active=True).order_by(User.id).all()
        assignable = [u for u in active_users if normalize_role(u.role) not in [ROLE_ADMIN, ROLE_MANAGER]]
        return assignable if assignable else active_users

    @staticmethod
    def get_round_robin_user():
        assignable = ExceptionService.get_assignable_users()
        if not assignable:
            return None
        total_count = ShipmentException.query.count()
        return assignable[total_count % len(assignable)]

    @staticmethod
    def reassign_all_round_robin():
        """Reassign all exceptions in the system to operational users (excluding Admin and Manager) using round-robin."""
        assignable = ExceptionService.get_assignable_users()
        if not assignable:
            return 0

        exceptions = ShipmentException.query.order_by(ShipmentException.id.asc()).all()
        for idx, ex in enumerate(exceptions):
            target_user = assignable[idx % len(assignable)]
            ex.assigned_to = target_user.username
            act = ExceptionAction(
                exception_id=ex.id,
                action_taken=f"Assigned to operational specialist {target_user.username} via round-robin distribution.",
                taken_by="System (Round-Robin)"
            )
            db.session.add(act)
        db.session.commit()
        return len(exceptions)

    @staticmethod
    def get_all(status=None):
        q = ShipmentException.query
        if status:
            q = q.filter_by(status=status)
        return q.order_by(ShipmentException.created_at.desc()).all()

    @staticmethod
    def create(shipment_id, exception_type, severity='MEDIUM', assigned_to=None):
        if not assigned_to:
            user = ExceptionService.get_round_robin_user()
            if user:
                assigned_to = user.username

        ex = ShipmentException(
            shipment_id=shipment_id,
            exception_type=exception_type,
            severity=severity,
            assigned_to=assigned_to
        )
        db.session.add(ex)
        db.session.commit()

        if assigned_to:
            act = ExceptionAction(
                exception_id=ex.id,
                action_taken=f"Auto-assigned to {assigned_to} via round-robin dispatch.",
                taken_by="System (Round-Robin)"
            )
            db.session.add(act)
            db.session.commit()

        return ex

    @staticmethod
    def add_action(exception_id, action_taken, taken_by):
        act = ExceptionAction(
            exception_id=exception_id,
            action_taken=action_taken,
            taken_by=taken_by
        )
        db.session.add(act)
        db.session.commit()
        return act
