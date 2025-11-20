"""Points API endpoints for ChoreControl."""

from flask import Blueprint, jsonify, request, g
from sqlalchemy import desc
from models import db, User, PointsHistory
from auth import ha_auth_required, get_current_user as auth_get_current_user
from utils.webhooks import fire_webhook

points_bp = Blueprint('points', __name__, url_prefix='/api/points')


def get_current_user():
    """Helper to get current user from g.ha_user."""
    return auth_get_current_user()


@points_bp.route('/adjust', methods=['POST'])
@ha_auth_required
def adjust_points():
    """Manual point adjustment (parent only)."""
    current_user = get_current_user()
    if not current_user or current_user.role != 'parent':
        return jsonify({
            'error': 'Forbidden',
            'message': 'Only parents can manually adjust points'
        }), 403

    data = request.get_json()

    # Validate required fields
    if not data or 'user_id' not in data or 'points_delta' not in data or 'reason' not in data:
        return jsonify({
            'error': 'BadRequest',
            'message': 'Missing required fields: user_id, points_delta, reason'
        }), 400

    # Validate points_delta is an integer
    try:
        points_delta = int(data['points_delta'])
    except (ValueError, TypeError):
        return jsonify({
            'error': 'BadRequest',
            'message': 'points_delta must be a valid integer'
        }), 400

    # Check if points_delta is non-zero
    if points_delta == 0:
        return jsonify({
            'error': 'BadRequest',
            'message': 'points_delta cannot be zero'
        }), 400

    # Get target user
    user_id = data['user_id']
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            'error': 'NotFound',
            'message': f'User {user_id} not found'
        }), 404

    if user.role != 'kid':
        return jsonify({
            'error': 'BadRequest',
            'message': 'Can only adjust points for kids'
        }), 400

    # Store old balance
    old_balance = user.points

    # Adjust points
    reason = data['reason']
    user.adjust_points(
        delta=points_delta,
        reason=reason,
        created_by_id=current_user.id
    )

    db.session.commit()

    # Fire webhook for points adjustment
    fire_webhook('points_awarded', user, delta=points_delta, reason=reason, adjusted_by=current_user.username)

    return jsonify({
        'data': {
            'user_id': user.id,
            'username': user.username,
            'old_balance': old_balance,
            'new_balance': user.points,
            'points_delta': points_delta,
            'reason': reason,
            'adjusted_by': current_user.username
        },
        'message': 'Points adjusted successfully'
    })


@points_bp.route('/history/<int:user_id>', methods=['GET'])
@ha_auth_required
def get_points_history(user_id):
    """Get paginated points history for a user."""
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            'error': 'NotFound',
            'message': f'User {user_id} not found'
        }), 404

    # Check permissions - users can only view their own history, parents can view all
    current_user = get_current_user()
    if not current_user:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'User not found'
        }), 401

    if current_user.role != 'parent' and current_user.id != user_id:
        return jsonify({
            'error': 'Forbidden',
            'message': 'You can only view your own points history'
        }), 403

    # Pagination
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except (ValueError, TypeError):
        return jsonify({
            'error': 'BadRequest',
            'message': 'limit and offset must be valid integers'
        }), 400

    # Validate pagination parameters
    if limit < 1 or limit > 1000:
        return jsonify({
            'error': 'BadRequest',
            'message': 'limit must be between 1 and 1000'
        }), 400

    if offset < 0:
        return jsonify({
            'error': 'BadRequest',
            'message': 'offset must be non-negative'
        }), 400

    # Query points history
    query = PointsHistory.query.filter_by(user_id=user_id).order_by(desc(PointsHistory.created_at))
    total = query.count()
    history_entries = query.limit(limit).offset(offset).all()

    # Format response
    history_data = []
    for entry in history_entries:
        entry_dict = {
            'id': entry.id,
            'points_delta': entry.points_delta,
            'reason': entry.reason,
            'created_at': entry.created_at.isoformat(),
            'chore_instance_id': entry.chore_instance_id,
            'reward_claim_id': entry.reward_claim_id
        }

        # Add creator info if available
        if entry.created_by:
            creator = User.query.get(entry.created_by)
            if creator:
                entry_dict['created_by'] = {
                    'id': creator.id,
                    'username': creator.username,
                    'role': creator.role
                }

        history_data.append(entry_dict)

    return jsonify({
        'data': history_data,
        'total': total,
        'limit': limit,
        'offset': offset,
        'current_balance': user.points,
        'message': f'Retrieved {len(history_data)} history entries'
    })
