"""
Background job scheduler using APScheduler.

This module sets up and manages the background scheduler for ChoreControl,
handling tasks like instance generation, auto-approval, and cleanup jobs.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging
import atexit

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def init_scheduler(app):
    """
    Initialize and start the background scheduler.

    Args:
        app: Flask application instance
    """
    # Check if scheduler should be enabled
    scheduler_enabled = app.config.get('SCHEDULER_ENABLED', True)

    if not scheduler_enabled:
        logger.info("Background scheduler disabled via configuration")
        return

    # Don't run scheduler in testing mode
    if app.config.get('TESTING', False):
        logger.info("Background scheduler disabled in testing mode")
        return

    # Import job functions
    from addon.jobs.instance_generator import generate_daily_instances
    from addon.jobs.auto_approval import check_auto_approvals
    from addon.jobs.missed_instances import mark_missed_instances
    from addon.jobs.reward_expiration import expire_pending_rewards
    from addon.jobs.points_audit import audit_points_balances

    # Configure scheduler timezone
    timezone = app.config.get('SCHEDULER_TIMEZONE', 'UTC')

    # Create job wrappers that run within app context
    def with_app_context(func):
        """Wrap job function to run within Flask app context."""
        def wrapper():
            with app.app_context():
                func()
        wrapper.__name__ = func.__name__
        return wrapper

    # Schedule jobs

    # Daily instance generation at midnight
    scheduler.add_job(
        with_app_context(generate_daily_instances),
        trigger=CronTrigger(hour=0, minute=0, timezone=timezone),
        id='daily_instance_generation',
        name='Generate daily chore instances',
        replace_existing=True
    )

    # Auto-approval check every 5 minutes
    scheduler.add_job(
        with_app_context(check_auto_approvals),
        trigger=IntervalTrigger(minutes=5),
        id='auto_approval_check',
        name='Check for auto-approvals',
        replace_existing=True
    )

    # Mark missed instances hourly at :30
    scheduler.add_job(
        with_app_context(mark_missed_instances),
        trigger=CronTrigger(minute=30, timezone=timezone),
        id='mark_missed_instances',
        name='Mark missed chore instances',
        replace_existing=True
    )

    # Expire pending rewards daily at 00:01
    scheduler.add_job(
        with_app_context(expire_pending_rewards),
        trigger=CronTrigger(hour=0, minute=1, timezone=timezone),
        id='expire_pending_rewards',
        name='Expire pending reward claims',
        replace_existing=True
    )

    # Audit points balances nightly at 02:00
    scheduler.add_job(
        with_app_context(audit_points_balances),
        trigger=CronTrigger(hour=2, minute=0, timezone=timezone),
        id='audit_points_balances',
        name='Audit user points balances',
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    logger.info("Background scheduler started with %d jobs", len(scheduler.get_jobs()))

    # Register shutdown handler
    atexit.register(shutdown_scheduler)


def shutdown_scheduler():
    """Shutdown the background scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")


def get_scheduler():
    """
    Get the scheduler instance.

    Returns:
        BackgroundScheduler: The scheduler instance
    """
    return scheduler


def run_job_now(job_id: str):
    """
    Run a scheduled job immediately (useful for testing/admin).

    Args:
        job_id: ID of the job to run

    Returns:
        bool: True if job was found and triggered, False otherwise
    """
    job = scheduler.get_job(job_id)
    if job:
        job.func()
        return True
    return False


def get_job_status():
    """
    Get status of all scheduled jobs.

    Returns:
        list: List of job status dictionaries
    """
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger)
        })
    return jobs
