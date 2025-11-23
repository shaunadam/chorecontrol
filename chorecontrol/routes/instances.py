"""Instance Workflow API routes - Stream 3.

This module implements the core chore instance workflow:
- Listing and viewing instances
- Claiming chores (kid marks as complete)
- Approving chores (parent awards points)
- Rejecting chores (parent rejects with reason, allows re-claim)

State machine: assigned → claimed → approved/rejected
After rejection: rejected → assigned (can re-claim)
"""

from datetime import datetime, date
from flask import Blueprint, jsonify, request, g
from sqlalchemy import and_, or_
from models import db, ChoreInstance, User, Chore, ChoreAssignment
from auth import ha_auth_required, get_current_user as auth_get_current_user
from utils.webhooks import fire_webhook

instances_bp = Blueprint('instances', __name__, url_prefix='/api/instances')


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
        'created_at': instance.created_at.isoformat() if instance.created_at else None,
        'updated_at': instance.updated_at.isoformat() if instance.updated_at else None
    }

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
    today = date.today()

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
    instance = ChoreInstance.query.get(instance_id)

    if not instance:
        return jsonify({
            'error': 'Not Found',
            'message': f'Chore instance {instance_id} not found'
        }), 404

    # Get user_id from request body or use current authenticated user
    data = request.get_json() or {}
    user_id = data.get('user_id')

    if not user_id:
        # Use current authenticated user
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Could not identify current user'
            }), 401
        user_id = current_user.id

    # Check if user can claim this instance
    if not instance.can_claim(user_id):
        # Determine specific reason for failure
        if instance.status != 'assigned':
            return jsonify({
                'error': 'Bad Request',
                'message': f'Cannot claim chore with status "{instance.status}". Only "assigned" chores can be claimed.'
            }), 400
        else:
            # Check if user is assigned
            assignment = ChoreAssignment.query.filter_by(
                chore_id=instance.chore_id,
                user_id=user_id
            ).first()

            if not assignment:
                return jsonify({
                    'error': 'Forbidden',
                    'message': 'You are not assigned to this chore'
                }), 403

    # Claim the instance
    instance.status = 'claimed'
    instance.claimed_by = user_id
    instance.claimed_at = datetime.utcnow()

    # Check if late (claimed after due_date)
    if instance.due_date and datetime.utcnow().date() > instance.due_date:
        instance.claimed_late = True
    else:
        instance.claimed_late = False

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to claim chore',
            'details': str(e)
        }), 500

    # Fire webhook
    fire_webhook('chore_instance_claimed', instance)

    return jsonify({
        'data': serialize_instance(instance, include_details=True),
        'message': 'Chore claimed successfully'
    }), 200


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
    instance = ChoreInstance.query.get(instance_id)

    if not instance:
        return jsonify({
            'error': 'Not Found',
            'message': f'Chore instance {instance_id} not found'
        }), 404

    # Get approver_id from request body or use current authenticated user
    data = request.get_json() or {}
    approver_id = data.get('approver_id')
    custom_points = data.get('points')

    if not approver_id:
        # Use current authenticated user
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Could not identify current user'
            }), 401
        approver_id = current_user.id

    # Check if user can approve this instance
    if not instance.can_approve(approver_id):
        # Determine specific reason for failure
        if instance.status != 'claimed':
            return jsonify({
                'error': 'Bad Request',
                'message': f'Cannot approve chore with status "{instance.status}". Only "claimed" chores can be approved.'
            }), 400
        else:
            # Check if user is a parent
            user = User.query.get(approver_id)
            if not user or user.role != 'parent':
                return jsonify({
                    'error': 'Forbidden',
                    'message': 'Only parents can approve chores'
                }), 403

    # Award points using the model's method (handles everything)
    try:
        instance.award_points(approver_id, custom_points)
        db.session.commit()
    except ValueError as e:
        db.session.rollback()
        return jsonify({
            'error': 'Bad Request',
            'message': str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to approve chore',
            'details': str(e)
        }), 500

    points_awarded = instance.points_awarded or instance.chore.points

    # Fire webhooks
    fire_webhook('chore_instance_approved', instance)
    fire_webhook('points_awarded', instance)

    return jsonify({
        'data': serialize_instance(instance, include_details=True),
        'message': f'Chore approved successfully, {points_awarded} points awarded'
    }), 200


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
    instance = ChoreInstance.query.get(instance_id)

    if not instance:
        return jsonify({
            'error': 'Not Found',
            'message': f'Chore instance {instance_id} not found'
        }), 404

    # Get data from request body
    data = request.get_json() or {}
    approver_id = data.get('approver_id')
    reason = data.get('reason')

    if not approver_id:
        # Use current authenticated user
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Could not identify current user'
            }), 401
        approver_id = current_user.id

    # Validate reason is provided
    if not reason or not reason.strip():
        return jsonify({
            'error': 'Bad Request',
            'message': 'Rejection reason is required'
        }), 400

    # Check if user can reject (must be a parent and chore must be claimed)
    if instance.status != 'claimed':
        return jsonify({
            'error': 'Bad Request',
            'message': f'Cannot reject chore with status "{instance.status}". Only "claimed" chores can be rejected.'
        }), 400

    user = User.query.get(approver_id)
    if not user or user.role != 'parent':
        return jsonify({
            'error': 'Forbidden',
            'message': 'Only parents can reject chores'
        }), 403

    # Reject the instance and set back to assigned (allow re-claim)
    instance.status = 'assigned'
    instance.rejected_by = approver_id
    instance.rejected_at = datetime.utcnow()
    instance.rejection_reason = reason.strip()

    # Clear claim data to allow re-claim
    instance.claimed_by = None
    instance.claimed_at = None

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to reject chore',
            'details': str(e)
        }), 500

    # Fire webhook
    fire_webhook('chore_instance_rejected', instance)

    return jsonify({
        'data': serialize_instance(instance, include_details=True),
        'message': 'Chore rejected. Status set back to "assigned" to allow re-claim.'
    }), 200


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
    instance = ChoreInstance.query.get(instance_id)

    if not instance:
        return jsonify({
            'error': 'Not Found',
            'message': f'Chore instance {instance_id} not found'
        }), 404

    # Get user_id from request body or use current authenticated user
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

    # Validate ownership
    if instance.claimed_by != user_id:
        return jsonify({
            'error': 'Forbidden',
            'message': 'Not your claim'
        }), 403

    if instance.status != 'claimed':
        return jsonify({
            'error': 'Bad Request',
            'message': 'Can only unclaim pending instances'
        }), 400

    # Unclaim
    instance.status = 'assigned'
    instance.claimed_by = None
    instance.claimed_at = None
    instance.claimed_late = False

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to unclaim chore',
            'details': str(e)
        }), 500

    return jsonify({
        'data': serialize_instance(instance, include_details=True),
        'message': 'Chore unclaimed successfully'
    }), 200


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
    instance = ChoreInstance.query.get(instance_id)

    if not instance:
        return jsonify({
            'error': 'Not Found',
            'message': f'Chore instance {instance_id} not found'
        }), 404

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

    # Validate reassigner is a parent
    reassigner = User.query.get(reassigned_by)
    if not reassigner or reassigner.role != 'parent':
        return jsonify({
            'error': 'Forbidden',
            'message': 'Only parents can reassign chores'
        }), 403

    if instance.status != 'assigned':
        return jsonify({
            'error': 'Bad Request',
            'message': 'Can only reassign unclaimed instances'
        }), 400

    if instance.chore.assignment_type != 'individual':
        return jsonify({
            'error': 'Bad Request',
            'message': 'Can only reassign individual chores'
        }), 400

    new_user = User.query.get(new_user_id)
    if not new_user or new_user.role != 'kid':
        return jsonify({
            'error': 'Bad Request',
            'message': 'New assignee must be a kid'
        }), 400

    # Reassign
    instance.assigned_to = new_user_id

    # Ensure ChoreAssignment exists
    assignment = ChoreAssignment.query.filter_by(
        chore_id=instance.chore_id,
        user_id=new_user_id
    ).first()

    if not assignment:
        assignment = ChoreAssignment(
            chore_id=instance.chore_id,
            user_id=new_user_id
        )
        db.session.add(assignment)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to reassign chore',
            'details': str(e)
        }), 500

    return jsonify({
        'data': serialize_instance(instance, include_details=True),
        'message': f'Chore reassigned to {new_user.username}'
    }), 200
