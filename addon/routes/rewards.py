"""Rewards API endpoints for ChoreControl."""

from datetime import datetime
from flask import Blueprint, jsonify, request, g
from sqlalchemy import desc
from models import db, Reward, RewardClaim, User
from auth import ha_auth_required, get_current_user as auth_get_current_user

rewards_bp = Blueprint('rewards', __name__, url_prefix='/api/rewards')


def get_current_user():
    """Helper to get current user from g.ha_user."""
    return auth_get_current_user()


@rewards_bp.route('', methods=['GET'])
@ha_auth_required
def list_rewards():
    """List all rewards with optional filtering by active status."""
    active_filter = request.args.get('active')

    query = Reward.query

    if active_filter is not None:
        is_active = active_filter.lower() in ('true', '1', 'yes')
        query = query.filter_by(is_active=is_active)

    rewards = query.order_by(Reward.points_cost).all()

    # Add claim counts to each reward
    rewards_data = []
    for reward in rewards:
        reward_dict = {
            'id': reward.id,
            'name': reward.name,
            'description': reward.description,
            'points_cost': reward.points_cost,
            'cooldown_days': reward.cooldown_days,
            'max_claims_total': reward.max_claims_total,
            'max_claims_per_kid': reward.max_claims_per_kid,
            'is_active': reward.is_active,
            'created_at': reward.created_at.isoformat(),
            'updated_at': reward.updated_at.isoformat(),
            'total_claims': RewardClaim.query.filter_by(
                reward_id=reward.id,
                status='approved'
            ).count()
        }
        rewards_data.append(reward_dict)

    return jsonify({
        'data': rewards_data,
        'message': f'Found {len(rewards_data)} rewards'
    })


@rewards_bp.route('', methods=['POST'])
@ha_auth_required
def create_reward():
    """Create a new reward."""
    user = get_current_user()
    if not user or user.role != 'parent':
        return jsonify({
            'error': 'Forbidden',
            'message': 'Only parents can create rewards'
        }), 403

    data = request.get_json()

    # Validate required fields
    if not data or 'name' not in data or 'points_cost' not in data:
        return jsonify({
            'error': 'BadRequest',
            'message': 'Missing required fields: name, points_cost'
        }), 400

    # Validate points_cost is positive
    try:
        points_cost = int(data['points_cost'])
        if points_cost <= 0:
            return jsonify({
                'error': 'BadRequest',
                'message': 'points_cost must be greater than 0'
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            'error': 'BadRequest',
            'message': 'points_cost must be a valid integer'
        }), 400

    # Create reward
    reward = Reward(
        name=data['name'],
        description=data.get('description'),
        points_cost=points_cost,
        cooldown_days=data.get('cooldown_days'),
        max_claims_total=data.get('max_claims_total'),
        max_claims_per_kid=data.get('max_claims_per_kid'),
        is_active=data.get('is_active', True)
    )

    db.session.add(reward)
    db.session.commit()

    return jsonify({
        'data': {
            'id': reward.id,
            'name': reward.name,
            'description': reward.description,
            'points_cost': reward.points_cost,
            'cooldown_days': reward.cooldown_days,
            'max_claims_total': reward.max_claims_total,
            'max_claims_per_kid': reward.max_claims_per_kid,
            'is_active': reward.is_active,
            'created_at': reward.created_at.isoformat(),
            'updated_at': reward.updated_at.isoformat()
        },
        'message': 'Reward created successfully'
    }), 201


@rewards_bp.route('/<int:reward_id>', methods=['GET'])
@ha_auth_required
def get_reward(reward_id):
    """Get reward details with claim counts and cooldown status."""
    reward = Reward.query.get(reward_id)

    if not reward:
        return jsonify({
            'error': 'NotFound',
            'message': f'Reward {reward_id} not found'
        }), 404

    user = get_current_user()

    # Calculate claim counts
    total_claims = RewardClaim.query.filter_by(
        reward_id=reward.id,
        status='approved'
    ).count()

    # Check if on cooldown for current user
    is_on_cooldown_for_user = False
    cooldown_days_remaining = None
    if user and user.role == 'kid':
        on_cooldown, cooldown_msg = reward.is_on_cooldown(user.id)
        is_on_cooldown_for_user = on_cooldown
        if on_cooldown and cooldown_msg:
            # Extract days from message like "Reward is on cooldown for 3 more days"
            import re
            match = re.search(r'(\d+)', cooldown_msg)
            if match:
                cooldown_days_remaining = int(match.group(1))

    # Get user's claim count
    user_claims = 0
    if user and user.role == 'kid':
        user_claims = RewardClaim.query.filter_by(
            reward_id=reward.id,
            user_id=user.id,
            status='approved'
        ).count()

    return jsonify({
        'data': {
            'id': reward.id,
            'name': reward.name,
            'description': reward.description,
            'points_cost': reward.points_cost,
            'cooldown_days': reward.cooldown_days,
            'max_claims_total': reward.max_claims_total,
            'max_claims_per_kid': reward.max_claims_per_kid,
            'is_active': reward.is_active,
            'created_at': reward.created_at.isoformat(),
            'updated_at': reward.updated_at.isoformat(),
            'total_claims': total_claims,
            'user_claims': user_claims,
            'is_on_cooldown_for_user': is_on_cooldown_for_user,
            'cooldown_days_remaining': cooldown_days_remaining
        },
        'message': 'Reward retrieved successfully'
    })


