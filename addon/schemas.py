"""
JSON schemas and validation for ChoreControl.

This module defines JSON schemas for recurrence patterns and provides
validation and parsing utilities.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
import json

# JSON Schema definitions for recurrence patterns

SIMPLE_RECURRENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["simple"]
        },
        "interval": {
            "type": "string",
            "enum": ["daily", "weekly", "monthly"]
        },
        "every_n": {
            "type": "integer",
            "minimum": 1,
            "description": "Every N days/weeks/months"
        },
        "time": {
            "type": "string",
            "pattern": "^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
            "description": "Time in HH:MM format (24-hour)"
        }
    },
    "required": ["type", "interval", "every_n"],
    "additionalProperties": False
}

COMPLEX_RECURRENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["complex"]
        },
        "days_of_week": {
            "type": "array",
            "items": {
                "type": "integer",
                "minimum": 0,
                "maximum": 6
            },
            "description": "0=Monday, 6=Sunday"
        },
        "weeks_of_month": {
            "type": "array",
            "items": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5
            },
            "description": "1st, 2nd, 3rd, 4th, 5th week"
        },
        "days_of_month": {
            "type": "array",
            "items": {
                "type": "integer",
                "minimum": 1,
                "maximum": 31
            },
            "description": "Specific days of month"
        },
        "time": {
            "type": "string",
            "pattern": "^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
            "description": "Time in HH:MM format (24-hour)"
        }
    },
    "required": ["type"],
    "additionalProperties": False
}

RECURRENCE_PATTERN_SCHEMA = {
    "oneOf": [
        SIMPLE_RECURRENCE_SCHEMA,
        COMPLEX_RECURRENCE_SCHEMA
    ]
}


def validate_recurrence_pattern(pattern: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate a recurrence pattern against the JSON schema.

    Args:
        pattern: Dictionary containing the recurrence pattern

    Returns:
        tuple: (is_valid: bool, error_message: str if invalid)
    """
    if not pattern:
        return False, "Pattern cannot be empty"

    if not isinstance(pattern, dict):
        return False, "Pattern must be a dictionary"

    pattern_type = pattern.get('type')
    if not pattern_type:
        return False, "Pattern must have a 'type' field"

    try:
        # Import jsonschema only when needed
        import jsonschema

        if pattern_type == 'simple':
            jsonschema.validate(instance=pattern, schema=SIMPLE_RECURRENCE_SCHEMA)
        elif pattern_type == 'complex':
            jsonschema.validate(instance=pattern, schema=COMPLEX_RECURRENCE_SCHEMA)
        else:
            return False, f"Unknown pattern type: {pattern_type}"

        return True, None

    except jsonschema.exceptions.ValidationError as e:
        return False, str(e.message)
    except ImportError:
        # If jsonschema not installed, do basic validation
        return _basic_validation(pattern)


