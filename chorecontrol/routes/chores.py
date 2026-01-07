"""Chore Management API endpoints for ChoreControl (Stream 2)."""

from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from datetime import datetime, date

from models import db, Chore, ChoreAssignment, ChoreInstance, User
from schemas import validate_recurrence_pattern
from auth import ha_auth_required, get_current_user as auth_get_current_user
from utils.instance_generator import generate_instances_for_chore, regenerate_instances_for_chore
from utils.timezone import local_today
from utils.webhooks import fire_webhook

chores_bp = Blueprint('chores', __name__, url_prefix='/api/chores')


def get_current_user():
    """Get current User object from g.ha_user."""
    return auth_get_current_user()


def _parse_bool(value):
    """Parse a boolean value from various input types.

    Handles:
    - Python booleans: True, False
    - Checkbox strings: 'on', 'off', 'true', 'false', '1', '0'
    - Integers: 1 (True), 0 (False)
    - None/missing: False

    Args:
        value: The value to parse

    Returns:
        bool: Parsed boolean value
    """
    if isinstance(value, bool):
        return value
    if value is None or value == '':
        return False
    if isinstance(value, str):
        return value.lower() in ('on', 'true', '1', 'yes')
    return bool(value)


def _parse_int(value, allow_none=True):
    """Parse an integer value from various input types.

    Handles:
    - Integers: returned as-is
    - Strings: converted to int
    - None/empty string: returns None if allow_none, otherwise 0
    - Float: converted to int

    Args:
        value: The value to parse
        allow_none: Whether to allow None as a return value

    Returns:
        int or None: Parsed integer value

    Raises:
        ValueError: If value cannot be converted to int
    """
    if value is None or value == '':
        return None if allow_none else 0
    if isinstance(value, int):
        return value
    if isinstance(value, (str, float)):
        return int(value)
    raise ValueError(f"Cannot convert {type(value).__name__} to int")


def error_response(message, status_code=400, details=None):
    """Generate consistent error response."""
    response = {
        'error': 'ValidationError' if status_code == 400 else 'Error',
        'message': message
    }
    if details:
        response['details'] = details
    return jsonify(response), status_code


def success_response(data, message="Success", status_code=200):
    """Generate consistent success response."""
    return jsonify({
        'data': data,
        'message': message
    }), status_code


def serialize_chore(chore, include_assignments=True, include_counts=False):
    """Serialize a Chore object to dictionary."""
    result = {
        'id': chore.id,
        'name': chore.name,
        'description': chore.description,
        'points': chore.points,
        'recurrence_type': chore.recurrence_type,
        'recurrence_pattern': chore.recurrence_pattern,
        'start_date': chore.start_date.isoformat() if chore.start_date else None,
        'end_date': chore.end_date.isoformat() if chore.end_date else None,
        'assignment_type': chore.assignment_type,
        'allow_work_together': chore.allow_work_together,
        'extra': chore.extra,
        'requires_approval': chore.requires_approval,
        'auto_approve_after_hours': chore.auto_approve_after_hours,
        'allow_late_claims': chore.allow_late_claims,
        'late_points': chore.late_points,
        'is_active': chore.is_active,
        'created_by': chore.created_by,
        'created_at': chore.created_at.isoformat() if chore.created_at else None,
        'updated_at': chore.updated_at.isoformat() if chore.updated_at else None
    }

    if include_assignments and chore.assignments:
        result['assignments'] = [
            {
                'id': a.id,
                'user_id': a.user_id,
                'username': a.user.username if a.user else None,
                'due_date': a.due_date.isoformat() if a.due_date else None
            }
            for a in chore.assignments
        ]

    if include_counts:
        result['assignment_count'] = len(chore.assignments) if chore.assignments else 0
        result['instance_count'] = len(chore.instances) if chore.instances else 0

    return result


