"""
Missed instance marker job.
"""

from datetime import date, datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def mark_missed_instances():
    """
    Mark overdue assigned instances as missed.

    Runs hourly. Transitions instances to 'missed' status if:
    - status = 'assigned'
    - due_date + grace_period_days < today (past grace period)

    Also marks anytime chores as expired if:
    - status = 'assigned'
    - due_date is NULL
    - created_at + expires_after_days < now
    """
    logger.debug("Checking for missed instances")

    # Import inside function to avoid circular imports and to get app context
    from models import db, ChoreInstance, Chore

    try:
        today = date.today()
        now = datetime.utcnow()
        marked_count = 0

        # Find overdue assigned instances with dated due dates
        # We need to check each instance's grace period individually
        dated_instances = ChoreInstance.query.filter(
            ChoreInstance.status == 'assigned',
            ChoreInstance.due_date.isnot(None),
            ChoreInstance.due_date < today  # Only check past-due instances
        ).join(Chore).all()

        for instance in dated_instances:
            # Check if beyond grace period
            grace_deadline = instance.due_date + timedelta(days=instance.chore.grace_period_days)
            if today > grace_deadline:
                instance.status = 'missed'
                marked_count += 1
                logger.debug(f"Marked instance {instance.id} as missed (grace period expired)")

        # Find expired anytime chores
        anytime_instances = ChoreInstance.query.filter(
            ChoreInstance.status == 'assigned',
            ChoreInstance.due_date.is_(None)
        ).join(Chore).filter(
            Chore.expires_after_days.isnot(None)
        ).all()

        for instance in anytime_instances:
            # Check if expired
            expiry_deadline = instance.created_at + timedelta(days=instance.chore.expires_after_days)
            if now > expiry_deadline:
                instance.status = 'missed'
                marked_count += 1
                logger.debug(f"Marked anytime instance {instance.id} as expired")

        db.session.commit()

        if marked_count > 0:
            logger.info(f"Marked {marked_count} instances as missed/expired")

    except Exception as e:
        logger.error(f"Error marking missed instances: {e}")
        db.session.rollback()
        raise
