"""User management API endpoints."""

from flask import Blueprint, jsonify, request, g
from sqlalchemy import desc
from models import db, User, PointsHistory

users_bp = Blueprint('users', __name__, url_prefix='/api/users')


def get_current_user():
    """
    Get the current authenticated user from the database.

    Returns:
        User: Current user object or None if not found
    """
    if not hasattr(g, 'ha_user') or g.ha_user is None:
        return None

    # Cache the user lookup in g to avoid repeated DB queries within the same request
    # Check if we need to refresh the cache (ha_user changed)
    if not hasattr(g, 'current_user') or not hasattr(g, 'cached_ha_user_id') or g.cached_ha_user_id != g.ha_user:
        g.current_user = User.query.filter_by(ha_user_id=g.ha_user).first()
        g.cached_ha_user_id = g.ha_user

    return g.current_user


def requires_auth(f):
    """Decorator to ensure user is authenticated and exists in database."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'ha_user') or g.ha_user is None:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Home Assistant authentication required'
            }), 401

        user = get_current_user()
        if user is None:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'User not found in database. Please create a user account first.'
            }), 401

        return f(*args, **kwargs)

    return decorated_function


def requires_parent(f):
    """Decorator to ensure user is a parent."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None or user.role != 'parent':
            return jsonify({
                'error': 'Forbidden',
                'message': 'This action requires parent privileges'
            }), 403

        return f(*args, **kwargs)

    return decorated_function


@users_bp.route('', methods=['GET'])
@requires_auth
def list_users():
    """
    List all users with optional filtering by role.

    Query Parameters:
        role: Filter by role (parent or kid)
        limit: Maximum number of results (default: 50)
        offset: Offset for pagination (default: 0)

    Returns:
        JSON response with list of users
    """
    # Get query parameters
    role_filter = request.args.get('role')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    # Validate role filter
    if role_filter and role_filter not in ('parent', 'kid'):
        return jsonify({
            'error': 'BadRequest',
            'message': 'Invalid role filter. Must be "parent" or "kid"'
        }), 400

    # Build query
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)

    # Get total count
    total = query.count()

    # Apply pagination
    users = query.limit(limit).offset(offset).all()

    # Serialize users
    users_data = [{
        'id': user.id,
        'ha_user_id': user.ha_user_id,
        'username': user.username,
        'role': user.role,
        'points': user.points if user.role == 'kid' else None,
        'created_at': user.created_at.isoformat(),
        'updated_at': user.updated_at.isoformat()
    } for user in users]

    return jsonify({
        'data': users_data,
        'total': total,
        'limit': limit,
        'offset': offset,
        'message': 'Users retrieved successfully'
    }), 200


@users_bp.route('', methods=['POST'])
@requires_auth
@requires_parent
def create_user():
    """
    Create a new user linked to a Home Assistant user ID.

    Request Body:
        ha_user_id: Home Assistant user ID (required)
        username: Display name (required)
        role: User role - "parent" or "kid" (required)

    Returns:
        JSON response with created user data
    """
    data = request.get_json()

    # Validate required fields
    if not data:
        return jsonify({
            'error': 'BadRequest',
            'message': 'Request body is required'
        }), 400

    ha_user_id = data.get('ha_user_id')
    username = data.get('username')
    role = data.get('role')

    if not ha_user_id:
        return jsonify({
            'error': 'BadRequest',
            'message': 'ha_user_id is required'
        }), 400

    if not username:
        return jsonify({
            'error': 'BadRequest',
            'message': 'username is required'
        }), 400

    if not role or role not in ('parent', 'kid'):
        return jsonify({
            'error': 'BadRequest',
            'message': 'role is required and must be "parent" or "kid"'
        }), 400

    # Check if user already exists
    existing_user = User.query.filter_by(ha_user_id=ha_user_id).first()
    if existing_user:
        return jsonify({
            'error': 'Conflict',
            'message': f'User with ha_user_id "{ha_user_id}" already exists',
            'details': {'user_id': existing_user.id}
        }), 409

    # Create new user
    new_user = User(
        ha_user_id=ha_user_id,
        username=username,
        role=role,
        points=0 if role == 'kid' else 0
    )

    try:
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'data': {
                'id': new_user.id,
                'ha_user_id': new_user.ha_user_id,
                'username': new_user.username,
                'role': new_user.role,
                'points': new_user.points if new_user.role == 'kid' else None,
                'created_at': new_user.created_at.isoformat(),
                'updated_at': new_user.updated_at.isoformat()
            },
            'message': 'User created successfully'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'InternalServerError',
            'message': 'Failed to create user',
            'details': {'error': str(e)}
        }), 500


