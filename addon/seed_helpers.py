"""
Helper functions for generating seed data.

This module provides utilities for creating realistic test data
for the ChoreControl application.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


# Predefined data for realistic seed generation
PARENT_NAMES = ["ParentOne", "ParentTwo"]
KID_NAMES = ["Alex", "Bailey", "Charlie"]
KID_AGES = {"Alex": 12, "Bailey": 9, "Charlie": 15}

CHORE_DATA = [
    {"name": "Take out trash", "description": "Roll bins to curb", "points": 5, "age_min": 8},
    {"name": "Do dishes", "description": "Wash and put away dishes", "points": 8, "age_min": 10},
    {"name": "Clean room", "description": "Make bed, organize toys, vacuum", "points": 10, "age_min": 7},
    {"name": "Homework", "description": "Complete daily homework assignments", "points": 15, "age_min": 6},
    {"name": "Walk dog", "description": "Walk Rex around the block", "points": 7, "age_min": 10},
    {"name": "Set table", "description": "Set table for dinner", "points": 3, "age_min": 6},
    {"name": "Feed pets", "description": "Feed dog and cat", "points": 4, "age_min": 7},
    {"name": "Vacuum living room", "description": "Vacuum the living room and hallway", "points": 8, "age_min": 10},
    {"name": "Water plants", "description": "Water all indoor plants", "points": 3, "age_min": 8},
    {"name": "Take out recycling", "description": "Sort and take out recycling", "points": 5, "age_min": 9},
    {"name": "Clean bathroom", "description": "Wipe down sink and mirror", "points": 10, "age_min": 12},
    {"name": "Fold laundry", "description": "Fold and put away clean laundry", "points": 8, "age_min": 10},
    {"name": "Mow lawn", "description": "Mow front and back yard", "points": 20, "age_min": 14},
    {"name": "Practice instrument", "description": "30 minutes of piano practice", "points": 12, "age_min": 8},
    {"name": "Read for 20 minutes", "description": "Read a book for 20 minutes", "points": 5, "age_min": 6},
]

REWARD_DATA = [
    {"name": "Ice cream trip", "description": "Trip to the ice cream shop", "points_cost": 20},
    {"name": "Extra screen time", "description": "30 minutes extra screen time", "points_cost": 15},
    {"name": "Stay up late", "description": "Stay up 30 minutes past bedtime", "points_cost": 25},
    {"name": "Choose dinner", "description": "Pick what we have for dinner", "points_cost": 30},
    {"name": "Movie night pick", "description": "Choose the movie for family movie night", "points_cost": 20},
    {"name": "Skip a chore", "description": "Skip one chore this week", "points_cost": 40},
    {"name": "Friend sleepover", "description": "Have a friend sleep over", "points_cost": 50},
]


def generate_random_date(days_back: int = 7) -> datetime:
    """
    Generate a random datetime within the last N days.

    Args:
        days_back: Number of days to go back from today

    Returns:
        Random datetime within the specified range
    """
    now = datetime.now()
    start_date = now - timedelta(days=days_back)
    random_seconds = random.randint(0, int((now - start_date).total_seconds()))
    return start_date + timedelta(seconds=random_seconds)


def generate_future_date(days_ahead: int = 7) -> datetime:
    """
    Generate a random datetime within the next N days.

    Args:
        days_ahead: Number of days ahead from today

    Returns:
        Random datetime within the specified range
    """
    now = datetime.now()
    random_days = random.uniform(0, days_ahead)
    return now + timedelta(days=random_days)


def generate_recent_dates(count: int, days_back: int = 7) -> List[datetime]:
    """
    Generate a list of recent dates, sorted chronologically.

    Args:
        count: Number of dates to generate
        days_back: How many days back to generate dates from

    Returns:
        List of datetime objects, sorted oldest to newest
    """
    dates = [generate_random_date(days_back) for _ in range(count)]
    return sorted(dates)


def get_date_range(start_days_ago: int = 7, end_days_ahead: int = 0) -> tuple:
    """
    Get a date range from X days ago to Y days ahead.

    Args:
        start_days_ago: Days in the past for start date
        end_days_ahead: Days in the future for end date

    Returns:
        Tuple of (start_date, end_date)
    """
    now = datetime.now()
    start_date = now - timedelta(days=start_days_ago)
    end_date = now + timedelta(days=end_days_ahead)
    return start_date, end_date


def create_simple_recurrence_pattern(interval: str = "daily", every_n: int = 1) -> Dict[str, Any]:
    """
    Create a simple recurrence pattern (DEC-010 format).

    Args:
        interval: 'daily', 'weekly', or 'monthly'
        every_n: Every N days/weeks/months

    Returns:
        Recurrence pattern dict (will be stored as JSON)
    """
    return {
        "type": "simple",
        "interval": interval,
        "every_n": every_n
    }


def create_complex_recurrence_pattern(
    days_of_week: Optional[List[int]] = None,
    weeks_of_month: Optional[List[int]] = None,
    days_of_month: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Create a complex recurrence pattern (DEC-010 format).

    Args:
        days_of_week: List of weekday numbers (1=Mon, 7=Sun)
        weeks_of_month: List of week numbers (1-4)
        days_of_month: List of day numbers (1-31)

    Returns:
        Recurrence pattern dict (will be stored as JSON)
    """
    pattern = {"type": "complex"}

    if days_of_week:
        pattern["days_of_week"] = days_of_week
    if weeks_of_month:
        pattern["weeks_of_month"] = weeks_of_month
    if days_of_month:
        pattern["days_of_month"] = days_of_month

    return pattern


