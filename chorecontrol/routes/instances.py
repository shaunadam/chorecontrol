"""Instance Workflow API routes - Stream 3.

This module implements the core chore instance workflow:
- Listing and viewing instances
- Claiming chores (kid marks as complete)
- Approving chores (parent awards points)
- Rejecting chores (parent rejects with reason, allows re-claim)

State machine: assigned → claimed → approved/rejected
After rejection: rejected → assigned (can re-claim)
"""

import logging
from datetime import datetime, date
from flask import Blueprint, jsonify, request, g
from sqlalchemy import and_, or_
from models import db, ChoreInstance, User
from auth import ha_auth_required, get_current_user as auth_get_current_user
from services.instance_service import InstanceService, InstanceServiceError
from utils.timezone import local_today

instances_bp = Blueprint('instances', __name__, url_prefix='/api/instances')
logger = logging.getLogger(__name__)


def get_current_user() -> User:
    """Get the current authenticated user from the database."""
    return auth_get_current_user()


def serialize_instance(instance: ChoreInstance, include_details: bool = False) -> dict:
    """Serialize a ChoreInstance to JSON.

    Args:
        instance: ChoreInstance object to serialize
        include_details: If True, include full chore and user details

    Returns:
        dict: Serialized instance data
    """
    data = {
        'id': instance.id,
        'chore_id': instance.chore_id,
        'due_date': instance.due_date.isoformat() if instance.due_date else None,
        'status': instance.status,
        'assigned_to': instance.assigned_to,
        'claimed_by': instance.claimed_by,
        'claimed_at': instance.claimed_at.isoformat() if instance.claimed_at else None,
        'claimed_late': instance.claimed_late if hasattr(instance, 'claimed_late') else False,
        'approved_by': instance.approved_by,
        'approved_at': instance.approved_at.isoformat() if instance.approved_at else None,
        'rejected_by': instance.rejected_by,
        'rejected_at': instance.rejected_at.isoformat() if instance.rejected_at else None,
        'rejection_reason': instance.rejection_reason,
        'points_awarded': instance.points_awarded,
        'claiming_closed_at': instance.claiming_closed_at.isoformat() if instance.claiming_closed_at else None,
        'is_work_together': instance.is_work_together(),
        'created_at': instance.created_at.isoformat() if instance.created_at else None,
        'updated_at': instance.updated_at.isoformat() if instance.updated_at else None
    }

    # Include claims for work-together instances
    if instance.is_work_together():
        data['claims'] = [c.to_dict() for c in instance.claims]
        data['claims_count'] = len(instance.claims)
        data['pending_claims_count'] = len([c for c in instance.claims if c.status == 'claimed'])

    if include_details:
        # Include chore details
        if instance.chore:
            data['chore'] = {
                'id': instance.chore.id,
                'name': instance.chore.name,
                'description': instance.chore.description,
                'points': instance.chore.points,
                'requires_approval': instance.chore.requires_approval
            }

        # Include user details
        if instance.claimer:
            data['claimer'] = {
                'id': instance.claimer.id,
                'username': instance.claimer.username,
                'role': instance.claimer.role
            }

        if instance.approver:
            data['approver'] = {
                'id': instance.approver.id,
                'username': instance.approver.username,
                'role': instance.approver.role
            }

        if instance.rejecter:
            data['rejecter'] = {
                'id': instance.rejecter.id,
                'username': instance.rejecter.username,
                'role': instance.rejecter.role
            }

    return data


@instances_bp.route('/test', methods=['GET', 'POST'])
def test_json_response():
    """Test endpoint to verify JSON responses work."""
    logger.info("Test endpoint hit")
    return jsonify({
        'message': 'Test successful',
        'method': request.method,
        'path': request.path,
        'has_ha_user': hasattr(g, 'ha_user'),
        'ha_user_value': getattr(g, 'ha_user', None)
    }), 200