@chores_bp.route('', methods=['GET'])
@ha_auth_required
def list_chores():
    """
    GET /api/chores - List all chores with optional filters.

    Query Parameters:
    - active (bool): Filter by is_active status (default: True)
    - assigned_to (int): Filter by user_id assigned to chore
    - recurrence_type (str): Filter by recurrence type (none, simple, complex)
    - limit (int): Number of results per page (default: 50)
    - offset (int): Offset for pagination (default: 0)
    """
    try:
        # Parse query parameters
        active = request.args.get('active', 'true').lower() == 'true'
        assigned_to = request.args.get('assigned_to', type=int)
        recurrence_type = request.args.get('recurrence_type')
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Validate limit
        if limit > 100:
            limit = 100

        # Build query with eager loading
        query = Chore.query.options(
            joinedload(Chore.assignments).joinedload(ChoreAssignment.user)
        )

        # Apply filters
        if active is not None:
            query = query.filter(Chore.is_active == active)

        if assigned_to:
            query = query.join(Chore.assignments).filter(
                ChoreAssignment.user_id == assigned_to
            )

        if recurrence_type:
            if recurrence_type not in ['none', 'simple', 'complex']:
                return error_response("Invalid recurrence_type. Must be 'none', 'simple', or 'complex'")
            query = query.filter(Chore.recurrence_type == recurrence_type)

        # Get total count
        total = query.count()

        # Apply pagination and fetch
        chores = query.order_by(Chore.created_at.desc()).limit(limit).offset(offset).all()

        # Serialize results
        chores_data = [serialize_chore(chore, include_assignments=True, include_counts=True) for chore in chores]

        return jsonify({
            'data': chores_data,
            'total': total,
            'limit': limit,
            'offset': offset,
            'message': f'Retrieved {len(chores_data)} chore(s)'
        }), 200

    except Exception as e:
        return error_response(f"Failed to retrieve chores: {str(e)}", 500)


@chores_bp.route('', methods=['POST'])
@ha_auth_required
def create_chore():
    """
    POST /api/chores - Create a new chore.

    Request Body:
    {
        "name": "Take out trash",
        "description": "Roll bins to curb",
        "points": 5,
        "recurrence_type": "simple",
        "recurrence_pattern": {"type": "simple", "interval": "weekly", "every_n": 1},
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "assignment_type": "individual",
        "requires_approval": true,
        "auto_approve_after_hours": null,
        "assignments": [
            {"user_id": 2},
            {"user_id": 3}
        ]
    }
    """
    try:
        data = request.get_json()

        if not data:
            return error_response("Request body is required")

        # Validate required fields
        if 'name' not in data:
            return error_response("Field 'name' is required")

        if 'points' not in data:
            return error_response("Field 'points' is required")

        # Validate recurrence pattern if provided
        if 'recurrence_pattern' in data and data['recurrence_pattern']:
            is_valid, error_msg = validate_recurrence_pattern(data['recurrence_pattern'])
            if not is_valid:
                return error_response(f"Invalid recurrence pattern: {error_msg}")

        # Validate recurrence_type
        if 'recurrence_type' in data and data['recurrence_type']:
            if data['recurrence_type'] not in ['none', 'simple', 'complex']:
                return error_response("recurrence_type must be 'none', 'simple', or 'complex'")

        # Validate assignment_type
        if 'assignment_type' in data and data['assignment_type']:
            if data['assignment_type'] not in ['individual', 'shared']:
                return error_response("assignment_type must be 'individual' or 'shared'")

        # Validate and convert numeric fields (form data comes as strings)
        if data.get('late_points') is not None and data.get('late_points') != '':
            try:
                data['late_points'] = int(data['late_points'])
                if data['late_points'] < 0:
                    return error_response('late_points must be non-negative')
            except (ValueError, TypeError):
                return error_response('late_points must be a valid integer')
        elif data.get('late_points') == '':
            data['late_points'] = None

        if data.get('early_claim_days') is not None and data.get('early_claim_days') != '':
            try:
                data['early_claim_days'] = int(data['early_claim_days'])
                if data['early_claim_days'] < 0:
                    return error_response('early_claim_days must be non-negative')
            except (ValueError, TypeError):
                return error_response('early_claim_days must be a valid integer')
        elif data.get('early_claim_days') == '':
            data['early_claim_days'] = 0

        if data.get('grace_period_days') is not None and data.get('grace_period_days') != '':
            try:
                data['grace_period_days'] = int(data['grace_period_days'])
                if data['grace_period_days'] < 0:
                    return error_response('grace_period_days must be non-negative')
            except (ValueError, TypeError):
                return error_response('grace_period_days must be a valid integer')
        elif data.get('grace_period_days') == '':
            data['grace_period_days'] = 0

        if data.get('expires_after_days') is not None and data.get('expires_after_days') != '':
            try:
                data['expires_after_days'] = int(data['expires_after_days'])
                if data['expires_after_days'] < 1:
                    return error_response('expires_after_days must be at least 1')
            except (ValueError, TypeError):
                return error_response('expires_after_days must be a valid integer')
        elif data.get('expires_after_days') == '':
            data['expires_after_days'] = None

        # Get current user for created_by
        current_user = get_current_user()

        # Create chore object
        chore = Chore(
            name=data['name'],
            description=data.get('description'),
            points=_parse_int(data['points'], allow_none=False),
            recurrence_type=data.get('recurrence_type'),
            recurrence_pattern=data.get('recurrence_pattern'),
            start_date=datetime.fromisoformat(data['start_date']).date() if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']).date() if data.get('end_date') else None,
            assignment_type=data.get('assignment_type'),
            allow_work_together=_parse_bool(data.get('allow_work_together', False)),
            extra=_parse_bool(data.get('extra', False)),
            requires_approval=_parse_bool(data.get('requires_approval', True)),
            auto_approve_after_hours=_parse_int(data.get('auto_approve_after_hours')),
            allow_late_claims=data.get('allow_late_claims', False),
            late_points=_parse_int(data.get('late_points')),
            early_claim_days=_parse_int(data.get('early_claim_days', 0), allow_none=False),
            grace_period_days=_parse_int(data.get('grace_period_days', 0), allow_none=False),
            expires_after_days=_parse_int(data.get('expires_after_days')),
            created_by=current_user.id if current_user else None
        )

        db.session.add(chore)
        db.session.flush()  # Get chore.id before creating assignments

        # Create assignments if provided
        # Support both formats:
        # - assigned_to: [1, 2, 3] (from web UI form)
        # - assignments: [{user_id: 1}, {user_id: 2}] (from API)
        assignment_user_ids = []

        if 'assigned_to' in data and data['assigned_to']:
            # Web UI format: array of user IDs
            assignment_user_ids = data['assigned_to']
        elif 'assignments' in data and data['assignments']:
            # API format: array of objects with user_id
            for assignment_data in data['assignments']:
                if 'user_id' not in assignment_data:
                    db.session.rollback()
                    return error_response("Each assignment must have 'user_id'")
                assignment_user_ids.append(assignment_data['user_id'])

        for user_id in assignment_user_ids:
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                db.session.rollback()
                return error_response(f"User {user_id} not found")

            assignment = ChoreAssignment(
                chore_id=chore.id,
                user_id=user_id
            )
            db.session.add(assignment)

        db.session.commit()

        # Generate instances for the chore
        today = local_today()
        instances = generate_instances_for_chore(chore)

        # Fire webhooks for instances due today
        for instance in instances:
            if instance.due_date == today or instance.due_date is None:
                fire_webhook('chore_instance_created', instance)

        # Reload with relationships
        chore = Chore.query.options(
            joinedload(Chore.assignments).joinedload(ChoreAssignment.user)
        ).get(chore.id)

        return success_response(
            serialize_chore(chore, include_assignments=True),
            "Chore created successfully",
            201
        )

    except ValueError as e:
        db.session.rollback()
        return error_response(f"Invalid date format: {str(e)}")
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to create chore: {str(e)}", 500)


