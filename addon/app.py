"""ChoreControl Flask application - Main entry point."""

import os
from pathlib import Path
from functools import wraps
from flask import Flask, jsonify, request, g
from flask_migrate import Migrate
from sqlalchemy import text

# Import db from models (models.py creates the SQLAlchemy instance)
from .models import db

# Initialize Flask-Migrate
migrate = Migrate()


def create_app(config_name=None):
    """Application factory pattern for Flask app creation."""
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')

    from .config import config
    app.config.from_object(config[config_name])

    # Ensure data directory exists
    data_dir = Path(app.config['DATA_DIR'])
    data_dir.mkdir(parents=True, exist_ok=True)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Register middleware
    register_middleware(app)

    # Register routes
    register_routes(app)

    return app


def register_middleware(app):
    """Register middleware for authentication and request processing."""

    @app.before_request
    def extract_ha_user():
        """Extract Home Assistant user from ingress headers."""
        if app.config['HA_INGRESS_ENABLED']:
            # HA ingress provides authenticated user via header
            ha_user = request.headers.get('X-Ingress-User')
            g.ha_user = ha_user
        else:
            # For development/testing without ingress
            g.ha_user = request.headers.get('X-Ingress-User', 'dev-user')


def ha_auth_required(f):
    """Decorator to ensure user is authenticated via HA ingress."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'ha_user') or g.ha_user is None:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Home Assistant authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def register_routes(app):
    """Register all application routes."""

    @app.route('/')
    def index():
        """Home page - will serve web UI."""
        return jsonify({
            'name': 'ChoreControl',
            'version': '0.1.0',
            'status': 'running',
            'message': 'ChoreControl API is running. Web UI coming soon!'
        })

    @app.route('/health')
    def health():
        """Health check endpoint for monitoring."""
        try:
            # Check database connectivity
            db.session.execute(text('SELECT 1'))
            db_status = 'healthy'
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'

        return jsonify({
            'status': 'healthy' if db_status == 'healthy' else 'degraded',
            'database': db_status,
            'ha_user': getattr(g, 'ha_user', None)
        })

    @app.route('/api/user')
    @ha_auth_required
    def current_user():
        """Get current authenticated user information."""
        return jsonify({
            'ha_user': g.ha_user,
            'message': 'User authentication working! Models will be added in Stream 2.'
        })

    # Placeholder for future API routes
    # These will be implemented after models are created in Stream 2
    @app.route('/api/chores')
    @ha_auth_required
    def list_chores():
        """List all chores - placeholder."""
        return jsonify({
            'message': 'Chores endpoint - to be implemented with models',
            'chores': []
        })

    @app.route('/api/rewards')
    @ha_auth_required
    def list_rewards():
        """List all rewards - placeholder."""
        return jsonify({
            'message': 'Rewards endpoint - to be implemented with models',
            'rewards': []
        })


# Create application instance for development server
app = create_app()


if __name__ == '__main__':
    # Run development server
    app.run(host='0.0.0.0', port=8099, debug=True)
