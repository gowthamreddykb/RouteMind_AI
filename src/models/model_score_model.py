import datetime as dt
from extensions import db

class ModelScore(db.Model):
    __tablename__ = 'model_scores'
    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipments.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('model_registry.id'), nullable=True)
    prediction_stage = db.Column(db.String(50), nullable=False)
    predicted_probability = db.Column(db.Float, nullable=False)
    predicted_class = db.Column(db.Integer, nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)
    scoring_timestamp = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'shipment_id': self.shipment_id,
            'stage': self.prediction_stage,
            'prob': self.predicted_probability,
            'class': self.predicted_class,
            'risk_level': self.risk_level,
            'scored_at': self.scoring_timestamp.isoformat() if self.scoring_timestamp else None
        }
