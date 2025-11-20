"""
Webhook utilities for Home Assistant integration.
"""

import requests
from datetime import datetime
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def get_webhook_url() -> Optional[str]:
    """Get the configured webhook URL."""
    from flask import current_app
    return current_app.config.get('HA_WEBHOOK_URL')


def build_payload(event_name: str, obj: Any, **kwargs) -> dict:
    """
    Build webhook payload for an event.

    Args:
        event_name: Name of the event
        obj: Model instance (ChoreInstance, RewardClaim, User, etc.)
        **kwargs: Additional event-specific data

    Returns:
        Webhook payload dict
    """
    payload = {
        'event': event_name,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'data': {}
    }

    # Build data based on object type
    if hasattr(obj, 'to_dict'):
        payload['data'] = obj.to_dict()
    elif isinstance(obj, dict):
        payload['data'] = obj

    # Add any additional kwargs
    payload['data'].update(kwargs)

    return payload


def fire_webhook(event_name: str, obj: Any, **kwargs) -> bool:
    """
    Fire a webhook to Home Assistant.

    Args:
        event_name: Name of the event
        obj: Model instance
        **kwargs: Additional event-specific data

    Returns:
        True if successful, False otherwise
    """
    webhook_url = get_webhook_url()

    if not webhook_url:
        logger.debug("Webhook URL not configured, skipping webhook")
        return False

    payload = build_payload(event_name, obj, **kwargs)

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=5  # Don't block for too long
        )
        response.raise_for_status()

        logger.info(f"Webhook fired: {event_name} (status {response.status_code})")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Webhook delivery timeout for event: {event_name}")
        return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Webhook delivery failed for event {event_name}: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error firing webhook {event_name}: {e}")
        return False