def _basic_validation(pattern: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Basic validation without jsonschema library."""
    pattern_type = pattern.get('type')

    if pattern_type == 'simple':
        if 'interval' not in pattern:
            return False, "Simple pattern requires 'interval' field"
        if pattern['interval'] not in ['daily', 'weekly', 'monthly']:
            return False, "Invalid interval value"
        if 'every_n' not in pattern:
            return False, "Simple pattern requires 'every_n' field"
        if not isinstance(pattern['every_n'], int) or pattern['every_n'] < 1:
            return False, "'every_n' must be a positive integer"

    elif pattern_type == 'complex':
        # At least one constraint required
        if not any(k in pattern for k in ['days_of_week', 'weeks_of_month', 'days_of_month']):
            return False, "Complex pattern requires at least one constraint"

    return True, None


def calculate_next_due_date(pattern: Optional[Dict[str, Any]], after_date: date) -> Optional[date]:
    """
    Calculate the next due date based on recurrence pattern.

    Args:
        pattern: Recurrence pattern dictionary
        after_date: Calculate next date after this date

    Returns:
        date: Next due date, or None if no more occurrences
    """
    if not pattern:
        return None

    pattern_type = pattern.get('type')

    if pattern_type == 'simple':
        return _calculate_simple_next_date(pattern, after_date)
    elif pattern_type == 'complex':
        return _calculate_complex_next_date(pattern, after_date)

    return None


def _calculate_simple_next_date(pattern: Dict[str, Any], after_date: date) -> Optional[date]:
    """Calculate next date for simple recurrence patterns."""
    interval = pattern['interval']
    every_n = pattern['every_n']

    if interval == 'daily':
        return after_date + timedelta(days=every_n)

    elif interval == 'weekly':
        return after_date + timedelta(weeks=every_n)

    elif interval == 'monthly':
        # Add N months (approximate - may need adjustment for month-end dates)
        next_month = after_date.month + every_n
        next_year = after_date.year + (next_month - 1) // 12
        next_month = ((next_month - 1) % 12) + 1

        # Handle day overflow (e.g., Jan 31 -> Feb 31 doesn't exist)
        try:
            return date(next_year, next_month, after_date.day)
        except ValueError:
            # If day doesn't exist in target month, use last day of month
            from calendar import monthrange
            last_day = monthrange(next_year, next_month)[1]
            return date(next_year, next_month, last_day)

    return None


def _calculate_complex_next_date(pattern: Dict[str, Any], after_date: date) -> Optional[date]:
    """
    Calculate next date for complex recurrence patterns.

    This is a simplified implementation. A production version would need
    more sophisticated logic to handle all combinations of constraints.
    """
    days_of_week = pattern.get('days_of_week')
    days_of_month = pattern.get('days_of_month')
    weeks_of_month = pattern.get('weeks_of_month')

    # Simple case: specific days of week
    if days_of_week and not weeks_of_month and not days_of_month:
        return _next_matching_weekday(after_date, days_of_week)

    # Simple case: specific days of month
    if days_of_month and not days_of_week and not weeks_of_month:
        return _next_matching_day_of_month(after_date, days_of_month)

    # Complex case: combination of constraints
    # Start checking from next day
    check_date = after_date + timedelta(days=1)
    max_days_to_check = 366  # Prevent infinite loops

    for _ in range(max_days_to_check):
        if _matches_complex_pattern(check_date, pattern):
            return check_date
        check_date += timedelta(days=1)

    return None


def _next_matching_weekday(after_date: date, days_of_week: List[int]) -> date:
    """Find next date matching one of the specified weekdays (0=Monday)."""
    check_date = after_date + timedelta(days=1)

    for _ in range(7):  # Check at most one week ahead
        if check_date.weekday() in days_of_week:
            return check_date
        check_date += timedelta(days=1)

    # Should never reach here if days_of_week is valid
    return after_date + timedelta(days=1)


def _next_matching_day_of_month(after_date: date, days_of_month: List[int]) -> date:
    """Find next date matching one of the specified days of month."""
    from calendar import monthrange

    # Check if any remaining days in current month match
    current_month_days = range(after_date.day + 1, monthrange(after_date.year, after_date.month)[1] + 1)
    for day in current_month_days:
        if day in days_of_month:
            return date(after_date.year, after_date.month, day)

    # Move to next month
    next_month = after_date.month + 1
    next_year = after_date.year
    if next_month > 12:
        next_month = 1
        next_year += 1

    # Find first matching day in next month
    for day in sorted(days_of_month):
        try:
            return date(next_year, next_month, day)
        except ValueError:
            continue  # Day doesn't exist in this month

    # If no valid day found, recurse to next month
    return _next_matching_day_of_month(
        date(next_year, next_month, 1),
        days_of_month
    )


def _matches_complex_pattern(check_date: date, pattern: Dict[str, Any]) -> bool:
    """Check if a date matches all constraints in a complex pattern."""
    days_of_week = pattern.get('days_of_week')
    days_of_month = pattern.get('days_of_month')
    weeks_of_month = pattern.get('weeks_of_month')

    # Check day of week constraint
    if days_of_week is not None and check_date.weekday() not in days_of_week:
        return False

    # Check day of month constraint
    if days_of_month is not None and check_date.day not in days_of_month:
        return False

    # Check week of month constraint
    if weeks_of_month is not None:
        week_of_month = (check_date.day - 1) // 7 + 1
        if week_of_month not in weeks_of_month:
            return False

    return True


def generate_instances_for_date_range(
    pattern: Optional[Dict[str, Any]],
    start_date: date,
    end_date: date,
    chore_start_date: Optional[date] = None,
    chore_end_date: Optional[date] = None
) -> List[date]:
    """
    Generate all due dates for a chore within a date range.

    Args:
        pattern: Recurrence pattern
        start_date: Start of range to generate instances
        end_date: End of range to generate instances
        chore_start_date: Earliest date chore can be due
        chore_end_date: Latest date chore can be due

    Returns:
        List of due dates
    """
    if not pattern:
        # One-off chore
        if chore_start_date and start_date <= chore_start_date <= end_date:
            return [chore_start_date]
        return []

    due_dates = []
    current_date = start_date

    # Respect chore start date
    if chore_start_date and current_date < chore_start_date:
        current_date = chore_start_date

    max_iterations = 1000  # Safety limit
    iterations = 0

    while current_date <= end_date and iterations < max_iterations:
        next_date = calculate_next_due_date(pattern, current_date - timedelta(days=1))

        if next_date is None or next_date > end_date:
            break

        # Respect chore end date
        if chore_end_date and next_date > chore_end_date:
            break

        if next_date >= start_date:
            due_dates.append(next_date)

        current_date = next_date + timedelta(days=1)
        iterations += 1

    return due_dates


def parse_recurrence_pattern(pattern_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse a JSON string into a recurrence pattern dictionary.

    Args:
        pattern_str: JSON string representation of pattern

    Returns:
        Dictionary or None if invalid
    """
    if not pattern_str:
        return None

    try:
        pattern = json.loads(pattern_str)
        is_valid, error = validate_recurrence_pattern(pattern)
        if is_valid:
            return pattern
        else:
            raise ValueError(f"Invalid recurrence pattern: {error}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def format_recurrence_pattern(pattern: Optional[Dict[str, Any]]) -> str:
    """
    Format a recurrence pattern dictionary as a human-readable string.

    Args:
        pattern: Recurrence pattern dictionary

    Returns:
        Human-readable description
    """
    if not pattern:
        return "One-time"

    pattern_type = pattern.get('type')

    if pattern_type == 'simple':
        interval = pattern['interval']
        every_n = pattern['every_n']

        if every_n == 1:
            return f"Every {interval[:-2]}"  # "daily" -> "day", "weekly" -> "week"
        else:
            return f"Every {every_n} {interval[:-2]}s"  # "days", "weeks", etc.

    elif pattern_type == 'complex':
        parts = []

        if 'days_of_week' in pattern:
            days = pattern['days_of_week']
            day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            day_str = ', '.join(day_names[d] for d in sorted(days))
            parts.append(f"on {day_str}")

        if 'days_of_month' in pattern:
            days = sorted(pattern['days_of_month'])
            days_str = ', '.join(str(d) for d in days)
            parts.append(f"on day(s) {days_str}")

        if 'weeks_of_month' in pattern:
            weeks = sorted(pattern['weeks_of_month'])
            ordinals = ['1st', '2nd', '3rd', '4th', '5th']
            weeks_str = ', '.join(ordinals[w-1] for w in weeks)
            parts.append(f"in {weeks_str} week(s)")

        return ' '.join(parts) if parts else "Complex schedule"

    return "Unknown pattern"


# Example patterns for testing/documentation

EXAMPLE_PATTERNS = {
    "daily": {
        "type": "simple",
        "interval": "daily",
        "every_n": 1,
        "time": "18:00"
    },
    "every_other_day": {
        "type": "simple",
        "interval": "daily",
        "every_n": 2
    },
    "weekly": {
        "type": "simple",
        "interval": "weekly",
        "every_n": 1
    },
    "bi_weekly": {
        "type": "simple",
        "interval": "weekly",
        "every_n": 2
    },
    "monthly": {
        "type": "simple",
        "interval": "monthly",
        "every_n": 1
    },
    "weekdays": {
        "type": "complex",
        "days_of_week": [0, 1, 2, 3, 4],  # Monday-Friday
        "time": "08:00"
    },
    "monday_wednesday_friday": {
        "type": "complex",
        "days_of_week": [0, 2, 4],  # Monday, Wednesday, Friday
        "time": "18:00"
    },
    "first_and_fifteenth": {
        "type": "complex",
        "days_of_month": [1, 15]
    },
    "first_monday": {
        "type": "complex",
        "days_of_week": [0],  # Monday
        "weeks_of_month": [1]  # First week
    }
}
