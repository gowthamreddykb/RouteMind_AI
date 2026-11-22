import datetime as dt
from extensions import db

class Shipment(db.Model):
    __tablename__ = 'shipments'
    id = db.Column(db.Integer, primary_key=True)
    shipment_number = db.Column(db.String(64), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    
    order_date = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    scheduled_days = db.Column(db.Integer, default=4)
    shipping_mode = db.Column(db.String(50), default='Standard Class')
    order_status = db.Column(db.String(50), default='PENDING')
    payment_type = db.Column(db.String(50), default='DEBIT')
    
    sales = db.Column(db.Float, default=0.0)
    quantity = db.Column(db.Integer, default=1)
    product_price = db.Column(db.Float, default=0.0)
    discount_rate = db.Column(db.Float, default=0.0)
    
    origin_region = db.Column(db.String(100), default='US Center')
    destination_region = db.Column(db.String(100), default='Western Europe')
    destination_country = db.Column(db.String(100), default='France')
    market = db.Column(db.String(50), default='Europe')
    
    # Maritime Specific Telemetry & Container Identifiers
    vessel_name = db.Column(db.String(100), nullable=True)
    container_number = db.Column(db.String(50), nullable=True)
    container_type = db.Column(db.String(50), default='40ft High Cube Dry')
    origin_port = db.Column(db.String(100), nullable=True)
    destination_port = db.Column(db.String(100), nullable=True)
    planned_departure = db.Column(db.DateTime, nullable=True)
    expected_arrival = db.Column(db.DateTime, nullable=True)
    actual_arrival = db.Column(db.DateTime, nullable=True)
    order_id_code = db.Column(db.String(50), nullable=True)

    order_creation_prob = db.Column(db.Float, nullable=True)
    dispatch_prob = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(20), default='LOW')
    dock_clearance_status = db.Column(db.String(50), default='CLEAR_FOR_TRANSIT')
    
    customer = db.relationship('Customer', backref=db.backref('shipments', lazy=True))
    product = db.relationship('Product', backref=db.backref('shipments', lazy=True))
    events = db.relationship('ShipmentEvent', backref='shipment', lazy=True, order_by='ShipmentEvent.event_timestamp.desc()')
    exceptions = db.relationship('ShipmentException', backref='shipment', lazy=True, order_by='ShipmentException.created_at.desc()')
    
    created_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by_name = db.Column(db.String(80), nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_to_name = db.Column(db.String(80), nullable=True)

    @property
    def shipment_identifier(self):
        return self.shipment_number

    @property
    def days_scheduled(self):
        return self.scheduled_days

    @property
    def order_item_quantity(self):
        return self.quantity

    @property
    def sales_per_customer(self):
        return self.sales

    @property
    def warehouse_processing_time_days(self):
        if self.order_status in ['READY_FOR_DISPATCH', 'DISPATCHED', 'IN_TRANSIT', 'ARRIVED_AT_DESTINATION', 'OUT_FOR_DELIVERY', 'DELIVERED', 'COMPLETED']:
            return 2.0
        return None

    @property
    def customer_segment(self):
        if self.customer and hasattr(self.customer, 'segment') and self.customer.segment:
            return self.customer.segment
        return "Consumer"

    @property
    def risk_score(self):
        if self.dispatch_prob is not None:
            return self.dispatch_prob
        if self.order_creation_prob is not None:
            return self.order_creation_prob
        return 0.25

    def to_dict(self):
        return {
            'id': self.id,
            'shipment_number': self.shipment_number,
            'order_id_code': self.order_id_code or f"ORD-{self.shipment_number}",
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'scheduled_days': self.scheduled_days,
            'shipping_mode': self.shipping_mode,
            'order_status': self.order_status,
            'sales': self.sales,
            'quantity': self.quantity,
            'origin_port': self.origin_port,
            'destination_port': self.destination_port,
            'destination_region': self.destination_region,
            'destination_country': self.destination_country,
            'market': self.market,
            'vessel_name': self.vessel_name,
            'container_number': self.container_number,
            'container_type': self.container_type,
            'planned_departure': self.planned_departure.isoformat() if self.planned_departure else None,
            'expected_arrival': self.expected_arrival.isoformat() if self.expected_arrival else None,
            'order_creation_prob': self.order_creation_prob,
            'dispatch_prob': self.dispatch_prob,
            'risk_level': self.risk_level,
            'dock_clearance_status': self.dock_clearance_status,
            'created_by': self.created_by_name,
            'assigned_to': self.assigned_to_name
        }
