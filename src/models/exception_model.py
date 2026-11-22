import datetime as dt
from extensions import db

class ShipmentException(db.Model):
    __tablename__ = 'shipment_exceptions'
    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipments.id'), nullable=False)
    exception_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), default='MEDIUM')
    status = db.Column(db.String(30), default='OPEN')
    assigned_to = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    actions = db.relationship('ExceptionAction', backref='exception', lazy=True, order_by='ExceptionAction.action_timestamp.desc()')

    def to_dict(self):
        return {
            'id': self.id,
            'shipment_id': self.shipment_id,
            'exception_type': self.exception_type,
            'severity': self.severity,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'actions': [a.to_dict() for a in self.actions] if self.actions else []
        }

ExceptionRecord = ShipmentException

