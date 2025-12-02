"""ChoreControl Flask application - Main entry point."""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, jsonify, request, g
from flask_migrate import Migrate
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Import db from models (models.py creates the SQLAlchemy instance)
from models import db
from auth import ha_auth_required

# Initialize Flask-Migrate
migrate = Migrate()


class IngressMiddleware:
    """WSGI middleware to handle Home Assistant ingress path.

    This middleware reads the X-Ingress-Path header and sets SCRIPT_NAME
    before Flask processes the request, ensuring url_for() generates
    correct URLs with the ingress prefix.
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Get X-Ingress-Path header (WSGI converts to HTTP_X_INGRESS_PATH)
        ingress_path = environ.get('HTTP_X_INGRESS_PATH', '')
        if ingress_path:
            # Set SCRIPT_NAME so Flask generates URLs with ingress prefix
            environ['SCRIPT_NAME'] = ingress_path.rstrip('/')

        return self.app(environ, start_response)


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

    # Add WSGI middleware for Home Assistant ingress
    # IngressMiddleware must wrap the app first to set SCRIPT_NAME before Flask sees it
    # ProxyFix handles other reverse proxy headers (X-Forwarded-For, etc.)
    app.wsgi_app = IngressMiddleware(app.wsgi_app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Register middleware
    register_middleware(app)

    # Register routes
    register_routes(app)

    # Initialize background scheduler
    from scheduler import init_scheduler
    init_scheduler(app)

    # Create default admin user on first run
    with app.app_context():
        from auth import create_default_admin, get_or_create_api_token
        admin = create_default_admin()
        if admin:
            import logging
            logging.getLogger(__name__).info(f"Created default admin user: {admin.username}")

        # Initialize API token for Home Assistant integration
        api_token = get_or_create_api_token()
        import logging
        logging.getLogger(__name__).info(f"API Token for Home Assistant Integration: {api_token}")
        logging.getLogger(__name__).info("Configure this token in the ChoreControl integration settings")

    return app


def register_middleware(app):
    """Register middleware for authentication and request processing."""

    @app.before_request
    def extract_ha_user():
        """Extract Home Assistant user from ingress headers, API token, or session."""
        from auth import get_session_user_id, auto_create_unmapped_user, verify_api_token
        from models import User

        ha_user = request.headers.get('X-Ingress-User')

        if ha_user:
            # Use the authenticated user from HA ingress
            # Set g.ha_user so requires_auth can distinguish between:
            # - No HA header at all (g.ha_user = None)
            # - HA header present but user not in database (g.ha_user set, but user lookup fails)
            g.ha_user = ha_user

            # Auto-create user if doesn't exist (with role='unmapped')
            # This is safe to call on every request - it returns None if user exists
            auto_create_unmapped_user(ha_user)
            g.api_authenticated = False
        else:
            # Check for API token authentication (for HA integration)
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove 'Bearer ' prefix
                if verify_api_token(token):
                    # API token is valid - set g.ha_user to a system user
                    # This allows the integration to access all data
                    g.ha_user = 'api-integration'
                    g.api_authenticated = True

                    # Ensure the api-integration system user exists
                    api_user = User.query.filter_by(ha_user_id='api-integration').first()
                    if not api_user:
                        from models import db
                        api_user = User(
                            ha_user_id='api-integration',
                            username='HA Integration',
                            role='system',
                            points=0
                        )
                        db.session.add(api_user)
                        try:
                            db.session.commit()
                        except:
                            db.session.rollback()
                else:
                    g.ha_user = None
                    g.api_authenticated = False
            else:
                # No API token - check session for local login
                session_user_id = get_session_user_id()
                if session_user_id:
                    g.ha_user = session_user_id
                    g.api_authenticated = False
                else:
                    g.ha_user = None
                    g.api_authenticated = False


def register_routes(app):
    """Register all application routes."""

    # Register blueprints
    from routes import users_bp, chores_bp, ui_bp, auth_bp
    from routes.instances import instances_bp
    from routes.rewards import rewards_bp
    from routes.points import points_bp
    from routes.user_mapping import user_mapping_bp

    # Register auth blueprint first (handles login/logout)
    app.register_blueprint(auth_bp)

    # Register UI blueprint (so it handles the root route)
    app.register_blueprint(ui_bp)

    # Register user mapping blueprint (UI for role assignment)
    app.register_blueprint(user_mapping_bp)

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
