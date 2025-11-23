"""
Points balance audit job.
"""

import logging

logger = logging.getLogger(__name__)


def audit_points_balances():
    """
    Audit all users' points balances against history.

    Runs nightly at 02:00. Verifies that denormalized points field
    matches calculated total from PointsHistory.
    """
    logger.info("Starting points balance audit")

    # Import inside function to avoid circular imports and to get app context
    from models import User

    try:
        users = User.query.filter_by(role='kid').all()
        discrepancies = []

        for user in users:
            if not user.verify_points_balance():
                calculated = user.calculate_current_points()
                discrepancies.append({
                    'user_id': user.id,
                    'username': user.username,
                    'stored': user.points,
                    'calculated': calculated,
                    'diff': user.points - calculated
                })

        if discrepancies:
            logger.error(f"Points discrepancies found: {discrepancies}")
            # Future: send alert to admin, auto-heal, etc.
        else:
            logger.info(f"Points audit complete: all {len(users)} user balances verified")

    except Exception as e:
        logger.error(f"Error in points balance audit: {e}")
        raise
