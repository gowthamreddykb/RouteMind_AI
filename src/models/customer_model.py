from extensions import db

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    segment = db.Column(db.String(50), default='Consumer')
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    country = db.Column(db.String(100), default='Puerto Rico')

    def to_dict(self):
        return {
            'id': self.id,
            'name': f"{self.first_name} {self.last_name}",
            'segment': self.segment,
            'city': self.city,
            'state': self.state,
            'country': self.country
        }
