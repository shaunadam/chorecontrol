"""ChoreControl Flask application - Main entry point."""

import os
from pathlib import Path
from flask import Flask, jsonify, request, g
from flask_migrate import Migrate
from sqlalchemy import text

# Import db from models (models.py creates the SQLAlchemy instance)
from models import db
from auth import ha_auth_required

# Initialize Flask-Migrate
migrate = Migrate()


def create_app(config_name=None):
    """Application factory pattern for Flask app creation."""
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        # Default to development if running locally, production if in container/HA
        # Check if we're in a production environment (Home Assistant addon)
        if os.path.exists('/data') or os.environ.get('SUPERVISOR_TOKEN'):
            config_name = os.environ.get('FLASK_ENV', 'production')
        else:
            config_name = os.environ.get('FLASK_ENV', 'development')

    from config import config
    app.config.from_object(config[config_name])

    # Ensure data directory exists (skip for in-memory database)
    if app.config['SQLALCHEMY_DATABASE_URI'] != "sqlite:///:memory:":
        data_dir = Path(app.config['DATA_DIR'])
        data_dir.mkdir(parents=True, exist_ok=True)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Register middleware
    register_middleware(app)

    # Register routes
    register_routes(app)

    # Initialize background scheduler
    from scheduler import init_scheduler
    init_scheduler(app)

    # Create default admin user on first run
    with app.app_context():
        from auth import create_default_admin
        admin = create_default_admin()
        if admin:
            import logging
            logging.getLogger(__name__).info(f"Created default admin user: {admin.username}")

    return app


def register_middleware(app):
    """Register middleware for authentication and request processing."""

    @app.before_request
    def extract_ha_user():
        """Extract Home Assistant user from ingress headers or session."""
        from auth import get_session_user_id
        from models import User

        ha_user = request.headers.get('X-Ingress-User')

        if ha_user:
            # Use the authenticated user from HA ingress
            # Check if this HA user exists in our database
            user = User.query.filter_by(ha_user_id=ha_user).first()
            if user:
                g.ha_user = ha_user
            else:
                # HA user not in database - they need to log in
                g.ha_user = None
        else:
            # No HA header - check session for local login
            session_user_id = get_session_user_id()
            if session_user_id:
                g.ha_user = session_user_id
            else:
                g.ha_user = None


def register_routes(app):
    """Register all application routes."""

    # Register blueprints
    from routes import users_bp, chores_bp, ui_bp, auth_bp
    from routes.instances import instances_bp
    from routes.rewards import rewards_bp
    from routes.points import points_bp

    # Register auth blueprint first (handles login/logout)
    app.register_blueprint(auth_bp)

    # Register UI blueprint (so it handles the root route)
    app.register_blueprint(ui_bp)

    # Register API blueprints
    app.register_blueprint(users_bp)
    app.register_blueprint(chores_bp)
    app.register_blueprint(instances_bp)
    app.register_blueprint(rewards_bp)
    app.register_blueprint(points_bp)

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
        from models import User
        user = User.query.filter_by(ha_user_id=g.ha_user).first()

        if user:
            return jsonify({
                'ha_user': g.ha_user,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'points': user.points if user.role == 'kid' else None
                },
                'message': 'User authentication working!'
            })
        else:
            return jsonify({
                'ha_user': g.ha_user,
                'user': None,
                'message': 'Authenticated but no user record found. Create a user via POST /api/users'
            })

    # Note: Rewards and Points endpoints are now handled by blueprints


# Create application instance for development server
app = create_app()


if __name__ == '__main__':
    # Run development server
    app.run(host='0.0.0.0', port=8099, debug=True)
