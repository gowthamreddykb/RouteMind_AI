from extensions import db

class ReferenceData(db.Model):
    __tablename__ = 'reference_data'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'code': self.code,
            'label': self.label,
            'is_active': self.is_active
        }
