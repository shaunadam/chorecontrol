"""Rewards API endpoints for ChoreControl."""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, g
from sqlalchemy import desc
from models import db, Reward, RewardClaim, User
from auth import ha_auth_required, get_current_user as auth_get_current_user
from utils.webhooks import fire_webhook

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
        requires_approval=data.get('requires_approval', False),
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
    if 'requires_approval' in data:
        reward.requires_approval = data['requires_approval']
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

    # Get user_id from request body or use current authenticated user
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')

    if not user_id:
        # Use current authenticated user
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'User not found'
            }), 401
        user_id = current_user.id

    # Get the user object
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            'error': 'NotFound',
            'message': f'User {user_id} not found'
        }), 404

    # Only kids and claim_only users can claim rewards
    if user.role not in ('kid', 'claim_only'):
        return jsonify({
            'error': 'Forbidden',
            'message': 'Only kids can claim rewards'
        }), 403

    # Check if user can claim the reward
    can_claim, reason = reward.can_claim(user_id)

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
        status='pending' if reward.requires_approval else 'approved'
    )

    # Set expiration for pending claims (7 days)
    if reward.requires_approval:
        claim.expires_at = datetime.utcnow() + timedelta(days=7)

    db.session.add(claim)
    db.session.flush()  # Flush to get claim.id before using it

    # Deduct points from user (optimistic)
    old_balance = user.points
    user.adjust_points(
        delta=-reward.points_cost,
        reason=f"Claimed reward: {reward.name}",
        created_by_id=user.id,
        reward_claim_id=claim.id
    )

    db.session.commit()

    # Fire webhook
    fire_webhook('reward_claimed', claim)

    message = 'Reward claimed successfully'
    if reward.requires_approval:
        message = f'Reward claim pending approval. Will expire in 7 days. {reward.points_cost} points reserved.'
    else:
        message = f'Reward claimed! {reward.points_cost} points spent.'

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
            'status': claim.status,
            'expires_at': claim.expires_at.isoformat() if claim.expires_at else None
        },
        'message': message
    }), 201


@rewards_bp.route('/claims/<int:claim_id>/unclaim', methods=['POST'])
@ha_auth_required
def unclaim_reward(claim_id):
    """Unclaim a pending reward and refund points."""
    claim = RewardClaim.query.get(claim_id)

    if not claim:
        return jsonify({
            'error': 'NotFound',
            'message': f'Reward claim {claim_id} not found'
        }), 404

    user = get_current_user()
    if not user:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'User not found'
        }), 401

    # Validate ownership
    # Allow claim_only users to unclaim any pending reward (they manage shared devices)
    # Otherwise enforce ownership check
    if user.role != 'claim_only' and claim.user_id != user.id:
        return jsonify({
            'error': 'Forbidden',
            'message': 'Not your claim'
        }), 403

    if claim.status != 'pending':
        return jsonify({
            'error': 'BadRequest',
            'message': 'Can only unclaim pending rewards'
        }), 400

    # Refund points
    reward = claim.reward
    user.adjust_points(
        delta=claim.points_spent,
        reason=f"Unclaimed reward: {reward.name}",
        created_by_id=user.id,
        reward_claim_id=claim.id
    )

    # Delete claim
    db.session.delete(claim)
    db.session.commit()

    return jsonify({
        'message': 'Reward unclaimed, points refunded',
        'points_refunded': claim.points_spent,
        'new_balance': user.points
    }), 200


@rewards_bp.route('/claims/<int:claim_id>/approve', methods=['POST'])
@ha_auth_required
def approve_reward_claim(claim_id):
    """Approve a pending reward claim (parents only)."""
    claim = RewardClaim.query.get(claim_id)

    if not claim:
        return jsonify({
            'error': 'NotFound',
            'message': f'Reward claim {claim_id} not found'
        }), 404

    user = get_current_user()
    if not user or user.role != 'parent':
        return jsonify({
            'error': 'Forbidden',
            'message': 'Only parents can approve rewards'
        }), 403

    if claim.status != 'pending':
        return jsonify({
            'error': 'BadRequest',
            'message': 'Claim is not pending'
        }), 400

    # Approve
    claim.status = 'approved'
    claim.approved_by = user.id
    claim.approved_at = datetime.utcnow()
    claim.expires_at = None

    db.session.commit()

    # Fire webhook
    fire_webhook('reward_approved', claim)

    return jsonify({
        'data': {
            'id': claim.id,
            'reward_id': claim.reward_id,
            'reward_name': claim.reward.name,
            'user_id': claim.user_id,
            'status': claim.status,
            'approved_by': claim.approved_by,
            'approved_at': claim.approved_at.isoformat()
        },
        'message': 'Reward claim approved'
    }), 200


