"""Authentication utilities for ChoreControl."""

import secrets
from functools import wraps
from flask import g, jsonify, session, redirect, url_for, request


def ha_auth_required(f):
    """Decorator to ensure user is authenticated via HA ingress or session.

    For UI routes: Only parents can access (kids/unmapped see access_restricted page)
    For API routes: All authenticated users can access (needed for HA integration)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'ha_user') or g.ha_user is None:
            # For UI routes, redirect to login
            if request.accept_mimetypes.accept_html:
                return redirect(url_for('auth.login'))
            # For API routes, return JSON error
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }), 401

        # Get current user to check role
        user = get_current_user()

        # If user doesn't exist in database, redirect to login
        if user is None:
            if request.accept_mimetypes.accept_html:
                return redirect(url_for('auth.login'))
            return jsonify({
                'error': 'Unauthorized',
                'message': 'User not found in database'
            }), 401

        # Check if this is an API route (starts with /api/)
        is_api_route = request.path.startswith('/api/')

        # For API routes, allow all authenticated users (kids need access for HA integration)
        if is_api_route:
            return f(*args, **kwargs)

        # For UI routes, only allow parents
        # Kids and unmapped users should use HA integration only
        if user.role != 'parent':
            # Show access restricted page
            from flask import render_template
            return render_template('access_restricted.html',
                                 username=user.username,
                                 user_role=user.role,
                                 ha_user_id=user.ha_user_id,
                                 points=user.points if user.role == 'kid' else 0), 403

        return f(*args, **kwargs)
    return decorated_function


def parent_required(f):
    """Decorator to ensure user is a parent (has admin privileges)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            if request.accept_mimetypes.accept_html:
                return redirect(url_for('auth.login'))
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }), 401

        if user.role != 'parent':
            if request.accept_mimetypes.accept_html:
                return redirect(url_for('ui.dashboard'))
            return jsonify({
                'error': 'Forbidden',
                'message': 'Parent privileges required'
            }), 403

        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """
    Get the current authenticated user from the database.

    Returns:
        User: Current user object or None if not found
    """
    from models import User

    if not hasattr(g, 'ha_user') or g.ha_user is None:
        return None

    # Cache the user lookup in g to avoid repeated DB queries within the same request
    if not hasattr(g, 'current_user') or not hasattr(g, 'cached_ha_user_id') or g.cached_ha_user_id != g.ha_user:
        g.current_user = User.query.filter_by(ha_user_id=g.ha_user).first()
        g.cached_ha_user_id = g.ha_user

    return g.current_user


def login_user(user):
    """
    Log in a user by setting their session.

    Args:
        user: User object to log in
    """
    session['user_id'] = user.id
    session['ha_user_id'] = user.ha_user_id
    session.permanent = True  # Use permanent session with configured lifetime


def logout_user():
    """Log out the current user by clearing session."""
    session.pop('user_id', None)
    session.pop('ha_user_id', None)


def get_session_user_id():
    """Get the ha_user_id from session if logged in."""
    return session.get('ha_user_id')


def auto_create_unmapped_user(ha_user_id: str):
    """
    Auto-create an unmapped user entry when a HA user accesses the addon via ingress.

    This function is called on every request from middleware. It:
    1. Skips local- prefix accounts (they use password login)
    2. Checks if user already exists (returns None if exists)
    3. Fetches HA user display name from Supervisor API
    4. Creates new user with role='unmapped' (parent will map them later)
    5. Handles race conditions gracefully

    Args:
        ha_user_id: The Home Assistant user ID from X-Ingress-User header

    Returns:
        User: The created user object, or None if user already exists or creation failed
    """
    from models import db, User
    from sqlalchemy.exc import IntegrityError
    from utils.ha_api import get_ha_user_display_name
    import logging

    logger = logging.getLogger(__name__)

    # Skip local accounts (they use password-based login)
    if ha_user_id.startswith('local-'):
        return None

    try:
        # Check if user already exists
        existing_user = User.query.filter_by(ha_user_id=ha_user_id).first()
        if existing_user:
            return None

        # Fetch display name from HA API (falls back to ha_user_id if unavailable)
        username = get_ha_user_display_name(ha_user_id)

        # Create new unmapped user
        new_user = User(
            ha_user_id=ha_user_id,
            username=username,
            role='unmapped',  # Parent will assign actual role via mapping UI
            points=0
        )
        # No password_hash - HA users authenticate via ingress only

        db.session.add(new_user)
        db.session.commit()

        logger.info(f"Auto-created unmapped user: {username} (ha_user_id={ha_user_id})")
        return new_user

    except IntegrityError:
        # Race condition - another request created the user simultaneously
        db.session.rollback()
        logger.debug(f"User {ha_user_id} already exists (race condition)")
        return None
    except Exception as e:
        # Log error but don't fail the request
        db.session.rollback()
        logger.error(f"Failed to auto-create user {ha_user_id}: {e}", exc_info=True)
        return None


def create_default_admin():
    """
    Create the default admin user if no users exist.

    Returns:
        User: The created admin user, or None if users already exist
    """
    from models import db, User
    from sqlalchemy.exc import OperationalError, IntegrityError

    try:
        # Check if admin user already exists
        existing_admin = User.query.filter_by(ha_user_id='local-admin').first()
        if existing_admin is not None:
            return None

        # Create default admin user
        admin = User(
            ha_user_id='local-admin',
            username='admin',
            role='parent',
            points=0
        )
        admin.set_password('admin')

        db.session.add(admin)
        db.session.commit()

        return admin
    except OperationalError:
        # Table doesn't exist yet (migrations not run)
        return None
    except IntegrityError:
        # Race condition - another worker already created the admin
        db.session.rollback()
        return None


def get_or_create_api_token() -> str:
    """
    Get or create the API token for Home Assistant integration.

    Returns:
        str: The API token
    """
    from models import Settings
    from sqlalchemy.exc import OperationalError
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Check if token already exists
        token = Settings.get('api_token')
        if token:
            return token

        # Generate new secure token (32 bytes = 64 hex characters)
        token = secrets.token_hex(32)
        Settings.set('api_token', token)
        logger.info("Generated new API token for Home Assistant integration")
        return token

    except OperationalError:
        # Table doesn't exist yet (migrations not run)
        # Return a temporary token that will be regenerated on next startup
        logger.warning("Settings table not ready, using temporary token")
        return "TEMPORARY_TOKEN_RUN_MIGRATIONS"


def verify_api_token(token: str) -> bool:
    """
    Verify if the provided API token is valid.

    Args:
        token: The API token to verify

    Returns:
        bool: True if token is valid
    """
    from models import Settings
    import logging

    logger = logging.getLogger(__name__)

    try:
        stored_token = Settings.get('api_token')
        if not stored_token:
            logger.warning("No API token found in database")
            return False

        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(token, stored_token)

    except Exception as e:
        logger.error(f"Error verifying API token: {e}")
        return False
