import datetime as dt
from extensions import db

class ModelRegistry(db.Model):
    __tablename__ = 'model_registry'
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    model_version = db.Column(db.String(50), nullable=False)
    prediction_stage = db.Column(db.String(50), nullable=False)
    algorithm = db.Column(db.String(100), nullable=False)
    accuracy = db.Column(db.Float, nullable=True)
    roc_auc = db.Column(db.Float, nullable=True)
    decision_threshold = db.Column(db.Float, default=0.50)
    artifact_path = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'model_name': self.model_name,
            'version': self.model_version,
            'stage': self.prediction_stage,
            'algorithm': self.algorithm,
            'accuracy': self.accuracy,
            'roc_auc': self.roc_auc,
            'decision_threshold': self.decision_threshold,
            'is_active': self.is_active
        }
