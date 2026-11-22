import datetime as dt
from extensions import db

class ShipmentEvent(db.Model):
    __tablename__ = 'shipment_events'
    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipments.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    event_timestamp = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    warehouse_processing_time = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'shipment_id': self.shipment_id,
            'event_type': self.event_type,
            'timestamp': self.event_timestamp.isoformat() if self.event_timestamp else None,
            'warehouse_processing_time': self.warehouse_processing_time,
            'notes': self.notes
        }