@rewards_bp.route('/<int:reward_id>', methods=['PUT'])
@ha_auth_required
def update_reward(reward_id):
    """Update an existing reward."""
    user = get_current_user()
    if not user or user.role != 'parent':
        return jsonify({
            'error': 'Forbidden',
            'message': 'Only parents can update rewards'
        }), 403

    reward = Reward.query.get(reward_id)

    if not reward:
        return jsonify({
            'error': 'NotFound',
            'message': f'Reward {reward_id} not found'
        }), 404

    data = request.get_json()

    if not data:
        return jsonify({
            'error': 'BadRequest',
            'message': 'No data provided'
        }), 400

    # Update fields if provided
    if 'name' in data:
        reward.name = data['name']
    if 'description' in data:
        reward.description = data['description']
    if 'points_cost' in data:
        try:
            points_cost = int(data['points_cost'])
            if points_cost <= 0:
                return jsonify({
                    'error': 'BadRequest',
                    'message': 'points_cost must be greater than 0'
                }), 400
            reward.points_cost = points_cost
        except (ValueError, TypeError):
            return jsonify({
                'error': 'BadRequest',
                'message': 'points_cost must be a valid integer'
            }), 400
    if 'cooldown_days' in data:
        reward.cooldown_days = data['cooldown_days']
    if 'max_claims_total' in data:
        reward.max_claims_total = data['max_claims_total']
    if 'max_claims_per_kid' in data:
        reward.max_claims_per_kid = data['max_claims_per_kid']
    if 'is_active' in data:
        reward.is_active = data['is_active']

    reward.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'data': {
            'id': reward.id,
            'name': reward.name,
            'description': reward.description,
            'points_cost': reward.points_cost,
            'cooldown_days': reward.cooldown_days,
            'max_claims_total': reward.max_claims_total,
            'max_claims_per_kid': reward.max_claims_per_kid,
            'is_active': reward.is_active,
            'created_at': reward.created_at.isoformat(),
            'updated_at': reward.updated_at.isoformat()
        },
        'message': 'Reward updated successfully'
    })


@rewards_bp.route('/<int:reward_id>', methods=['DELETE'])
@ha_auth_required
def delete_reward(reward_id):
    """Soft delete a reward (set is_active to False)."""
    user = get_current_user()
    if not user or user.role != 'parent':
        return jsonify({
            'error': 'Forbidden',
            'message': 'Only parents can delete rewards'
        }), 403

    reward = Reward.query.get(reward_id)

    if not reward:
        return jsonify({
            'error': 'NotFound',
            'message': f'Reward {reward_id} not found'
        }), 404

    reward.is_active = False
    reward.updated_at = datetime.utcnow()
    db.session.commit()

    return '', 204


@rewards_bp.route('/<int:reward_id>/claim', methods=['POST'])
@ha_auth_required
def claim_reward(reward_id):
    """Kid claims a reward - deducts points and creates claim record."""
    reward = Reward.query.get(reward_id)

    if not reward:
        return jsonify({
            'error': 'NotFound',
            'message': f'Reward {reward_id} not found'
        }), 404

    user = get_current_user()
    if not user:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'User not found'
        }), 401

    # Check if user can claim the reward
    can_claim, reason = reward.can_claim(user.id)

    if not can_claim:
        # Extract details for specific error types
        details = {}
        if 'Insufficient points' in reason:
            details['required'] = reward.points_cost
            details['current'] = user.points
        elif 'cooldown' in reason.lower():
            # Extract cooldown days remaining
            import re
            match = re.search(r'(\d+)', reason)
            if match:
                details['cooldown_days_remaining'] = int(match.group(1))

        return jsonify({
            'error': 'BadRequest',
            'message': reason,
            'details': details if details else None
        }), 400

    # Create reward claim
    claim = RewardClaim(
        reward_id=reward.id,
        user_id=user.id,
        points_spent=reward.points_cost,
        status='approved'  # Auto-approve reward claims
    )

    db.session.add(claim)
    db.session.flush()  # Flush to get claim.id before using it

    # Deduct points from user
    old_balance = user.points
    user.adjust_points(
        delta=-reward.points_cost,
        reason=f"Claimed reward: {reward.name}",
        created_by_id=user.id,
        reward_claim_id=claim.id
    )

    db.session.commit()

    return jsonify({
        'data': {
            'id': claim.id,
            'reward_id': reward.id,
            'reward_name': reward.name,
            'user_id': user.id,
            'points_spent': reward.points_cost,
            'old_balance': old_balance,
            'new_balance': user.points,
            'claimed_at': claim.claimed_at.isoformat(),
            'status': claim.status
        },
        'message': f'Reward claimed! {reward.points_cost} points spent.'
    })