def get_random_chore_data(count: int = 1) -> List[Dict[str, Any]]:
    """
    Get random chore data from predefined list.

    Args:
        count: Number of random chores to return

    Returns:
        List of chore data dictionaries
    """
    return random.sample(CHORE_DATA, min(count, len(CHORE_DATA)))


def get_random_reward_data(count: int = 1) -> List[Dict[str, Any]]:
    """
    Get random reward data from predefined list.

    Args:
        count: Number of random rewards to return

    Returns:
        List of reward data dictionaries
    """
    return random.sample(REWARD_DATA, min(count, len(REWARD_DATA)))


def is_chore_appropriate_for_kid(chore_data: Dict[str, Any], kid_name: str) -> bool:
    """
    Determine if a chore is age-appropriate for a kid.

    Args:
        chore_data: Dictionary with chore info including 'age_min'
        kid_name: Name of the kid

    Returns:
        True if chore is appropriate for the kid's age
    """
    kid_age = KID_AGES.get(kid_name, 10)  # Default to 10 if not found
    min_age = chore_data.get("age_min", 0)
    return kid_age >= min_age


def assign_chores_to_kids(chore_data_list: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Assign chores to kids based on age appropriateness.

    Args:
        chore_data_list: List of chore data dictionaries

    Returns:
        Dictionary mapping kid names to lists of appropriate chores
    """
    assignments = {kid: [] for kid in KID_NAMES}

    for chore_data in chore_data_list:
        appropriate_kids = [
            kid for kid in KID_NAMES
            if is_chore_appropriate_for_kid(chore_data, kid)
        ]

        # Assign to random subset of appropriate kids (1-3 kids)
        if appropriate_kids:
            num_to_assign = random.randint(1, min(3, len(appropriate_kids)))
            assigned_kids = random.sample(appropriate_kids, num_to_assign)

            for kid in assigned_kids:
                assignments[kid].append(chore_data)

    return assignments


def generate_ha_user_id(username: str) -> str:
    """
    Generate a fake but valid-looking Home Assistant user ID.

    Args:
        username: Username to base the ID on

    Returns:
        Fake HA user ID string
    """
    # HA user IDs are typically UUID-like strings
    import hashlib
    hash_obj = hashlib.md5(username.encode())
    hex_dig = hash_obj.hexdigest()

    # Format as UUID-like: 8-4-4-4-12
    return f"{hex_dig[:8]}-{hex_dig[8:12]}-{hex_dig[12:16]}-{hex_dig[16:20]}-{hex_dig[20:32]}"


def generate_rejection_reason() -> str:
    """
    Generate a random rejection reason.

    Returns:
        Random rejection reason string
    """
    reasons = [
        "Job not completed fully - missed spots",
        "Need to do it again, not thorough enough",
        "Forgot to put things away afterward",
        "Rushed through it, needs to be redone",
        "Didn't follow instructions completely",
        "Need to organize better, not just tidy",
    ]
    return random.choice(reasons)


def calculate_points_balance(points_history: List[Dict[str, Any]]) -> int:
    """
    Calculate current points balance from points history.

    Args:
        points_history: List of point transaction dictionaries with 'points_delta'

    Returns:
        Current points balance
    """
    return sum(entry.get("points_delta", 0) for entry in points_history)


def get_random_status_distribution() -> str:
    """
    Get a random chore instance status with realistic distribution.

    Returns:
        Status string: 'assigned', 'claimed', 'approved', or 'rejected'
    """
    # Weighted distribution: most approved, some assigned, fewer claimed/rejected
    statuses = (
        ["approved"] * 60 +      # 60% approved
        ["assigned"] * 20 +      # 20% assigned (not started)
        ["claimed"] * 15 +       # 15% claimed (pending)
        ["rejected"] * 5         # 5% rejected
    )
    return random.choice(statuses)


def generate_points_for_kid(num_completed: int, avg_points: int = 8) -> int:
    """
    Generate realistic current points for a kid based on completion history.

    Args:
        num_completed: Number of chores completed
        avg_points: Average points per chore

    Returns:
        Points balance (0-50 range)
    """
    # Base points from completed chores
    base_points = num_completed * avg_points

    # Subtract some for reward redemptions (random)
    spent = random.randint(0, int(base_points * 0.7))

    # Result should be in 0-50 range
    balance = max(0, min(50, base_points - spent))
    return balance
