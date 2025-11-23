"""
Missed instance marker job.
"""

from datetime import date
import logging

logger = logging.getLogger(__name__)


def mark_missed_instances():
    """
    Mark overdue assigned instances as missed.

    Runs hourly. Transitions instances to 'missed' status if:
    - status = 'assigned'
    - due_date < today
    - chore.allow_late_claims = False
    """
    logger.debug("Checking for missed instances")

    # Import inside function to avoid circular imports and to get app context
    from models import db, ChoreInstance, Chore

    try:
        today = date.today()

        # Find overdue assigned instances where late claims are not allowed
        overdue = ChoreInstance.query.filter(
            ChoreInstance.status == 'assigned',
            ChoreInstance.due_date < today,
            ChoreInstance.due_date.isnot(None)
        ).join(Chore).filter(
            Chore.allow_late_claims == False
        ).all()

        for instance in overdue:
            instance.status = 'missed'

        db.session.commit()

        if len(overdue) > 0:
            logger.info(f"Marked {len(overdue)} instances as missed")

    except Exception as e:
        logger.error(f"Error marking missed instances: {e}")
        db.session.rollback()
        raise