@users_bp.route('/<int:user_id>', methods=['GET'])
@requires_auth
def get_user(user_id):
    """
    Get detailed information about a specific user.

    Path Parameters:
        user_id: ID of the user to retrieve

    Returns:
        JSON response with user details including relationships
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            'error': 'NotFound',
            'message': f'User with ID {user_id} not found',
            'details': {'user_id': user_id}
        }), 404

    # Build user data with relationships
    user_data = {
        'id': user.id,
        'ha_user_id': user.ha_user_id,
        'username': user.username,
        'role': user.role,
        'points': user.points if user.role == 'kid' else None,
        'created_at': user.created_at.isoformat(),
        'updated_at': user.updated_at.isoformat(),
        'relationships': {
            'chore_assignments_count': len(user.chore_assignments),
            'claimed_chores_count': len(user.claimed_instances),
            'reward_claims_count': len(user.reward_claims)
        }
    }

    # Add parent-specific data
    if user.role == 'parent':
        user_data['relationships']['created_chores_count'] = len(user.created_chores)
        user_data['relationships']['approved_chores_count'] = len(user.approved_instances)

    return jsonify({
        'data': user_data,
        'message': 'User retrieved successfully'
    }), 200


@users_bp.route('/<int:user_id>', methods=['PUT'])
@requires_auth
@requires_parent
def update_user(user_id):
    """
    Update user information.

    Path Parameters:
        user_id: ID of the user to update

    Request Body:
        username: Display name (optional)
        role: User role - "parent" or "kid" (optional)

    Note: ha_user_id cannot be changed after creation

    Returns:
        JSON response with updated user data
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            'error': 'NotFound',
            'message': f'User with ID {user_id} not found',
            'details': {'user_id': user_id}
        }), 404

    data = request.get_json()

    if not data:
        return jsonify({
            'error': 'BadRequest',
            'message': 'Request body is required'
        }), 400

    # Update username if provided
    if 'username' in data:
        if not data['username']:
            return jsonify({
                'error': 'BadRequest',
                'message': 'username cannot be empty'
            }), 400
        user.username = data['username']

    # Update role if provided
    if 'role' in data:
        if data['role'] not in ('parent', 'kid'):
            return jsonify({
                'error': 'BadRequest',
                'message': 'role must be "parent" or "kid"'
            }), 400

        # If changing from parent to kid, initialize points
        if user.role == 'parent' and data['role'] == 'kid':
            user.points = 0

        user.role = data['role']

    # Prevent changing ha_user_id
    if 'ha_user_id' in data:
        return jsonify({
            'error': 'BadRequest',
            'message': 'ha_user_id cannot be changed after user creation'
        }), 400

    try:
        db.session.commit()

        return jsonify({
            'data': {
                'id': user.id,
                'ha_user_id': user.ha_user_id,
                'username': user.username,
                'role': user.role,
                'points': user.points if user.role == 'kid' else None,
                'created_at': user.created_at.isoformat(),
                'updated_at': user.updated_at.isoformat()
            },
            'message': 'User updated successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'InternalServerError',
            'message': 'Failed to update user',
            'details': {'error': str(e)}
        }), 500


@users_bp.route('/<int:user_id>/points', methods=['GET'])
@requires_auth
def get_user_points(user_id):
    """
    Get user's points balance and history with verification.

    Path Parameters:
        user_id: ID of the user

    Query Parameters:
        limit: Maximum number of history entries to return (default: 50)
        offset: Offset for pagination (default: 0)

    Returns:
        JSON response with current balance, calculated balance, and paginated history
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            'error': 'NotFound',
            'message': f'User with ID {user_id} not found',
            'details': {'user_id': user_id}
        }), 404

    # Get pagination parameters
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    # Calculate points from history
    calculated_points = user.calculate_current_points()
    is_balanced = user.verify_points_balance()

    # Get points history
    history_query = PointsHistory.query.filter_by(user_id=user_id).order_by(desc(PointsHistory.created_at))
    total_history = history_query.count()
    history_entries = history_query.limit(limit).offset(offset).all()

    # Serialize history
    history_data = [{
        'id': entry.id,
        'points_delta': entry.points_delta,
        'reason': entry.reason,
        'created_at': entry.created_at.isoformat(),
        'created_by': entry.created_by,
        'chore_instance_id': entry.chore_instance_id,
        'reward_claim_id': entry.reward_claim_id
    } for entry in history_entries]

    return jsonify({
        'data': {
            'user_id': user.id,
            'username': user.username,
            'current_balance': user.points,
            'calculated_balance': calculated_points,
            'is_balanced': is_balanced,
            'history': history_data,
            'total_history_entries': total_history,
            'limit': limit,
            'offset': offset
        },
        'message': 'Points information retrieved successfully'
    }), 200


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@requires_auth
@requires_parent
def delete_user(user_id):
    """
    Delete a user and all their associated data.

    Path Parameters:
        user_id: ID of the user to delete

    Returns:
        JSON response confirming deletion

    Note: This will cascade delete all related records including:
        - Chore assignments
        - Points history
        - Reward claims
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            'error': 'NotFound',
            'message': f'User with ID {user_id} not found',
            'details': {'user_id': user_id}
        }), 404

    # Store username for response message
    username = user.username

    try:
        # SQLAlchemy will handle cascade deletes based on relationships
        db.session.delete(user)
        db.session.commit()

        return jsonify({
            'message': f'User "{username}" deleted successfully',
            'details': {'user_id': user_id}
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'InternalServerError',
            'message': 'Failed to delete user',
            'details': {'error': str(e)}
        }), 500