@chores_bp.route('/<int:chore_id>', methods=['GET'])
@ha_auth_required
def get_chore(chore_id):
    """
    GET /api/chores/{id} - Get chore details with assignments and instance counts.
    """
    try:
        # Query with eager loading
        chore = Chore.query.options(
            joinedload(Chore.assignments).joinedload(ChoreAssignment.user),
            joinedload(Chore.instances)
        ).get(chore_id)

        if not chore:
            return error_response(f"Chore {chore_id} not found", 404)

        return success_response(
            serialize_chore(chore, include_assignments=True, include_counts=True),
            "Chore retrieved successfully"
        )

    except Exception as e:
        return error_response(f"Failed to retrieve chore: {str(e)}", 500)


@chores_bp.route('/<int:chore_id>', methods=['PUT', 'POST'])
@ha_auth_required
def update_chore(chore_id):
    """
    PUT /api/chores/{id} - Update a chore.

    Request Body: Partial chore object with fields to update.
    """
    try:
        chore = Chore.query.get(chore_id)

        if not chore:
            return error_response(f"Chore {chore_id} not found", 404)

        data = request.get_json(silent=True)

        if not data:
            return error_response("Request body is required")

        # Update simple fields
        if 'name' in data:
            chore.name = data['name']

        if 'description' in data:
            chore.description = data['description']

        if 'points' in data:
            chore.points = _parse_int(data['points'], allow_none=False)

        # Update recurrence_type
        if 'recurrence_type' in data:
            if data['recurrence_type'] not in ['none', 'simple', 'complex', None]:
                return error_response("recurrence_type must be 'none', 'simple', or 'complex'")
            chore.recurrence_type = data['recurrence_type']

        # Check if recurrence pattern is changing
        pattern_changed = False
        if 'recurrence_type' in data and data['recurrence_type'] != chore.recurrence_type:
            pattern_changed = True
        if 'recurrence_pattern' in data and data['recurrence_pattern'] != chore.recurrence_pattern:
            pattern_changed = True

        # Update recurrence_pattern with validation
        if 'recurrence_pattern' in data:
            if data['recurrence_pattern']:
                is_valid, error_msg = validate_recurrence_pattern(data['recurrence_pattern'])
                if not is_valid:
                    return error_response(f"Invalid recurrence pattern: {error_msg}")
            chore.recurrence_pattern = data['recurrence_pattern']

        # Update dates
        if 'start_date' in data:
            chore.start_date = datetime.fromisoformat(data['start_date']).date() if data['start_date'] else None

        if 'end_date' in data:
            chore.end_date = datetime.fromisoformat(data['end_date']).date() if data['end_date'] else None

        # Update assignment_type
        if 'assignment_type' in data:
            if data['assignment_type'] not in ['individual', 'shared', None]:
                return error_response("assignment_type must be 'individual' or 'shared'")
            chore.assignment_type = data['assignment_type']

        # Update allow_work_together (only valid for shared chores)
        if 'allow_work_together' in data:
            chore.allow_work_together = _parse_bool(data['allow_work_together'])

        # Update extra field
        if 'extra' in data:
            chore.extra = _parse_bool(data['extra'])

        # Update workflow fields
        if 'requires_approval' in data:
            chore.requires_approval = _parse_bool(data['requires_approval'])

        if 'auto_approve_after_hours' in data:
            chore.auto_approve_after_hours = _parse_int(data['auto_approve_after_hours'])

        if 'allow_late_claims' in data:
            chore.allow_late_claims = data['allow_late_claims']

        if 'late_points' in data:
            try:
                parsed_value = _parse_int(data['late_points'])
                if parsed_value is not None and parsed_value < 0:
                    return error_response('late_points must be non-negative')
                chore.late_points = parsed_value
            except (ValueError, TypeError):
                return error_response('late_points must be a valid integer')

        if 'early_claim_days' in data:
            try:
                parsed_value = _parse_int(data['early_claim_days'], allow_none=False)
                if parsed_value < 0:
                    return error_response('early_claim_days must be non-negative')
                chore.early_claim_days = parsed_value
            except (ValueError, TypeError):
                return error_response('early_claim_days must be a valid integer')

        if 'grace_period_days' in data:
            try:
                parsed_value = _parse_int(data['grace_period_days'], allow_none=False)
                if parsed_value < 0:
                    return error_response('grace_period_days must be non-negative')
                chore.grace_period_days = parsed_value
            except (ValueError, TypeError):
                return error_response('grace_period_days must be a valid integer')

        if 'expires_after_days' in data:
            try:
                parsed_value = _parse_int(data['expires_after_days'])
                if parsed_value is not None and parsed_value < 1:
                    return error_response('expires_after_days must be at least 1')
                chore.expires_after_days = parsed_value
            except (ValueError, TypeError):
                return error_response('expires_after_days must be a valid integer')

        if 'is_active' in data:
            chore.is_active = data['is_active']

        # Update assignments if provided
        # Support both formats:
        # - assigned_to: [1, 2, 3] (from web UI form)
        # - assignments: [{user_id: 1}, {user_id: 2}] (from API)
        assignment_user_ids = None

        if 'assigned_to' in data:
            # Web UI format: array of user IDs
            assignment_user_ids = data['assigned_to'] if data['assigned_to'] else []
        elif 'assignments' in data:
            # API format: array of objects with user_id
            assignment_user_ids = []
            for assignment_data in data['assignments']:
                if 'user_id' not in assignment_data:
                    return error_response("Each assignment must have 'user_id'")
                assignment_user_ids.append(assignment_data['user_id'])

        if assignment_user_ids is not None:
            # Clear existing assignments
            ChoreAssignment.query.filter_by(chore_id=chore.id).delete()

            # Add new assignments
            for user_id in assignment_user_ids:
                # Verify user exists
                user = User.query.get(user_id)
                if not user:
                    db.session.rollback()
                    return error_response(f"User {user_id} not found")

                assignment = ChoreAssignment(
                    chore_id=chore.id,
                    user_id=user_id
                )
                db.session.add(assignment)

            # Mark pattern as changed to regenerate instances with new assignments
            pattern_changed = True

        # Update timestamp
        chore.updated_at = datetime.utcnow()

        db.session.commit()

        # Regenerate instances if pattern changed
        if pattern_changed:
            today = local_today()
            instances = regenerate_instances_for_chore(chore)

            # Fire webhooks for new instances due today
            for instance in instances:
                if instance.due_date == today or instance.due_date is None:
                    fire_webhook('chore_instance_created', instance)

        # Reload with relationships
        chore = Chore.query.options(
            joinedload(Chore.assignments).joinedload(ChoreAssignment.user)
        ).get(chore_id)

        return success_response(
            serialize_chore(chore, include_assignments=True, include_counts=True),
            "Chore updated successfully"
        )

    except ValueError as e:
        db.session.rollback()
        return error_response(f"Invalid date format: {str(e)}")
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to update chore: {str(e)}", 500)


