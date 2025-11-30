"""
Home Assistant Supervisor API client.

This module provides utilities for interacting with the Home Assistant Supervisor API
to fetch user information and other HA-related data.
"""

import os
import logging
import requests
from typing import Optional, Dict, List
from functools import lru_cache

logger = logging.getLogger(__name__)

# Supervisor API configuration
SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN')
SUPERVISOR_API_BASE = 'http://supervisor/core/api'


class HAAPIError(Exception):
    """Exception raised for HA API errors."""
    pass


@lru_cache(maxsize=100)
def get_ha_user_info(ha_user_id: str) -> Optional[Dict[str, str]]:
    """
    Fetch user information from Home Assistant Supervisor API.

    Args:
        ha_user_id: The Home Assistant user ID

    Returns:
        Dictionary with user info:
        {
            'id': 'abc123def456',
            'username': 'john',
            'name': 'John Doe',
            'is_owner': False,
            'is_active': True
        }
        Returns None if user not found or API unavailable

    Raises:
        HAAPIError: If API request fails (but not on 404/user not found)
    """
    if not SUPERVISOR_TOKEN:
        logger.warning("SUPERVISOR_TOKEN not available, cannot fetch HA user info")
        return None

    try:
        # First, try to get user list and find the specific user
        users = get_all_ha_users()
        if users:
            for user in users:
                if user.get('id') == ha_user_id:
                    return user

        logger.debug(f"User {ha_user_id} not found in HA user list")
        return None

    except HAAPIError as e:
        logger.error(f"Failed to fetch HA user info for {ha_user_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching HA user info: {e}")
        return None


@lru_cache(maxsize=1, typed=False)
def get_all_ha_users() -> Optional[List[Dict[str, str]]]:
    """
    Fetch all users from Home Assistant.

    Returns:
        List of user dictionaries, or None if API unavailable

    Raises:
        HAAPIError: If API request fails
    """
    if not SUPERVISOR_TOKEN:
        logger.warning("SUPERVISOR_TOKEN not available")
        return None

    try:
        headers = {
            'Authorization': f'Bearer {SUPERVISOR_TOKEN}',
            'Content-Type': 'application/json'
        }

        # Try different API endpoints (HA API structure may vary)
        endpoints = [
            f'{SUPERVISOR_API_BASE}/auth',  # Primary endpoint
            f'{SUPERVISOR_API_BASE}/users',  # Alternative
        ]

        for endpoint in endpoints:
            try:
                logger.debug(f"Trying HA API endpoint: {endpoint}")
                response = requests.get(endpoint, headers=headers, timeout=5)

                if response.status_code == 200:
                    data = response.json()

                    # Extract users list from response
                    if 'data' in data and 'users' in data['data']:
                        users = data['data']['users']
                    elif 'users' in data:
                        users = data['users']
                    elif isinstance(data, list):
                        users = data
                    else:
                        logger.warning(f"Unexpected API response structure: {data}")
                        continue

                    logger.info(f"Successfully fetched {len(users)} HA users")
                    return users

                elif response.status_code == 404:
                    logger.debug(f"Endpoint not found: {endpoint}")
                    continue
                else:
                    logger.warning(f"API returned {response.status_code}: {response.text}")
                    continue

            except requests.exceptions.RequestException as e:
                logger.debug(f"Request to {endpoint} failed: {e}")
                continue

        logger.warning("All HA API endpoints failed")
        return None

    except Exception as e:
        logger.error(f"Error fetching HA users: {e}")
        return None


def get_ha_user_display_name(ha_user_id: str) -> str:
    """
    Get the display name for a Home Assistant user.

    Falls back to ha_user_id if name cannot be fetched.

    Args:
        ha_user_id: The Home Assistant user ID

    Returns:
        User's display name or ha_user_id as fallback
    """
    user_info = get_ha_user_info(ha_user_id)

    if user_info:
        # Try 'name' first, fall back to 'username', then ha_user_id
        name = user_info.get('name') or user_info.get('username') or ha_user_id
        return name

    # If API unavailable, make ha_user_id more friendly
    # Replace underscores with spaces and title case
    friendly_name = ha_user_id.replace('_', ' ').title()
    return friendly_name


def clear_ha_user_cache():
    """
    Clear the cached HA user information.

    Useful when users are added/removed in HA and cache needs refresh.
    """
    get_ha_user_info.cache_clear()
    get_all_ha_users.cache_clear()
    logger.info("HA user cache cleared")


def is_supervisor_api_available() -> bool:
    """
    Check if the Supervisor API is available.

    Returns:
        True if SUPERVISOR_TOKEN is set and API is reachable
    """
    if not SUPERVISOR_TOKEN:
        return False

    try:
        headers = {
            'Authorization': f'Bearer {SUPERVISOR_TOKEN}',
        }
        response = requests.get(
            f'http://supervisor/core/info',
            headers=headers,
            timeout=2
        )
        return response.status_code == 200
    except Exception:
        return False
