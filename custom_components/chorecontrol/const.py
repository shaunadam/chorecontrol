"""Constants for the ChoreControl integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "chorecontrol"

# Configuration
CONF_ADDON_URL: Final = "addon_url"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Defaults
DEFAULT_ADDON_URL: Final = "http://chorecontrol"
DEFAULT_SCAN_INTERVAL: Final = 30  # seconds

# Platforms
PLATFORMS: Final = ["sensor", "button", "binary_sensor"]

# Event types (from DEC-007)
EVENT_CHORE_ASSIGNED: Final = "chorecontrol_chore_assigned"
EVENT_CHORE_CLAIMED: Final = "chorecontrol_chore_claimed"
EVENT_CHORE_APPROVED: Final = "chorecontrol_chore_approved"
EVENT_CHORE_REJECTED: Final = "chorecontrol_chore_rejected"
EVENT_REWARD_CLAIMED: Final = "chorecontrol_reward_claimed"
EVENT_POINTS_ADJUSTED: Final = "chorecontrol_points_adjusted"

# Webhook
WEBHOOK_ID: Final = f"{DOMAIN}_events"

# Webhook event types (received from add-on)
EVENT_CHORE_INSTANCE_CLAIMED: Final = "chore_instance_claimed"
EVENT_CHORE_INSTANCE_APPROVED: Final = "chore_instance_approved"
EVENT_CHORE_INSTANCE_REJECTED: Final = "chore_instance_rejected"
EVENT_REWARD_CLAIM_CLAIMED: Final = "reward_claimed"
EVENT_REWARD_CLAIM_APPROVED: Final = "reward_approved"
EVENT_REWARD_CLAIM_REJECTED: Final = "reward_rejected"
EVENT_POINTS_AWARDED: Final = "points_awarded"
EVENT_INSTANCE_CREATED: Final = "chore_instance_created"

# Service names
SERVICE_CLAIM_CHORE: Final = "claim_chore"
SERVICE_APPROVE_CHORE: Final = "approve_chore"
SERVICE_REJECT_CHORE: Final = "reject_chore"
SERVICE_ADJUST_POINTS: Final = "adjust_points"
SERVICE_CLAIM_REWARD: Final = "claim_reward"
SERVICE_REFRESH_DATA: Final = "refresh_data"

# Service parameters
ATTR_CHORE_INSTANCE_ID: Final = "chore_instance_id"
ATTR_USER_ID: Final = "user_id"
ATTR_APPROVER_USER_ID: Final = "approver_user_id"
ATTR_REASON: Final = "reason"
ATTR_POINTS_DELTA: Final = "points_delta"
ATTR_REWARD_ID: Final = "reward_id"

# Sensor types
SENSOR_POINTS: Final = "points"
SENSOR_PENDING_CHORES: Final = "pending_chores"
SENSOR_CLAIMED_CHORES: Final = "claimed_chores"
SENSOR_COMPLETED_TODAY: Final = "completed_today"
SENSOR_COMPLETED_THIS_WEEK: Final = "completed_this_week"
SENSOR_PENDING_APPROVALS: Final = "pending_approvals"
SENSOR_TOTAL_KIDS: Final = "total_kids"
SENSOR_ACTIVE_CHORES: Final = "active_chores"

# API endpoints
API_USERS: Final = "/api/users"
API_CHORES: Final = "/api/chores"
API_INSTANCES: Final = "/api/instances"
API_REWARDS: Final = "/api/rewards"
API_REWARD_CLAIMS: Final = "/api/reward-claims"
API_POINTS: Final = "/api/points"
API_DASHBOARD: Final = "/api/dashboard"
API_HEALTH: Final = "/health"

# Update coordinator
UPDATE_LISTENER: Final = "update_listener"
COORDINATOR: Final = "coordinator"

# User roles
ROLE_PARENT: Final = "parent"
ROLE_KID: Final = "kid"
