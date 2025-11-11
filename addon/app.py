"""
Flask application factory for ChoreControl.

This module sets up the Flask application, database, and migrations.
"""

import os
from flask import Flask
from flask_migrate import Migrate

from .models import db


def create_app(config=None):
    """
    Create and configure the Flask application.

    Args:
        config: Optional configuration dictionary

    Returns:
        Flask application instance
    """
    app = Flask(__name__)

    # Default configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'sqlite:///chorecontrol.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = os.environ.get('SQL_DEBUG', 'false').lower() == 'true'

    # Override with provided config
    if config:
        app.config.update(config)

    # Initialize extensions
    db.init_app(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Register blueprints (when they exist)
    # from .routes import api_bp
    # app.register_blueprint(api_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
