"""
Recurrence pattern utilities for chore instance generation.
"""

from datetime import date, timedelta
from typing import Optional, List
from dateutil.relativedelta import relativedelta
import calendar


def calculate_next_due_date(pattern: dict, after_date: date) -> Optional[date]:
    """
    Calculate the next due date based on recurrence pattern.

    Args:
        pattern: Recurrence pattern dict from Chore.recurrence_pattern
        after_date: Calculate next occurrence after this date

    Returns:
        Next due date, or None if no more occurrences
    """
    if not pattern:
        return None

    pattern_type = pattern.get('type')

    # Handle 'simple' pattern type with interval
    if pattern_type == 'simple':
        interval = pattern.get('interval', 'daily')
        every_n = pattern.get('every_n', 1)

        if interval == 'daily':
            return after_date + timedelta(days=every_n)
        elif interval == 'weekly':
            return after_date + timedelta(weeks=every_n)
        elif interval == 'monthly':
            return after_date + relativedelta(months=every_n)
        else:
            raise ValueError(f"Unknown simple interval: {interval}")

    # Handle 'complex' pattern type
    elif pattern_type == 'complex':
        days_of_week = pattern.get('days_of_week', [])
        if days_of_week:
            # Find next occurrence in the specified days
            current = after_date + timedelta(days=1)
            for _ in range(7):
                if current.weekday() in days_of_week:
                    return current
                current += timedelta(days=1)
        return None

    elif pattern_type == 'daily':
        return after_date + timedelta(days=1)

    elif pattern_type == 'weekly':
        days_of_week = pattern.get('days_of_week', [])
        if not days_of_week:
            raise ValueError("Weekly pattern must have days_of_week")

        # Convert Sunday=0 to Python's Monday=0 format
        weekday_adjusted = [(d - 1) % 7 for d in days_of_week]

        # Find next occurrence
        current = after_date + timedelta(days=1)
        for _ in range(7):  # Check next 7 days
            if current.weekday() in weekday_adjusted:
                return current
            current += timedelta(days=1)

        return None

    elif pattern_type == 'monthly':
        days_of_month = pattern.get('days_of_month', [])
        if not days_of_month:
            raise ValueError("Monthly pattern must have days_of_month")

        # Find next occurrence
        current = after_date + timedelta(days=1)

        # Check current month first
        for day in sorted(days_of_month):
            target_day = min(day, calendar.monthrange(current.year, current.month)[1])
            target_date = date(current.year, current.month, target_day)

            if target_date >= current:
                return target_date

        # Move to next month
        next_month = current + relativedelta(months=1)
        first_day = sorted(days_of_month)[0]
        target_day = min(first_day, calendar.monthrange(next_month.year, next_month.month)[1])

        return date(next_month.year, next_month.month, target_day)

    elif pattern_type == 'none':
        return None

    else:
        raise ValueError(f"Unknown recurrence pattern type: {pattern_type}")


def generate_due_dates(pattern: dict, start_date: date, end_date: date) -> List[date]:
    """
    Generate all due dates between start and end based on pattern.

    Args:
        pattern: Recurrence pattern dict
        start_date: Start of range (inclusive)
        end_date: End of range (inclusive)

    Returns:
        List of due dates
    """
    if not pattern:
        return []

    pattern_type = pattern.get('type')

    if pattern_type == 'none':
        # One-off chore
        if start_date <= end_date:
            return [start_date]
        return []

    dates = []
    current = start_date

    while current <= end_date:
        # Add current date if it matches pattern
        if matches_pattern(pattern, current):
            dates.append(current)

        # Calculate next date
        next_date = calculate_next_due_date(pattern, current)
        if next_date is None or next_date > end_date:
            break
        current = next_date

    return dates


def matches_pattern(pattern: dict, check_date: date) -> bool:
    """
    Check if a given date matches the recurrence pattern.

    Args:
        pattern: Recurrence pattern dict
        check_date: Date to check

    Returns:
        True if date matches pattern
    """
    pattern_type = pattern.get('type')

    # Handle 'simple' pattern type
    if pattern_type == 'simple':
        interval = pattern.get('interval', 'daily')
        if interval == 'daily':
            return True
        elif interval == 'weekly':
            # Weekly patterns match once per week - use start_date if available
            return True  # Simplified - actual matching handled by generate logic
        elif interval == 'monthly':
            return True  # Simplified - actual matching handled by generate logic
        return True

    # Handle 'complex' pattern type
    elif pattern_type == 'complex':
        days_of_week = pattern.get('days_of_week', [])
        if days_of_week:
            return check_date.weekday() in days_of_week
        return False

    elif pattern_type == 'daily':
        return True

    elif pattern_type == 'weekly':
        days_of_week = pattern.get('days_of_week', [])
        # Convert Sunday=0 to Monday=0 format
        weekday_adjusted = [(d - 1) % 7 for d in days_of_week]
        return check_date.weekday() in weekday_adjusted

    elif pattern_type == 'monthly':
        days_of_month = pattern.get('days_of_month', [])
        # Handle month-end edge cases
        for day in days_of_month:
            target_day = min(day, calendar.monthrange(check_date.year, check_date.month)[1])
            if check_date.day == target_day:
                return True
        return False

    elif pattern_type == 'none':
        return False

    else:
        return False


def validate_recurrence_pattern(pattern: dict) -> tuple[bool, Optional[str]]:
    """
    Validate a recurrence pattern.

    Args:
        pattern: Recurrence pattern dict to validate

    Returns:
        (is_valid, error_message)
    """
    if not pattern:
        return False, "Pattern cannot be empty"

    pattern_type = pattern.get('type')

    if pattern_type not in ['daily', 'weekly', 'monthly', 'none', 'simple', 'complex']:
        return False, f"Invalid pattern type: {pattern_type}"

    if pattern_type == 'simple':
        interval = pattern.get('interval')
        if interval and interval not in ['daily', 'weekly', 'monthly']:
            return False, f"Invalid simple interval: {interval}"

    elif pattern_type == 'complex':
        days_of_week = pattern.get('days_of_week')
        if days_of_week:
            if not isinstance(days_of_week, list):
                return False, "days_of_week must be a list"
            if not all(isinstance(d, int) and 0 <= d <= 6 for d in days_of_week):
                return False, "days_of_week must contain integers 0-6"

    elif pattern_type == 'weekly':
        days_of_week = pattern.get('days_of_week')
        if not days_of_week or not isinstance(days_of_week, list) or len(days_of_week) == 0:
            return False, "Weekly pattern must have non-empty days_of_week array"

        if not all(isinstance(d, int) and 0 <= d <= 6 for d in days_of_week):
            return False, "days_of_week must contain integers 0-6"

    elif pattern_type == 'monthly':
        days_of_month = pattern.get('days_of_month')
        if not days_of_month or not isinstance(days_of_month, list) or len(days_of_month) == 0:
            return False, "Monthly pattern must have non-empty days_of_month array"

        if not all(isinstance(d, int) and 1 <= d <= 31 for d in days_of_month):
            return False, "days_of_month must contain integers 1-31"

    return True, None
