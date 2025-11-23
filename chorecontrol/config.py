"""Flask configuration for ChoreControl add-on."""

import os
from pathlib import Path
from datetime import timedelta


class Config:
    """Base configuration."""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Session settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Session lasts 7 days

    # Database settings
    DATA_DIR = Path(os.environ.get('DATA_DIR', '/data'))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATA_DIR / 'chorecontrol.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # APScheduler settings
    SCHEDULER_ENABLED = os.environ.get('SCHEDULER_ENABLED', 'true').lower() == 'true'
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = os.environ.get('TZ', 'UTC')

    # Home Assistant integration settings
    HA_SUPERVISOR_API = os.environ.get('SUPERVISOR_TOKEN')
    HA_INGRESS_ENABLED = os.environ.get('INGRESS', 'true').lower() == 'true'
    HA_WEBHOOK_URL = os.environ.get('HA_WEBHOOK_URL')
    # Example: http://homeassistant.local:8123/api/webhook/chorecontrol-abc123

    # Application settings
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    DATA_DIR = Path(__file__).parent / 'data'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATA_DIR / 'chorecontrol.db'}"
    # Keep scheduler running in development
    SCHEDULER_ENABLED = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Re-evaluate DATA_DIR and database URI to ensure environment variable is picked up
    DATA_DIR = Path(os.environ.get('DATA_DIR', '/data'))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATA_DIR / 'chorecontrol.db'}"


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Disable scheduler during tests
    SCHEDULER_ENABLED = False


# Config dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