@instances_bp.route('', methods=['GET'])
@ha_auth_required
def list_instances():
    """List chore instances with optional filters.

    Query parameters:
        - status: Filter by status (assigned, claimed, approved, rejected)
        - user_id: Filter by user (claimed_by)
        - chore_id: Filter by chore
        - start_date: Filter by due_date >= start_date (YYYY-MM-DD)
        - end_date: Filter by due_date <= end_date (YYYY-MM-DD)
        - limit: Maximum number of results (default 50)
        - offset: Number of results to skip (default 0)

    Returns:
        JSON: {data: [instances], total: int, limit: int, offset: int}
    """
    query = ChoreInstance.query

    # Apply filters
    status = request.args.get('status')
    if status:
        query = query.filter(ChoreInstance.status == status)

    user_id = request.args.get('user_id', type=int)
    if user_id:
        query = query.filter(ChoreInstance.claimed_by == user_id)

    chore_id = request.args.get('chore_id', type=int)
    if chore_id:
        query = query.filter(ChoreInstance.chore_id == chore_id)

    start_date = request.args.get('start_date')
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(ChoreInstance.due_date >= start_date_obj)
        except ValueError:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Invalid start_date format. Use YYYY-MM-DD'
            }), 400

    end_date = request.args.get('end_date')
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(ChoreInstance.due_date <= end_date_obj)
        except ValueError:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Invalid end_date format. Use YYYY-MM-DD'
            }), 400

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    # Limit max results to 200
    if limit > 200:
        limit = 200

    instances = query.order_by(ChoreInstance.due_date.desc()).limit(limit).offset(offset).all()

    return jsonify({
        'data': [serialize_instance(instance, include_details=True) for instance in instances],
        'total': total,
        'limit': limit,
        'offset': offset,
        'message': f'Found {total} instances'
    }), 200


@instances_bp.route('/<int:instance_id>', methods=['GET'])
@ha_auth_required
def get_instance(instance_id: int):
    """Get detailed information about a specific chore instance.

    Args:
        instance_id: ID of the chore instance

    Returns:
        JSON: {data: instance_details, message: str}
    """
    instance = ChoreInstance.query.get(instance_id)

    if not instance:
        return jsonify({
            'error': 'Not Found',
            'message': f'Chore instance {instance_id} not found'
        }), 404

    return jsonify({
        'data': serialize_instance(instance, include_details=True),
        'message': 'Instance details retrieved successfully'
    }), 200


@instances_bp.route('/due-today', methods=['GET'])
@ha_auth_required
def get_instances_due_today():
    """
    Get all chore instances due today or with no due date.

    Query params:
    - user_id: Filter by assigned user (optional)
    - status: Filter by status (optional)

    Returns:
        JSON: {date: str, count: int, instances: [...]}
    """
    today = local_today()

    query = ChoreInstance.query.filter(
        or_(
            ChoreInstance.due_date == today,
            ChoreInstance.due_date.is_(None)
        )
    )

    # Optional filters
    user_id = request.args.get('user_id', type=int)
    if user_id:
        query = query.filter(
            or_(
                ChoreInstance.assigned_to == user_id,
                ChoreInstance.assigned_to.is_(None)  # Include shared chores
            )
        )

    status = request.args.get('status')
    if status:
        query = query.filter(ChoreInstance.status == status)

    instances = query.all()

    return jsonify({
        'date': today.isoformat(),
        'count': len(instances),
        'instances': [serialize_instance(instance, include_details=True) for instance in instances]
    }), 200


