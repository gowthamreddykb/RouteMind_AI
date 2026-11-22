from extensions import db
from src.models.communication_model import CommunicationLog

class CommunicationService:
    @staticmethod
    def log_communication(shipment_id, recipient, channel, subject, body, prompt_version='v1.0.0'):
        c = CommunicationLog(
            shipment_id=shipment_id,
            recipient=recipient,
            channel=channel,
            subject=subject,
            message_body=body,
            prompt_version=prompt_version or 'v1.0.0'
        )
        db.session.add(c)
        db.session.commit()
        return c

    @staticmethod
    def get_recent(limit=50):
        return CommunicationLog.query.order_by(CommunicationLog.sent_at.desc()).limit(limit).all()
