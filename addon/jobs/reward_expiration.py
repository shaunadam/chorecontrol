"""
Pending reward expiration job.
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def expire_pending_rewards():
    """
    Expire pending reward claims after their expiration date.

    Runs daily at 00:01. Auto-rejects pending claims that have exceeded
    their expiration date and refunds points.
    """
    logger.info("Checking for expired reward claims")

    # Import inside function to avoid circular imports and to get app context
    from addon.models import db, RewardClaim, User

    try:
        expired = RewardClaim.query.filter(
            RewardClaim.status == 'pending',
            RewardClaim.expires_at <= datetime.utcnow()
        ).all()

        expired_count = 0

        for claim in expired:
            try:
                claim.status = 'rejected'

                # Refund points
                user = User.query.get(claim.user_id)
                if user:
                    user.adjust_points(
                        delta=claim.points_spent,
                        reason=f"Reward claim expired: {claim.reward.name}",
                        reward_claim_id=claim.id
                    )

                    logger.info(f"Expired reward claim {claim.id}, refunded {claim.points_spent} points to user {user.id}")

                    # Fire webhook
                    try:
                        from addon.utils.webhooks import fire_webhook
                        fire_webhook('reward_rejected', claim, reason='expired')
                    except ImportError:
                        # Webhooks not yet implemented
                        pass

                    expired_count += 1
                else:
                    logger.error(f"User {claim.user_id} not found for expired claim {claim.id}")

            except Exception as e:
                logger.error(f"Error expiring claim {claim.id}: {e}")
                db.session.rollback()

        db.session.commit()

        if expired_count > 0:
            logger.info(f"Expired {expired_count} pending reward claims")

    except Exception as e:
        logger.error(f"Error in reward expiration job: {e}")
        raise
