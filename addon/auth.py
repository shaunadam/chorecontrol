"""Authentication utilities for ChoreControl."""

from functools import wraps
from flask import g, jsonify


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
