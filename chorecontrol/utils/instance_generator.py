"""
Chore instance generation utilities.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List
import calendar
import logging

from models import db, Chore, ChoreInstance, ChoreAssignment
from utils.recurrence import generate_due_dates

logger = logging.getLogger(__name__)


def calculate_lookahead_end_date() -> date:
    """
    Calculate the end date for instance generation.

    Rule: End of the month that is 2 months ahead.
    Examples:
    - Jan 1 → Mar 31
    - Jan 31 → Mar 31
    - Feb 1 → Apr 30
    """
    today = date.today()
    target_month = today + relativedelta(months=2)
    last_day = calendar.monthrange(target_month.year, target_month.month)[1]

    return date(target_month.year, target_month.month, last_day)


def check_duplicate_instance(chore_id: int, due_date: date, assigned_to: int = None) -> bool:
    """
    Check if an instance already exists.

    Args:
        chore_id: Chore template ID
        due_date: Due date for instance
        assigned_to: User ID (for individual chores) or None (for shared)

    Returns:
        True if duplicate exists, False otherwise
    """
    existing = ChoreInstance.query.filter_by(
        chore_id=chore_id,
        due_date=due_date,
        assigned_to=assigned_to
    ).first()

    return existing is not None


def generate_instances_for_chore(chore: Chore, start_date: date = None, end_date: date = None) -> List[ChoreInstance]:
    """
    Generate instances for a chore based on its recurrence pattern.

    Args:
        chore: Chore template
        start_date: Start of generation range (default: today)
        end_date: End of generation range (default: lookahead window)

    Returns:
        List of newly created instances
    """
    if not chore.is_active:
        logger.info(f"Chore {chore.id} is inactive, skipping generation")
        return []

    if start_date is None:
        start_date = date.today()

    if end_date is None:
        end_date = calculate_lookahead_end_date()

    # Respect chore's start_date and end_date
    if chore.start_date and start_date < chore.start_date:
        start_date = chore.start_date

    if chore.end_date and end_date > chore.end_date:
        end_date = chore.end_date

    # Handle one-off chores
    if chore.recurrence_type == 'none':
        if chore.start_date:
            due_dates = [chore.start_date] if chore.start_date >= start_date and chore.start_date <= end_date else []
        else:
            # No due date (anytime chore)
            due_dates = [None]
    else:
        # Recurring chore
        due_dates = generate_due_dates(chore.recurrence_pattern, start_date, end_date)

    instances = []

    for due_date in due_dates:
        if chore.assignment_type == 'individual':
            # Create one instance per assigned kid
            for assignment in chore.assignments:
                if not check_duplicate_instance(chore.id, due_date, assignment.user_id):
                    instance = ChoreInstance(
                        chore_id=chore.id,
                        due_date=due_date,
                        assigned_to=assignment.user_id,
                        status='assigned'
                    )
                    db.session.add(instance)
                    instances.append(instance)
                    logger.debug(f"Created individual instance: chore={chore.id}, due={due_date}, user={assignment.user_id}")

        else:  # shared
            # Create one instance total
            if not check_duplicate_instance(chore.id, due_date, None):
                instance = ChoreInstance(
                    chore_id=chore.id,
                    due_date=due_date,
                    assigned_to=None,
                    status='assigned'
                )
                db.session.add(instance)
                instances.append(instance)
                logger.debug(f"Created shared instance: chore={chore.id}, due={due_date}")

    db.session.commit()
    logger.info(f"Generated {len(instances)} instances for chore {chore.id}")

    return instances


def delete_future_instances(chore: Chore) -> int:
    """
    Delete future assigned instances for a chore (used when schedule changes).

    Only deletes instances with status='assigned' and due_date >= today.
    Preserves claimed/approved/rejected instances for history.

    Args:
        chore: Chore template

    Returns:
        Number of instances deleted
    """
    today = date.today()

    deleted = ChoreInstance.query.filter(
        ChoreInstance.chore_id == chore.id,
        ChoreInstance.status == 'assigned',
        ChoreInstance.due_date >= today
    ).delete()

    db.session.commit()
    logger.info(f"Deleted {deleted} future instances for chore {chore.id}")

    return deleted


def regenerate_instances_for_chore(chore: Chore) -> List[ChoreInstance]:
    """
    Delete and regenerate instances (used when chore schedule is modified).

    Args:
        chore: Chore template

    Returns:
        List of newly created instances
    """
    deleted_count = delete_future_instances(chore)
    logger.info(f"Regenerating instances for chore {chore.id} (deleted {deleted_count})")

    instances = generate_instances_for_chore(chore)

    return instances
