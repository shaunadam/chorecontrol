"""Instance workflow service.

This module contains the business logic for chore instance operations:
- Claiming chores
- Approving chores (with points awarding)
- Rejecting chores
- Resetting one-time chores

Routes should delegate to this service and handle HTTP responses.
"""

import logging
from datetime import datetime
from typing import Optional

from models import db, ChoreInstance, ChoreInstanceClaim, User, ChoreAssignment
from utils.timezone import local_today
from utils.webhooks import fire_webhook

logger = logging.getLogger(__name__)


class InstanceServiceError(Exception):
    """Base exception for instance service errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(InstanceServiceError):
    def __init__(self, message: str):
        super().__init__(message, 404)


class ForbiddenError(InstanceServiceError):
    def __init__(self, message: str):
        super().__init__(message, 403)


class BadRequestError(InstanceServiceError):
    def __init__(self, message: str):
        super().__init__(message, 400)


class InstanceService:
    """Service for managing chore instance workflow."""

    @staticmethod
    def get_instance(instance_id: int) -> ChoreInstance:
        """Get an instance by ID or raise NotFoundError."""
        instance = db.session.get(ChoreInstance, instance_id)
        if not instance:
            raise NotFoundError(f'Chore instance {instance_id} not found')
        return instance

    @staticmethod
    def claim(instance_id: int, user_id: int) -> ChoreInstance:
        """Claim a chore instance for a user.

        Args:
            instance_id: ID of the instance to claim
            user_id: ID of the user claiming the chore

        Returns:
            The updated ChoreInstance

        Raises:
            NotFoundError: Instance not found
            BadRequestError: Instance cannot be claimed (wrong status)
            ForbiddenError: User not assigned to this chore
        """
        instance = InstanceService.get_instance(instance_id)

        logger.info(f"Claim request: instance={instance_id}, user={user_id}, status={instance.status}")

        # Handle work-together chores differently
        if instance.is_work_together():
            return InstanceService._claim_work_together(instance, user_id)

        if not instance.can_claim(user_id):
            if instance.status != 'assigned':
                raise BadRequestError(
                    f'Cannot claim chore with status "{instance.status}". '
                    'Only "assigned" chores can be claimed.'
                )
            else:
                assignment = ChoreAssignment.query.filter_by(
                    chore_id=instance.chore_id,
                    user_id=user_id
                ).first()

                if not assignment:
                    raise ForbiddenError('You are not assigned to this chore')

        instance.status = 'claimed'
        instance.claimed_by = user_id
        instance.claimed_at = datetime.utcnow()

        if instance.due_date and local_today() > instance.due_date:
            instance.claimed_late = True
        else:
            instance.claimed_late = False

        db.session.commit()
        logger.info(f"Successfully claimed instance {instance_id}")

        try:
            fire_webhook('chore_instance_claimed', instance)
        except Exception as e:
            logger.error(f"Failed to fire webhook: {e}")

        return instance

    @staticmethod
    def _claim_work_together(instance: ChoreInstance, user_id: int) -> ChoreInstance:
        """Claim a work-together chore instance.

        Creates a ChoreInstanceClaim record instead of claiming the instance directly.
        """
        if instance.claiming_closed_at is not None:
            raise BadRequestError('Claiming is closed for this chore')

        # Check if user already claimed
        existing = ChoreInstanceClaim.query.filter_by(
            chore_instance_id=instance.id,
            user_id=user_id
        ).first()
        if existing:
            raise BadRequestError('You have already claimed this chore')

        # Verify user is assigned
        if not instance._is_user_assigned(user_id):
            raise ForbiddenError('You are not assigned to this chore')

        # Determine if late
        is_late = instance.due_date and local_today() > instance.due_date

        # Create claim record
        claim = ChoreInstanceClaim(
            chore_instance_id=instance.id,
            user_id=user_id,
            claimed_at=datetime.utcnow(),
            claimed_late=is_late,
            status='claimed'
        )
        db.session.add(claim)
        db.session.flush()  # Flush so claim appears in instance.claims relationship

        # Check if should auto-close (all assigned kids have claimed)
        instance.check_auto_close_claiming()

        db.session.commit()
        logger.info(f"Work-together claim created for instance {instance.id} by user {user_id}")

        try:
            fire_webhook('chore_instance_claimed', instance, {'claim': claim.to_dict()})
        except Exception as e:
            logger.error(f"Failed to fire webhook: {e}")

        return instance

    @staticmethod
    def approve(instance_id: int, approver_id: int, custom_points: Optional[int] = None) -> ChoreInstance:
        """Approve a claimed chore instance and award points.

        Args:
            instance_id: ID of the instance to approve
            approver_id: ID of the parent approving
            custom_points: Optional override for points to award

        Returns:
            The updated ChoreInstance

        Raises:
            NotFoundError: Instance not found
            BadRequestError: Instance cannot be approved (wrong status)
            ForbiddenError: User is not a parent
        """
        instance = InstanceService.get_instance(instance_id)

        if not instance.can_approve(approver_id):
            if instance.status != 'claimed':
                raise BadRequestError(
                    f'Cannot approve chore with status "{instance.status}". '
                    'Only "claimed" chores can be approved.'
                )
            else:
                user = db.session.get(User, approver_id)
                if not user or user.role != 'parent':
                    raise ForbiddenError('Only parents can approve chores')

        instance.award_points(approver_id, custom_points)
        db.session.commit()

        fire_webhook('chore_instance_approved', instance)
        fire_webhook('points_awarded', instance)

        return instance

    @staticmethod
    def reject(instance_id: int, rejecter_id: int, reason: str) -> ChoreInstance:
        """Reject a claimed chore instance.

        After rejection, status is set back to 'assigned' to allow re-claim.

        Args:
            instance_id: ID of the instance to reject
            rejecter_id: ID of the parent rejecting
            reason: Reason for rejection (required)

        Returns:
            The updated ChoreInstance

        Raises:
            NotFoundError: Instance not found
            BadRequestError: Invalid status or missing reason
            ForbiddenError: User is not a parent
        """
        instance = InstanceService.get_instance(instance_id)

        if not reason or not reason.strip():
            raise BadRequestError('Rejection reason is required')

        if instance.status != 'claimed':
            raise BadRequestError(
                f'Cannot reject chore with status "{instance.status}". '
                'Only "claimed" chores can be rejected.'
            )

        user = db.session.get(User, rejecter_id)
        if not user or user.role != 'parent':
            raise ForbiddenError('Only parents can reject chores')

        instance.status = 'assigned'
        instance.rejected_by = rejecter_id
        instance.rejected_at = datetime.utcnow()
        instance.rejection_reason = reason.strip()
        instance.claimed_by = None
        instance.claimed_at = None

        db.session.commit()

        fire_webhook('chore_instance_rejected', instance)

        return instance

    @staticmethod
    def unclaim(instance_id: int, user_id: int) -> ChoreInstance:
        """Unclaim a chore instance (before approval).

        Args:
            instance_id: ID of the instance to unclaim
            user_id: ID of the user unclaiming

        Returns:
            The updated ChoreInstance

        Raises:
            NotFoundError: Instance not found
            BadRequestError: Instance not in claimed status
            ForbiddenError: User did not claim this instance
        """
        instance = InstanceService.get_instance(instance_id)

        if instance.claimed_by != user_id:
            raise ForbiddenError('Not your claim')

        if instance.status != 'claimed':
            raise BadRequestError('Can only unclaim pending instances')

        instance.status = 'assigned'
        instance.claimed_by = None
        instance.claimed_at = None
        instance.claimed_late = False

        db.session.commit()

        return instance

    @staticmethod
    def reset(instance_id: int, user_id: int) -> ChoreInstance:
        """Reset an approved one-time chore instance to allow re-claiming.

        Points already awarded are NOT reversed.

        Args:
            instance_id: ID of the instance to reset
            user_id: ID of the parent resetting

        Returns:
            The updated ChoreInstance

        Raises:
            NotFoundError: Instance not found
            BadRequestError: Instance not approved or not a one-time chore
            ForbiddenError: User is not a parent
        """
        instance = InstanceService.get_instance(instance_id)

        user = db.session.get(User, user_id)
        if not user or user.role != 'parent':
            raise ForbiddenError('Only parents can reset chore instances')

        if instance.status != 'approved':
            raise BadRequestError(
                f'Cannot reset instance with status "{instance.status}". '
                'Only approved instances can be reset.'
            )

        if instance.chore.recurrence_type != 'none':
            raise BadRequestError(
                'Only one-time chores can be reset. '
                'Recurring chores generate new instances automatically.'
            )

        instance.status = 'assigned'
        instance.claimed_by = None
        instance.claimed_at = None
        instance.claimed_late = False
        instance.approved_by = None
        instance.approved_at = None

        db.session.commit()

        fire_webhook('chore_instance_reset', instance)

        return instance

    @staticmethod
    def reassign(instance_id: int, new_user_id: int, reassigned_by_id: int) -> ChoreInstance:
        """Reassign a chore instance to a different kid.

        Args:
            instance_id: ID of the instance to reassign
            new_user_id: ID of the kid to assign to
            reassigned_by_id: ID of the parent doing the reassignment

        Returns:
            The updated ChoreInstance

        Raises:
            NotFoundError: Instance not found
            BadRequestError: Invalid status, not individual chore, or invalid assignee
            ForbiddenError: User is not a parent
        """
        instance = InstanceService.get_instance(instance_id)

        reassigner = db.session.get(User, reassigned_by_id)
        if not reassigner or reassigner.role != 'parent':
            raise ForbiddenError('Only parents can reassign chores')

        if instance.status != 'assigned':
            raise BadRequestError('Can only reassign unclaimed instances')

        if instance.chore.assignment_type != 'individual':
            raise BadRequestError('Can only reassign individual chores')

        new_user = db.session.get(User, new_user_id)
        if not new_user or new_user.role != 'kid':
            raise BadRequestError('New assignee must be a kid')

        instance.assigned_to = new_user_id

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

        db.session.commit()

        return instance

    # Work-together specific methods

    @staticmethod
    def close_claiming(instance_id: int, user_id: int) -> ChoreInstance:
        """Close claiming for a work-together instance (parent action).

        Args:
            instance_id: ID of the work-together instance
            user_id: ID of the parent closing claiming

        Returns:
            The updated ChoreInstance

        Raises:
            NotFoundError: Instance not found
            BadRequestError: Not a work-together chore or already closed
            ForbiddenError: User is not a parent
        """
        instance = InstanceService.get_instance(instance_id)

        if not instance.is_work_together():
            raise BadRequestError('This is not a work-together chore')

        if not instance.can_close_claiming(user_id):
            if instance.claiming_closed_at:
                raise BadRequestError('Claiming is already closed')
            if len(instance.claims) == 0:
                raise BadRequestError('Cannot close claiming with no claims')
            raise ForbiddenError('Only parents can close claiming')

        instance.close_claiming(user_id)
        db.session.commit()

        logger.info(f"Claiming closed for instance {instance_id} by user {user_id}")

        try:
            fire_webhook('work_together_claiming_closed', instance)
        except Exception as e:
            logger.error(f"Failed to fire webhook: {e}")

        return instance

    @staticmethod
    def get_claim(claim_id: int) -> ChoreInstanceClaim:
        """Get a claim by ID or raise NotFoundError."""
        claim = db.session.get(ChoreInstanceClaim, claim_id)
        if not claim:
            raise NotFoundError(f'Claim {claim_id} not found')
        return claim

    @staticmethod
    def approve_claim(claim_id: int, approver_id: int, custom_points: Optional[int] = None) -> ChoreInstanceClaim:
        """Approve an individual claim for a work-together chore.

        Args:
            claim_id: ID of the claim to approve
            approver_id: ID of the parent approving
            custom_points: Optional override for points to award

        Returns:
            The updated ChoreInstanceClaim

        Raises:
            NotFoundError: Claim not found
            BadRequestError: Cannot approve (wrong status or claiming not closed)
            ForbiddenError: User is not a parent
        """
        claim = InstanceService.get_claim(claim_id)

        if not claim.can_approve(approver_id):
            if claim.status != 'claimed':
                raise BadRequestError(f'Cannot approve claim with status "{claim.status}"')
            if claim.instance.claiming_closed_at is None:
                raise BadRequestError('Cannot approve until claiming is closed')
            raise ForbiddenError('Only parents can approve claims')

        claim.award_points(approver_id, custom_points)

        # Check if all claims are now resolved
        claim.instance.check_all_claims_resolved()

        db.session.commit()

        logger.info(f"Claim {claim_id} approved by user {approver_id}, {claim.points_awarded} points awarded")

        try:
            fire_webhook('work_together_claim_approved', claim.instance, {'claim': claim.to_dict()})
        except Exception as e:
            logger.error(f"Failed to fire webhook: {e}")

        return claim

    @staticmethod
    def reject_claim(claim_id: int, rejecter_id: int, reason: str) -> ChoreInstanceClaim:
        """Reject an individual claim for a work-together chore.

        Args:
            claim_id: ID of the claim to reject
            rejecter_id: ID of the parent rejecting
            reason: Reason for rejection (required)

        Returns:
            The updated ChoreInstanceClaim

        Raises:
            NotFoundError: Claim not found
            BadRequestError: Cannot reject (wrong status, no reason, or claiming not closed)
            ForbiddenError: User is not a parent
        """
        claim = InstanceService.get_claim(claim_id)

        if not reason or not reason.strip():
            raise BadRequestError('Rejection reason is required')

        if claim.status != 'claimed':
            raise BadRequestError(f'Cannot reject claim with status "{claim.status}"')

        if claim.instance.claiming_closed_at is None:
            raise BadRequestError('Cannot reject until claiming is closed')

        user = db.session.get(User, rejecter_id)
        if not user or user.role != 'parent':
            raise ForbiddenError('Only parents can reject claims')

        claim.status = 'rejected'
        claim.rejected_by = rejecter_id
        claim.rejected_at = datetime.utcnow()
        claim.rejection_reason = reason.strip()

        # Check if all claims are now resolved
        claim.instance.check_all_claims_resolved()

        db.session.commit()

        logger.info(f"Claim {claim_id} rejected by user {rejecter_id}")

        try:
            fire_webhook('work_together_claim_rejected', claim.instance, {'claim': claim.to_dict()})
        except Exception as e:
            logger.error(f"Failed to fire webhook: {e}")

        return claim
