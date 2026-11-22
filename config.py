import os
import datetime
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SECRET_KEY = os.environ.get('SECRET_KEY', 'routemind-super-secret-production-key-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f'sqlite:///{os.path.join(BASE_DIR, "instance", "routemind.db").replace(os.sep, "/")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEFAULT_EXTERNAL_MODELS = r'C:\gowtham_mithraz\python\Logistics-Control-Tower\files\models'
    MODELS_DIR = os.environ.get(
        'MODELS_DIR',
        DEFAULT_EXTERNAL_MODELS if os.path.exists(DEFAULT_EXTERNAL_MODELS) else os.path.join(BASE_DIR, 'models')
    )
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data', 'raw')
    
    ORDER_CREATION_THRESHOLD = float(os.environ.get('ORDER_CREATION_THRESHOLD', 0.40))
    DISPATCH_THRESHOLD = float(os.environ.get('DISPATCH_THRESHOLD', 0.39))
    
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    LLM_API_KEY = os.environ.get('LLM_API_KEY', 'demo-key')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gemini-1.5-pro')

    # SMTP Email Configuration for OTP Authentication
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ('true', '1', 'yes', 't')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ('true', '1', 'yes', 't')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', None)
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', None)
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'RouteMind AI <no-reply@routemind.ai>')
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'false').lower() in ('true', '1', 'yes', 't')

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
