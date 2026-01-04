"""Reward claiming service.

This module contains the business logic for reward claim operations:
- Claiming rewards (deducting points)
- Unclaiming pending rewards (refunding points)
- Approving reward claims
- Rejecting reward claims (refunding points)

Routes should delegate to this service and handle HTTP responses.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from models import db, Reward, RewardClaim, User
from utils.webhooks import fire_webhook

logger = logging.getLogger(__name__)


class RewardServiceError(Exception):
    """Base exception for reward service errors."""

    def __init__(self, message: str, status_code: int = 400, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(RewardServiceError):
    def __init__(self, message: str):
        super().__init__(message, 404)


class ForbiddenError(RewardServiceError):
    def __init__(self, message: str):
        super().__init__(message, 403)


class BadRequestError(RewardServiceError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, 400, details)


class RewardService:
    """Service for managing reward claims."""

    @staticmethod
    def get_reward(reward_id: int) -> Reward:
        """Get a reward by ID or raise NotFoundError."""
        reward = db.session.get(Reward, reward_id)
        if not reward:
            raise NotFoundError(f'Reward {reward_id} not found')
        return reward

    @staticmethod
    def get_claim(claim_id: int) -> RewardClaim:
        """Get a claim by ID or raise NotFoundError."""
        claim = db.session.get(RewardClaim, claim_id)
        if not claim:
            raise NotFoundError(f'Reward claim {claim_id} not found')
        return claim

    @staticmethod
    def claim_reward(reward_id: int, user_id: int) -> RewardClaim:
        """Claim a reward for a user.

        Args:
            reward_id: ID of the reward to claim
            user_id: ID of the user claiming

        Returns:
            The created RewardClaim

        Raises:
            NotFoundError: Reward or user not found
            ForbiddenError: User is not a kid/claim_only
            BadRequestError: Cannot claim (insufficient points, cooldown, etc.)
        """
        reward = RewardService.get_reward(reward_id)

        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f'User {user_id} not found')

        if user.role not in ('kid', 'claim_only'):
            raise ForbiddenError('Only kids can claim rewards')

        can_claim, reason = reward.can_claim(user_id)

        if not can_claim:
            details = {}
            if 'Insufficient points' in reason:
                details['required'] = reward.points_cost
                details['current'] = user.points
            elif 'cooldown' in reason.lower():
                import re
                match = re.search(r'(\d+)', reason)
                if match:
                    details['cooldown_days_remaining'] = int(match.group(1))

            raise BadRequestError(reason, details if details else None)

        claim = RewardClaim(
            reward_id=reward.id,
            user_id=user.id,
            points_spent=reward.points_cost,
            status='pending' if reward.requires_approval else 'approved'
        )

        if reward.requires_approval:
            claim.expires_at = datetime.utcnow() + timedelta(days=7)

        db.session.add(claim)
        db.session.flush()

        old_balance = user.points
        user.adjust_points(
            delta=-reward.points_cost,
            reason=f"Claimed reward: {reward.name}",
            created_by_id=user.id,
            reward_claim_id=claim.id
        )

        db.session.commit()

        fire_webhook('reward_claimed', claim)

        # Store old_balance for response building
        claim._old_balance = old_balance

        return claim

    @staticmethod
    def unclaim_reward(claim_id: int, user_id: int) -> tuple[dict, int]:
        """Unclaim a pending reward and refund points.

        Args:
            claim_id: ID of the claim to cancel
            user_id: ID of the user unclaiming

        Returns:
            Tuple of (claim_data dict, points_refunded)

        Raises:
            NotFoundError: Claim not found
            ForbiddenError: User doesn't own the claim
            BadRequestError: Claim is not pending
        """
        claim = RewardService.get_claim(claim_id)

        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f'User {user_id} not found')

        # Allow claim_only users to unclaim any pending reward
        if user.role != 'claim_only' and claim.user_id != user.id:
            raise ForbiddenError('Not your claim')

        if claim.status != 'pending':
            raise BadRequestError('Can only unclaim pending rewards')

        reward = claim.reward
        points_refunded = claim.points_spent

        # Capture claim data before deletion for return value
        claim_data = claim.to_dict()

        # Refund points to the claimer (not necessarily the current user)
        claimer = db.session.get(User, claim.user_id)
        claimer.adjust_points(
            delta=claim.points_spent,
            reason=f"Unclaimed reward: {reward.name}",
            created_by_id=user.id,
            reward_claim_id=claim.id
        )

        db.session.delete(claim)
        db.session.commit()

        return claim_data, points_refunded

    @staticmethod
    def approve_claim(claim_id: int, approver_id: int) -> RewardClaim:
        """Approve a pending reward claim.

        Args:
            claim_id: ID of the claim to approve
            approver_id: ID of the parent approving

        Returns:
            The updated RewardClaim

        Raises:
            NotFoundError: Claim not found
            ForbiddenError: User is not a parent
            BadRequestError: Claim is not pending
        """
        claim = RewardService.get_claim(claim_id)

        user = db.session.get(User, approver_id)
        if not user or user.role != 'parent':
            raise ForbiddenError('Only parents can approve rewards')

        if claim.status != 'pending':
            raise BadRequestError('Claim is not pending')

        claim.status = 'approved'
        claim.approved_by = approver_id
        claim.approved_at = datetime.utcnow()
        claim.expires_at = None

        db.session.commit()

        fire_webhook('reward_approved', claim)

        return claim

    @staticmethod
    def reject_claim(claim_id: int, rejecter_id: int) -> RewardClaim:
        """Reject a pending reward claim and refund points.

        Args:
            claim_id: ID of the claim to reject
            rejecter_id: ID of the parent rejecting

        Returns:
            The updated RewardClaim

        Raises:
            NotFoundError: Claim not found
            ForbiddenError: User is not a parent
            BadRequestError: Claim is not pending
        """
        claim = RewardService.get_claim(claim_id)

        user = db.session.get(User, rejecter_id)
        if not user or user.role != 'parent':
            raise ForbiddenError('Only parents can reject rewards')

        if claim.status != 'pending':
            raise BadRequestError('Claim is not pending')

        claim.status = 'rejected'
        claim.approved_by = rejecter_id
        claim.approved_at = datetime.utcnow()
        claim.expires_at = None

        # Refund points
        claimer = db.session.get(User, claim.user_id)
        reward = claim.reward
        claimer.adjust_points(
            delta=claim.points_spent,
            reason=f"Reward claim rejected: {reward.name}",
            created_by_id=rejecter_id,
            reward_claim_id=claim.id
        )

        db.session.commit()

        fire_webhook('reward_rejected', claim, reason='manual')

        return claim
