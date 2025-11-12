"""Flask configuration for ChoreControl add-on."""

import os
from pathlib import Path


class Config:
    """Base configuration."""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database settings
    DATA_DIR = Path(os.environ.get('DATA_DIR', '/data'))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATA_DIR / 'chorecontrol.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # APScheduler settings
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = os.environ.get('TZ', 'UTC')

    # Home Assistant integration settings
    HA_SUPERVISOR_API = os.environ.get('SUPERVISOR_TOKEN')
    HA_INGRESS_ENABLED = os.environ.get('INGRESS', 'true').lower() == 'true'

    # Application settings
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    DATA_DIR = Path('./data')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATA_DIR / 'chorecontrol.db'}"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# Config dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
