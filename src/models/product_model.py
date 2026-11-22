from extensions import db

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    category_name = db.Column(db.String(100), nullable=False)
    department_name = db.Column(db.String(100), nullable=False)
    product_price = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.product_name,
            'category': self.category_name,
            'department': self.department_name,
            'price': self.product_price
        }
