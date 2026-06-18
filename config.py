"""
وضيفة DZ | Wadifa DZ — Production Configuration
"""
import os
from datetime import timedelta

class Config:
    # ── Security ──────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is not set!")

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # ── Database ──────────────────────────────────────────
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///wadifa-dz.db')
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # ── Upload ────────────────────────────────────────────
    UPLOAD_FOLDER = '/tmp/uploads'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

    # ── App ───────────────────────────────────────────────
    BASE_URL = os.environ.get('BASE_URL', 'https://web-production-dbe18.up.railway.app')
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig,
}
