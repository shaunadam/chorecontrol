"""
Timezone utilities for ChoreControl.

Provides consistent timezone-aware date and datetime functions
using the configured timezone from the TZ environment variable.
"""

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo


def get_timezone() -> ZoneInfo:
    """Get the configured timezone from environment.

    Returns:
        ZoneInfo for the configured timezone, defaults to America/Denver (MST/MDT)
    """
    tz_name = os.environ.get('TZ', 'America/Denver')
    try:
        return ZoneInfo(tz_name)
    except Exception:
        # Fallback to Denver if invalid timezone configured
        return ZoneInfo('America/Denver')


def local_now() -> datetime:
    """Get the current datetime in the configured timezone.

    Returns:
        Timezone-aware datetime in the configured local timezone
    """
    return datetime.now(get_timezone())


def local_today() -> date:
    """Get today's date in the configured timezone.

    Returns:
        Date object representing today in the configured local timezone
    """
    return local_now().date()


def utc_now() -> datetime:
    """Get the current datetime in UTC (timezone-aware).

    Use this for storing timestamps in the database.

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.now(ZoneInfo('UTC'))
