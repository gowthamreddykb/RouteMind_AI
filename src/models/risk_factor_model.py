from extensions import db

class RiskFactor(db.Model):
    __tablename__ = 'risk_factors'
    id = db.Column(db.Integer, primary_key=True)
    score_id = db.Column(db.Integer, db.ForeignKey('model_scores.id'), nullable=False)
    feature_name = db.Column(db.String(100), nullable=False)
    feature_value = db.Column(db.String(100), nullable=True)
    contribution_value = db.Column(db.Float, nullable=True)
    contribution_direction = db.Column(db.String(20))
    explanation = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'feature': self.feature_name,
            'value': self.feature_value,
            'contribution': self.contribution_value,
            'direction': self.contribution_direction,
            'explanation': self.explanation
        }
