from src.models.user_model import User
from extensions import db

class AuthService:
    @staticmethod
    def authenticate(username_or_email, password):
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        if user and user.check_password(password) and user.is_active:
            return user
        return None

    @staticmethod
    def register(username, email, password, role='dispatcher'):
        if User.query.filter((User.username == username) | (User.email == email)).first():
            return None
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
