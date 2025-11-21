"""Authentication utilities for ChoreControl."""

from functools import wraps
from flask import g, jsonify, session, redirect, url_for, request


def ha_auth_required(f):
    """Decorator to ensure user is authenticated via HA ingress or session."""
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


def create_default_admin():
    """
    Create the default admin user if no users exist.

    Returns:
        User: The created admin user, or None if users already exist
    """
    from models import db, User
    from sqlalchemy.exc import OperationalError

    try:
        # Check if any users exist
        if User.query.first() is not None:
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
