import datetime as dt
from extensions import db

class ExceptionAction(db.Model):
    __tablename__ = 'exception_actions'
    id = db.Column(db.Integer, primary_key=True)
    exception_id = db.Column(db.Integer, db.ForeignKey('shipment_exceptions.id'), nullable=False)
    action_taken = db.Column(db.String(255), nullable=False)
    taken_by = db.Column(db.String(80), nullable=False)
    action_timestamp = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'exception_id': self.exception_id,
            'action': self.action_taken,
            'taken_by': self.taken_by,
            'timestamp': self.action_timestamp.isoformat() if self.action_timestamp else None
        }