@instances_bp.route('/<int:instance_id>/claim', methods=['POST'])
@ha_auth_required
def claim_instance(instance_id: int):
    """Kid claims completion of a chore instance.

    State transition: assigned → claimed

    Request body:
        {
            "user_id": int (optional, uses current authenticated user if not provided)
        }

    Args:
        instance_id: ID of the chore instance to claim

    Returns:
        JSON: {data: updated_instance, message: str}
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')

    if not user_id:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Could not identify current user'
            }), 401
        user_id = current_user.id

    try:
        instance = InstanceService.claim(instance_id, user_id)
        return jsonify({
            'data': serialize_instance(instance, include_details=True),
            'message': 'Chore claimed successfully'
        }), 200
    except InstanceServiceError as e:
        return jsonify({
            'error': e.__class__.__name__.replace('Error', ' Error'),
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Failed to claim instance {instance_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to claim chore',
            'details': str(e)
        }), 500


@instances_bp.route('/<int:instance_id>/approve', methods=['POST'])
@ha_auth_required
def approve_instance(instance_id: int):
    """Parent approves a claimed chore instance and awards points.

    State transition: claimed → approved

    Request body:
        {
            "approver_id": int (optional, uses current authenticated user if not provided),
            "points": int (optional, uses chore default points if not provided)
        }

    Args:
        instance_id: ID of the chore instance to approve

    Returns:
        JSON: {data: updated_instance, message: str}
    """
    data = request.get_json() or {}
    approver_id = data.get('approver_id')
    custom_points = data.get('points')

    if not approver_id:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Could not identify current user'
            }), 401
        approver_id = current_user.id

    try:
        instance = InstanceService.approve(instance_id, approver_id, custom_points)
        points_awarded = instance.points_awarded or instance.chore.points
        return jsonify({
            'data': serialize_instance(instance, include_details=True),
            'message': f'Chore approved successfully, {points_awarded} points awarded'
        }), 200
    except InstanceServiceError as e:
        return jsonify({
            'error': e.__class__.__name__.replace('Error', ' Error'),
            'message': e.message
        }), e.status_code
    except ValueError as e:
        db.session.rollback()
        return jsonify({
            'error': 'Bad Request',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Failed to approve instance {instance_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to approve chore',
            'details': str(e)
        }), 500


@instances_bp.route('/<int:instance_id>/reject', methods=['POST'])
@ha_auth_required
def reject_instance(instance_id: int):
    """Parent rejects a claimed chore instance with a reason.

    State transition: claimed → rejected
    After rejection, the chore status is set back to 'assigned' to allow re-claim.

    Request body:
        {
            "approver_id": int (optional, uses current authenticated user if not provided),
            "reason": str (required - why the chore was rejected)
        }

    Args:
        instance_id: ID of the chore instance to reject

    Returns:
        JSON: {data: updated_instance, message: str}
    """
    data = request.get_json() or {}
    rejecter_id = data.get('approver_id')
    reason = data.get('reason', '')

    if not rejecter_id:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Could not identify current user'
            }), 401
        rejecter_id = current_user.id

    try:
        instance = InstanceService.reject(instance_id, rejecter_id, reason)
        return jsonify({
            'data': serialize_instance(instance, include_details=True),
            'message': 'Chore rejected. Status set back to "assigned" to allow re-claim.'
        }), 200
    except InstanceServiceError as e:
        return jsonify({
            'error': e.__class__.__name__.replace('Error', ' Error'),
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Failed to reject instance {instance_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to reject chore',
            'details': str(e)
        }), 500


@instances_bp.route('/<int:instance_id>/unclaim', methods=['POST'])
@ha_auth_required
def unclaim_instance(instance_id: int):
    """Unclaim a chore instance (before approval).

    State transition: claimed → assigned

    Request body:
        {
            "user_id": int (optional, uses current authenticated user if not provided)
        }

    Args:
        instance_id: ID of the chore instance to unclaim

    Returns:
        JSON: {data: updated_instance, message: str}
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')

    if not user_id:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Could not identify current user'
            }), 401
        user_id = current_user.id

    try:
        instance = InstanceService.unclaim(instance_id, user_id)
        return jsonify({
            'data': serialize_instance(instance, include_details=True),
            'message': 'Chore unclaimed successfully'
        }), 200
    except InstanceServiceError as e:
        return jsonify({
            'error': e.__class__.__name__.replace('Error', ' Error'),
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Failed to unclaim instance {instance_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to unclaim chore',
            'details': str(e)
        }), 500


@instances_bp.route('/<int:instance_id>/reassign', methods=['POST'])
@ha_auth_required
def reassign_instance(instance_id: int):
    """Reassign a chore instance to a different kid (parents only).

    Request body:
        {
            "new_user_id": int (required),
            "reassigned_by": int (optional, uses current authenticated user if not provided)
        }

    Args:
        instance_id: ID of the chore instance to reassign

    Returns:
        JSON: {data: updated_instance, message: str}
    """
    data = request.get_json() or {}
    new_user_id = data.get('new_user_id')
    reassigned_by = data.get('reassigned_by')

    if not new_user_id:
        return jsonify({
            'error': 'Bad Request',
            'message': 'new_user_id is required'
        }), 400

    if not reassigned_by:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Could not identify current user'
            }), 401
        reassigned_by = current_user.id

    try:
        instance = InstanceService.reassign(instance_id, new_user_id, reassigned_by)
        new_user = db.session.get(User, new_user_id)
        return jsonify({
            'data': serialize_instance(instance, include_details=True),
            'message': f'Chore reassigned to {new_user.username}'
        }), 200
    except InstanceServiceError as e:
        return jsonify({
            'error': e.__class__.__name__.replace('Error', ' Error'),
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Failed to reassign instance {instance_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to reassign chore',
            'details': str(e)
        }), 500


@instances_bp.route('/<int:instance_id>/reset', methods=['POST'])
@ha_auth_required
def reset_instance(instance_id: int):
    """Reset an approved one-time chore instance to allow re-claiming.

    This is only applicable to one-time chores (recurrence_type='none').
    Points already awarded are NOT reversed - the kid keeps them.

    State transition: approved → assigned

    Args:
        instance_id: ID of the chore instance to reset

    Returns:
        JSON: {data: updated_instance, message: str}
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Could not identify current user'
        }), 401

    try:
        instance = InstanceService.reset(instance_id, current_user.id)
        return jsonify({
            'data': serialize_instance(instance, include_details=True),
            'message': 'Chore instance reset successfully. It can now be claimed again.'
        }), 200
    except InstanceServiceError as e:
        return jsonify({
            'error': e.__class__.__name__.replace('Error', ' Error'),
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Failed to reset instance {instance_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to reset chore instance',
            'details': str(e)
        }), 500


# Work-together endpoints

@instances_bp.route('/<int:instance_id>/close-claiming', methods=['POST'])
@ha_auth_required
def close_claiming(instance_id: int):
    """Close claiming for a work-together instance (parent action).

    This allows parents to close claiming early when not all assigned kids
    have claimed. After closing, the parent can approve/reject individual claims.

    Args:
        instance_id: ID of the work-together instance

    Returns:
        JSON: {data: updated_instance, message: str}
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Could not identify current user'
        }), 401

    try:
        instance = InstanceService.close_claiming(instance_id, current_user.id)
        return jsonify({
            'data': serialize_instance(instance, include_details=True),
            'message': 'Claiming closed successfully. You can now approve individual claims.'
        }), 200
    except InstanceServiceError as e:
        return jsonify({
            'error': e.__class__.__name__.replace('Error', ' Error'),
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Failed to close claiming for instance {instance_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to close claiming',
            'details': str(e)
        }), 500


@instances_bp.route('/claims/<int:claim_id>/approve', methods=['POST'])
@ha_auth_required
def approve_claim(claim_id: int):
    """Approve an individual claim for a work-together chore.

    Each kid's claim is approved separately, and each receives full points.

    Request body:
        {
            "points": int (optional, uses chore default points if not provided)
        }

    Args:
        claim_id: ID of the claim to approve

    Returns:
        JSON: {data: claim_details, message: str}
    """
    data = request.get_json() or {}
    custom_points = data.get('points')

    current_user = get_current_user()
    if not current_user:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Could not identify current user'
        }), 401

    try:
        claim = InstanceService.approve_claim(claim_id, current_user.id, custom_points)
        return jsonify({
            'data': claim.to_dict(),
            'message': f'Claim approved, {claim.points_awarded} points awarded to {claim.user.username}'
        }), 200
    except InstanceServiceError as e:
        return jsonify({
            'error': e.__class__.__name__.replace('Error', ' Error'),
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Failed to approve claim {claim_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to approve claim',
            'details': str(e)
        }), 500


@instances_bp.route('/claims/<int:claim_id>/reject', methods=['POST'])
@ha_auth_required
def reject_claim(claim_id: int):
    """Reject an individual claim for a work-together chore.

    Request body:
        {
            "reason": str (required - why the claim was rejected)
        }

    Args:
        claim_id: ID of the claim to reject

    Returns:
        JSON: {data: claim_details, message: str}
    """
    data = request.get_json() or {}
    reason = data.get('reason', '')

    current_user = get_current_user()
    if not current_user:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Could not identify current user'
        }), 401

    try:
        claim = InstanceService.reject_claim(claim_id, current_user.id, reason)
        return jsonify({
            'data': claim.to_dict(),
            'message': f'Claim from {claim.user.username} rejected'
        }), 200
    except InstanceServiceError as e:
        return jsonify({
            'error': e.__class__.__name__.replace('Error', ' Error'),
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Failed to reject claim {claim_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to reject claim',
            'details': str(e)
        }), 500