@rewards_bp.route('/claims/history', methods=['GET'])
@ha_auth_required
def claim_history():
    """Get paginated history of approved/rejected reward claims (last 30 days by default)."""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    days = request.args.get('days', 30, type=int)
    user_id = request.args.get('user_id', type=int)
    status_filter = request.args.get('status')  # 'approved', 'rejected', or None for both

    # Limit per_page to reasonable bounds
    per_page = min(max(per_page, 1), 50)

    # Calculate date cutoff
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Build query - only approved and rejected claims (not pending)
    query = RewardClaim.query.filter(
        RewardClaim.status.in_(['approved', 'rejected']),
        RewardClaim.claimed_at >= cutoff_date
    )

    # Apply optional filters
    if user_id:
        query = query.filter(RewardClaim.user_id == user_id)

    if status_filter and status_filter in ('approved', 'rejected'):
        query = query.filter(RewardClaim.status == status_filter)

    # Order by most recent first
    query = query.order_by(desc(RewardClaim.claimed_at))

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Build response data
    claims_data = []
    for claim in pagination.items:
        claim_dict = {
            'id': claim.id,
            'reward_id': claim.reward_id,
            'reward_name': claim.reward.name if claim.reward else 'Unknown',
            'user_id': claim.user_id,
            'username': claim.user.username if claim.user else 'Unknown',
            'points_spent': claim.points_spent,
            'claimed_at': claim.claimed_at.isoformat(),
            'status': claim.status,
            'approved_by': claim.approved_by,
            'approver_name': claim.approver.username if claim.approver else None,
            'approved_at': claim.approved_at.isoformat() if claim.approved_at else None
        }
        claims_data.append(claim_dict)

    return jsonify({
        'data': claims_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'prev_page': page - 1 if pagination.has_prev else None,
            'next_page': page + 1 if pagination.has_next else None
        },
        'message': f'Found {len(claims_data)} claims'
    })


@rewards_bp.route('/claims', methods=['GET'])
@ha_auth_required
def list_claims():
    """List reward claims with optional filtering by status and user.

    Query parameters:
        status: Filter by claim status ('pending', 'approved', 'rejected')
        user_id: Filter by user ID
        limit: Maximum number of results (default 50, max 100)
        offset: Number of results to skip (default 0)

    Returns:
        List of reward claims matching the filters.
    """
    status_filter = request.args.get('status')
    user_id = request.args.get('user_id', type=int)
    limit = min(request.args.get('limit', 50, type=int), 100)
    offset = request.args.get('offset', 0, type=int)

    query = RewardClaim.query

    if status_filter:
        if status_filter not in ('pending', 'approved', 'rejected'):
            return jsonify({
                'error': 'BadRequest',
                'message': f'Invalid status: {status_filter}. Must be pending, approved, or rejected.'
            }), 400
        query = query.filter(RewardClaim.status == status_filter)

    if user_id:
        query = query.filter(RewardClaim.user_id == user_id)

    # Order by most recent first
    query = query.order_by(desc(RewardClaim.claimed_at))

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    claims = query.offset(offset).limit(limit).all()

    claims_data = []
    for claim in claims:
        claims_data.append({
            'id': claim.id,
            'claim_id': claim.id,  # Alias for clarity
            'reward_id': claim.reward_id,
            'reward_name': claim.reward.name if claim.reward else 'Unknown',
            'user_id': claim.user_id,
            'username': claim.user.username if claim.user else 'Unknown',
            'points_spent': claim.points_spent,
            'claimed_at': claim.claimed_at.isoformat(),
            'status': claim.status,
            'expires_at': claim.expires_at.isoformat() if claim.expires_at else None,
            'approved_by': claim.approved_by,
            'approver_name': claim.approver.username if claim.approver else None,
            'approved_at': claim.approved_at.isoformat() if claim.approved_at else None
        })

    return jsonify({
        'data': claims_data,
        'total': total,
        'limit': limit,
        'offset': offset,
        'message': f'Found {len(claims_data)} claims'
    })


@rewards_bp.route('/claims/<int:claim_id>/reject', methods=['POST'])
@ha_auth_required
def reject_reward_claim(claim_id):
    """Reject a pending reward claim and refund points (parents only)."""
    claim = RewardClaim.query.get(claim_id)

    if not claim:
        return jsonify({
            'error': 'NotFound',
            'message': f'Reward claim {claim_id} not found'
        }), 404

    user = get_current_user()
    if not user or user.role != 'parent':
        return jsonify({
            'error': 'Forbidden',
            'message': 'Only parents can reject rewards'
        }), 403

    if claim.status != 'pending':
        return jsonify({
            'error': 'BadRequest',
            'message': 'Claim is not pending'
        }), 400

    # Reject and refund
    claim.status = 'rejected'
    claim.approved_by = user.id
    claim.approved_at = datetime.utcnow()
    claim.expires_at = None

    # Refund points
    claimer = User.query.get(claim.user_id)
    reward = claim.reward
    claimer.adjust_points(
        delta=claim.points_spent,
        reason=f"Reward claim rejected: {reward.name}",
        created_by_id=user.id,
        reward_claim_id=claim.id
    )

    db.session.commit()

    # Fire webhook
    fire_webhook('reward_rejected', claim, reason='manual')

    return jsonify({
        'data': {
            'id': claim.id,
            'reward_id': claim.reward_id,
            'reward_name': reward.name,
            'user_id': claim.user_id,
            'status': claim.status,
            'approved_by': claim.approved_by,
            'approved_at': claim.approved_at.isoformat(),
            'points_refunded': claim.points_spent
        },
        'message': 'Reward claim rejected, points refunded'
    }), 200