@chores_bp.route('/<int:chore_id>', methods=['DELETE'])
@ha_auth_required
def delete_chore(chore_id):
    """
    DELETE /api/chores/{id} - Soft delete a chore (set is_active=False).

    Note: This does not delete the database record or associated instances.
    """
    try:
        chore = Chore.query.get(chore_id)

        if not chore:
            return error_response(f"Chore {chore_id} not found", 404)

        # Soft delete - just mark as inactive
        chore.is_active = False
        chore.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'message': f'Chore {chore_id} deactivated successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to delete chore: {str(e)}", 500)


@chores_bp.route('/<int:chore_id>/permanent', methods=['DELETE'])
@ha_auth_required
def permanently_delete_chore(chore_id):
    """
    DELETE /api/chores/{id}/permanent - Permanently delete a chore and all its data.

    This performs a hard delete, removing:
    - The chore record
    - All associated chore instances
    - All chore assignments

    Use with caution - this cannot be undone.
    """
    try:
        chore = Chore.query.get(chore_id)

        if not chore:
            return error_response(f"Chore {chore_id} not found", 404)

        chore_name = chore.name

        # Delete all associated instances first
        ChoreInstance.query.filter_by(chore_id=chore_id).delete()

        # Delete all assignments
        ChoreAssignment.query.filter_by(chore_id=chore_id).delete()

        # Delete the chore itself
        db.session.delete(chore)
        db.session.commit()

        return jsonify({
            'message': f'Chore "{chore_name}" permanently deleted'
        }), 200

    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to permanently delete chore: {str(e)}", 500)


