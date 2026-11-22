import datetime as dt
from flask_login import UserMixin
from extensions import db
from src.security.authentication import hash_password, verify_password
from src.security.permissions import normalize_role, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=ROLE_DISPATCHER)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    @property
    def normalized_role(self):
        return normalize_role(self.role)

    def is_dispatcher(self):
        return self.normalized_role == ROLE_DISPATCHER

    def is_manager(self):
        return self.normalized_role == ROLE_MANAGER

    def is_admin(self):
        return self.normalized_role == ROLE_ADMIN

    def set_password(self, password):
        self.password_hash = hash_password(password)

    def check_password(self, password):
        return verify_password(password, self.password_hash)

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name or self.username.replace('_', ' ').title(),
            'username': self.username,
            'email': self.email,
            'role': self.normalized_role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
