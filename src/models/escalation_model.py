import datetime as dt
from extensions import db

class ManagerEscalation(db.Model):
    __tablename__ = 'manager_escalations'

    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipments.id'), nullable=False, index=True)
    exception_id = db.Column(db.Integer, db.ForeignKey('shipment_exceptions.id'), nullable=True)
    priority = db.Column(db.String(20), default='MEDIUM', nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    reason = db.Column(db.String(255), nullable=False)
    dispatcher_remarks = db.Column(db.Text, nullable=True)
    risk_score = db.Column(db.Float, default=0.0, nullable=True)
    escalated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    escalated_by_name = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(30), default='PENDING', nullable=False)  # PENDING, UNDER_REVIEW, IN_PROGRESS, RESOLVED
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_to_name = db.Column(db.String(80), nullable=True)
    manager_remarks = db.Column(db.Text, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc), onupdate=lambda: dt.datetime.now(dt.timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    shipment = db.relationship('Shipment', backref=db.backref('escalations', lazy='dynamic', cascade='all, delete-orphan'))
    exception = db.relationship('ShipmentException', backref=db.backref('escalations', lazy='dynamic'))
    history = db.relationship('EscalationHistory', backref='escalation', cascade='all, delete-orphan', order_by='EscalationHistory.timestamp.asc()')

    def to_dict(self):
        return {
            'id': self.id,
            'shipment_id': self.shipment_id,
            'shipment_identifier': self.shipment.shipment_identifier if self.shipment else f"SHP-{self.shipment_id}",
            'exception_id': self.exception_id,
            'priority': self.priority,
            'reason': self.reason,
            'dispatcher_remarks': self.dispatcher_remarks,
            'risk_score': self.risk_score,
            'escalated_by': self.escalated_by_name,
            'status': self.status,
            'assigned_to': self.assigned_to_name or 'Unassigned',
            'manager_remarks': self.manager_remarks,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'resolved_at': self.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if self.resolved_at else None,
            'history': [h.to_dict() for h in self.history] if self.history else []
        }

class EscalationHistory(db.Model):
    __tablename__ = 'escalation_history'

    id = db.Column(db.Integer, primary_key=True)
    escalation_id = db.Column(db.Integer, db.ForeignKey('manager_escalations.id', ondelete='CASCADE'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)  # ESCALATED, STATUS_UPDATED, ASSIGNED, REMARKS_ADDED, RESOLVED
    performed_by = db.Column(db.String(80), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'escalation_id': self.escalation_id,
            'action': self.action,
            'performed_by': self.performed_by,
            'notes': self.notes,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None
        }
