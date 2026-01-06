"""
Daily instance generation job.
"""

from datetime import date
import logging

from utils.timezone import local_today

logger = logging.getLogger(__name__)


def generate_daily_instances():
    """
    Generate chore instances for all active chores.

    Runs daily at midnight. Generates instances through the look-ahead window
    (end of month + 2 months). Fires webhooks only for instances due today.
    """
    logger.info("Starting daily instance generation")

    # Import inside function to avoid circular imports and to get app context
    from models import db, Chore
    from utils.instance_generator import generate_instances_for_chore, calculate_lookahead_end_date

    try:
        active_chores = Chore.query.filter_by(is_active=True).all()

        today = local_today()
        end_date = calculate_lookahead_end_date()

        total_instances = 0
        webhooks_fired = 0

        for chore in active_chores:
            try:
                instances = generate_instances_for_chore(chore, start_date=today, end_date=end_date)
                total_instances += len(instances)

                # Fire webhooks only for instances due today or NULL due date
                for instance in instances:
                    if instance.due_date == today or instance.due_date is None:
                        try:
                            from utils.webhooks import fire_webhook
                            fire_webhook('chore_instance_created', instance)
                            webhooks_fired += 1
                        except ImportError:
                            # Webhooks not yet implemented
                            pass

            except Exception as e:
                logger.error(f"Error generating instances for chore {chore.id}: {e}")
                db.session.rollback()

        logger.info(f"Daily instance generation complete: {total_instances} instances created, {webhooks_fired} webhooks fired")

    except Exception as e:
        logger.error(f"Error in daily instance generation: {e}")
        raise
