"""
Auto-approval checker job.
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def check_auto_approvals():
    """
    Check for chore instances eligible for auto-approval.

    Runs every 5 minutes. Auto-approves claimed instances that have exceeded
    the auto-approval window.
    """
    logger.debug("Checking for auto-approvals")

    # Import inside function to avoid circular imports and to get app context
    from addon.models import db, ChoreInstance, Chore, User

    try:
        # Find eligible instances
        eligible = ChoreInstance.query.filter(
            ChoreInstance.status == 'claimed'
        ).join(Chore).filter(
            Chore.auto_approve_after_hours.isnot(None)
        ).all()

        system_user = User.query.filter_by(ha_user_id='system').first()

        if not system_user:
            logger.error("System user not found, cannot auto-approve")
            return

        approved_count = 0

        for instance in eligible:
            try:
                if instance.claimed_at is None:
                    logger.warning(f"Instance {instance.id} is claimed but has no claimed_at timestamp")
                    continue

                hours_since_claim = (datetime.utcnow() - instance.claimed_at).total_seconds() / 3600

                if hours_since_claim >= instance.chore.auto_approve_after_hours:
                    # Auto-approve
                    instance.award_points(approver_id=system_user.id)
                    db.session.commit()

                    logger.info(f"Auto-approved instance {instance.id} after {hours_since_claim:.1f} hours")

                    # Fire webhooks
                    try:
                        from addon.utils.webhooks import fire_webhook
                        fire_webhook('chore_instance_approved', instance, auto_approved=True)
                        fire_webhook('points_awarded', instance)
                    except ImportError:
                        # Webhooks not yet implemented
                        pass

                    approved_count += 1

            except Exception as e:
                logger.error(f"Error auto-approving instance {instance.id}: {e}")
                db.session.rollback()

        if approved_count > 0:
            logger.info(f"Auto-approved {approved_count} instances")

    except Exception as e:
        logger.error(f"Error in auto-approval checker: {e}")
        raise