@chores_bp.route('/<int:chore_id>/instances', methods=['GET'])
@ha_auth_required
def get_chore_instances(chore_id):
    """
    GET /api/chores/{id}/instances - Get all instances for a chore with pagination.

    Query Parameters:
    - status (str): Filter by status (assigned, claimed, approved, rejected)
    - limit (int): Number of results per page (default: 50)
    - offset (int): Offset for pagination (default: 0)
    """
    try:
        # Verify chore exists
        chore = Chore.query.get(chore_id)
        if not chore:
            return error_response(f"Chore {chore_id} not found", 404)

        # Parse query parameters
        status = request.args.get('status')
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Validate limit
        if limit > 100:
            limit = 100

        # Build query
        query = ChoreInstance.query.filter_by(chore_id=chore_id).options(
            joinedload(ChoreInstance.chore),
            joinedload(ChoreInstance.claimer),
            joinedload(ChoreInstance.approver)
        )

        # Apply status filter
        if status:
            if status not in ['assigned', 'claimed', 'approved', 'rejected']:
                return error_response("Invalid status. Must be 'assigned', 'claimed', 'approved', or 'rejected'")
            query = query.filter(ChoreInstance.status == status)

        # Get total count
        total = query.count()

        # Apply pagination and fetch
        instances = query.order_by(ChoreInstance.due_date.desc()).limit(limit).offset(offset).all()

        # Serialize instances
        instances_data = [
            {
                'id': instance.id,
                'chore_id': instance.chore_id,
                'chore_name': instance.chore.name if instance.chore else None,
                'due_date': instance.due_date.isoformat() if instance.due_date else None,
                'status': instance.status,
                'claimed_by': instance.claimed_by,
                'claimed_by_username': instance.claimer.username if instance.claimer else None,
                'claimed_at': instance.claimed_at.isoformat() if instance.claimed_at else None,
                'approved_by': instance.approved_by,
                'approved_by_username': instance.approver.username if instance.approver else None,
                'approved_at': instance.approved_at.isoformat() if instance.approved_at else None,
                'rejected_by': instance.rejected_by,
                'rejected_at': instance.rejected_at.isoformat() if instance.rejected_at else None,
                'rejection_reason': instance.rejection_reason,
                'points_awarded': instance.points_awarded
            }
            for instance in instances
        ]

        return jsonify({
            'data': instances_data,
            'total': total,
            'limit': limit,
            'offset': offset,
            'message': f'Retrieved {len(instances_data)} instance(s) for chore {chore_id}'
        }), 200

    except Exception as e:
        return error_response(f"Failed to retrieve chore instances: {str(e)}", 500)
