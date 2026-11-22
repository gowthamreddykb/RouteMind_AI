from extensions import db
from src.models.audit_log_model import AuditLog

class AuditService:
    @staticmethod
    def log(action, entity, entity_id=None, user_id=None, details=None):
        al = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id else None,
            details=details
        )
        db.session.add(al)
        db.session.commit()
        return al
