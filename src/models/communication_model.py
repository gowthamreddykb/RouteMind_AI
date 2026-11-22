import datetime as dt
from extensions import db

class CommunicationLog(db.Model):
    __tablename__ = 'communication_logs'
    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipments.id'), nullable=True)
    recipient = db.Column(db.String(120), nullable=False)
    channel = db.Column(db.String(50), default='EMAIL')
    subject = db.Column(db.String(255), nullable=True)
    message_body = db.Column(db.Text, nullable=False)
    prompt_version = db.Column(db.String(50), nullable=False, default='v1.0.0')
    sent_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'shipment_id': self.shipment_id,
            'recipient': self.recipient,
            'channel': self.channel,
            'subject': self.subject,
            'prompt_version': self.prompt_version,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }

# Model alias for BRD compliance
Communication = CommunicationLog
