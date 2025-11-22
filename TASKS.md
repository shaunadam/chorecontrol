# Step 5: Complete HA Integration - Implementation Tasks

This document breaks down Step 5 (HA Integration) into independent implementation streams that can be executed sequentially by AI agents.

---

## Integration Primer: How ChoreControl Connects to Home Assistant

Before diving into tasks, here's how the integration architecture works:

### The Two Components

**1. Add-on (Backend)** - Already built
- Flask REST API running in a Docker container
- SQLite database with all chore/user/reward data
- Web UI accessible via HA sidebar
- Fires webhooks when events occur

**2. Integration (Custom Component)** - What we're building
- Python code that runs inside Home Assistant
- Creates entities (sensors, buttons) that appear in HA
- Registers services that automations can call
- Listens for webhook events from the add-on

### Data Flow: Polling vs Webhooks

```
┌─────────────────────┐                    ┌─────────────────────┐
│   Home Assistant    │                    │   ChoreControl      │
│                     │                    │   Add-on            │
│  ┌───────────────┐  │                    │                     │
│  │  Integration  │  │   Polling (30s)    │  ┌───────────────┐  │
│  │  Coordinator  │──┼──GET /api/users────┼─▶│   REST API    │  │
│  │               │  │  GET /api/instances│  │               │  │
│  │               │◀─┼──JSON response─────┼──│               │  │
│  └───────────────┘  │                    │  └───────────────┘  │
│         │           │                    │         │           │
│         ▼           │                    │         │           │
│  ┌───────────────┐  │                    │  ┌───────────────┐  │
│  │   Entities    │  │                    │  │   Webhooks    │  │
│  │  - Sensors    │  │    Real-time       │  │   (Events)    │  │
│  │  - Buttons    │◀─┼─chore_claimed──────┼──│               │  │
│  └───────────────┘  │  chore_approved    │  └───────────────┘  │
│                     │                    │                     │
└─────────────────────┘                    └─────────────────────┘
```

**Polling (Coordinator → Add-on)**
- Every 30 seconds, the integration asks the add-on "what's the current state?"
- Gets all users, chores, instances, rewards
- Updates all sensor values (points, pending counts, etc.)
- This is the primary data source for entity states

**Webhooks (Add-on → Integration)**
- When something happens (kid claims chore, parent approves), add-on sends event
- Integration receives event immediately (no 30-second delay)
- Triggers refresh and can send HA notifications
- Events: `chore_instance_claimed`, `chore_instance_approved`, etc.

### What Gets Created in Home Assistant

**Sensors** (read-only state)
```yaml
sensor.chorecontrol_pending_approvals: 3
sensor.chorecontrol_active_chores: 12
sensor.chorecontrol_total_kids: 2

sensor.emma_points: 45
sensor.emma_pending_chores: 2
sensor.emma_claimed_chores: 1
sensor.emma_completed_today: 3
sensor.emma_completed_this_week: 15
```

**Buttons** (actions)
```yaml
# One button per claimable chore instance per assigned kid
button.claim_take_out_trash_emma      # Instance ID 42, User ID 3
button.claim_make_bed_emma            # Instance ID 43, User ID 3
button.claim_feed_dog_jack            # Instance ID 44, User ID 4
```
- Buttons are created dynamically based on available instances
- When an instance is claimed/approved/missed, the button is removed
- Button press calls the `claim_chore` service

**Binary Sensor** (health check)
```yaml
binary_sensor.chorecontrol_api_connected: on/off
```

**Services** (callable actions)
```yaml
# Used by automations, scripts, or Lovelace buttons
chorecontrol.claim_chore:
  chore_instance_id: 42
  user_id: 3

chorecontrol.approve_chore:
  chore_instance_id: 42
  approver_user_id: 1

chorecontrol.reject_chore:
  chore_instance_id: 42
  approver_user_id: 1
  reason: "Not done properly"

chorecontrol.adjust_points:
  user_id: 3
  points_delta: -5
  reason: "Left toys out"

chorecontrol.claim_reward:
  reward_id: 2
  user_id: 3

chorecontrol.refresh_data: {}
```

### Example User Flows

**Kid Claims a Chore:**
1. Kid sees `button.claim_take_out_trash_emma` in their HA dashboard
2. Kid presses button
3. Button entity calls `chorecontrol.claim_chore` service
4. Service calls `POST /api/instances/42/claim` on add-on
5. Add-on updates database, fires `chore_instance_claimed` webhook
6. Integration receives webhook, triggers data refresh
7. Integration sends HA notification to parents
8. Sensor `emma_claimed_chores` increments from 0 to 1
9. Button `button.claim_take_out_trash_emma` is removed (instance no longer claimable)

**Parent Approves via HA:**
1. Parent sees notification "Emma claimed Take out trash"
2. Parent opens HA app, calls `chorecontrol.approve_chore` service
3. Add-on awards points, fires `chore_instance_approved` webhook
4. Integration receives webhook, sends notification to Emma
5. Sensor `emma_points` increases by chore points value
6. Sensor `emma_completed_today` increments

### Webhook Event Structure

Events sent from add-on to integration:

```json
{
  "event": "chore_instance_claimed",
  "timestamp": "2025-01-15T14:30:00Z",
  "data": {
    "instance_id": 42,
    "chore_id": 5,
    "chore_name": "Take out trash",
    "user_id": 3,
    "username": "emma",
    "points": 5
  }
}
```

The integration listens for these and can:
- Trigger immediate data refresh (faster than waiting for poll)
- Send mobile notifications to appropriate users
- Fire HA events for automations to react to

---

## Project Structure (Best Practices)

After completing all streams, the integration structure will be:

```
custom_components/chorecontrol/
├── __init__.py           # Setup, service registration
├── manifest.json         # Component metadata
├── const.py              # Constants
├── config_flow.py        # UI configuration
├── coordinator.py        # Data update coordinator
├── api_client.py         # REST API client
├── sensor.py             # Sensor entities
├── button.py             # Button entities
├── binary_sensor.py      # Health check sensor
├── services.yaml         # Service descriptions for UI
├── strings.json          # UI strings
└── translations/
    └── en.json           # English translations

tests/
├── conftest.py           # Shared fixtures
├── test_init.py          # Integration setup tests
├── test_config_flow.py   # Config flow tests
├── test_coordinator.py   # Coordinator tests
├── test_api_client.py    # API client tests
├── test_sensor.py        # Sensor entity tests
├── test_button.py        # Button entity tests
├── test_binary_sensor.py # Binary sensor tests
└── test_services.py      # Service handler tests
```

---

## Stream 1: API Client & Coordinator Completion

**Goal:** Complete the API client with all required methods and update the coordinator to fetch and organize data properly.

### Context

The API client (`api_client.py`) needs methods for all REST endpoints. The coordinator (`coordinator.py`) needs to fetch this data and organize it for easy consumption by entities.

### Tasks

#### 1.1 Complete API Client Methods

File: `custom_components/chorecontrol/api_client.py`

**Required Methods:**

```python
class ChoreControlApiClient:
    """API client for ChoreControl add-on."""

    # Health check
    async def check_health(self) -> bool:
        """Check if API is available. GET /health"""

    # Users
    async def get_users(self) -> list[dict]:
        """Get all users. GET /api/users"""

    async def get_user(self, user_id: int) -> dict:
        """Get single user. GET /api/users/{id}"""

    async def get_user_points(self, user_id: int) -> dict:
        """Get user points and history. GET /api/users/{id}/points"""

    # Chores
    async def get_chores(self, active_only: bool = True) -> list[dict]:
        """Get chores. GET /api/chores?is_active=true"""

    # Instances
    async def get_instances(
        self,
        status: str | None = None,
        user_id: int | None = None,
        due_date: str | None = None,
    ) -> list[dict]:
        """Get instances with filters. GET /api/instances"""

    async def get_due_today(self) -> list[dict]:
        """Get instances due today. GET /api/instances/due-today"""

    async def claim_chore(self, instance_id: int, user_id: int) -> dict:
        """Claim a chore. POST /api/instances/{id}/claim"""

    async def unclaim_chore(self, instance_id: int) -> dict:
        """Unclaim a chore. POST /api/instances/{id}/unclaim"""

    async def approve_chore(
        self,
        instance_id: int,
        approver_id: int,
        points: int | None = None,
    ) -> dict:
        """Approve a chore. POST /api/instances/{id}/approve"""

    async def reject_chore(
        self,
        instance_id: int,
        approver_id: int,
        reason: str,
    ) -> dict:
        """Reject a chore. POST /api/instances/{id}/reject"""

    # Rewards
    async def get_rewards(self, active_only: bool = True) -> list[dict]:
        """Get rewards. GET /api/rewards"""

    async def claim_reward(self, reward_id: int, user_id: int) -> dict:
        """Claim a reward. POST /api/rewards/{id}/claim"""

    async def unclaim_reward(self, claim_id: int) -> dict:
        """Unclaim a reward. POST /api/reward-claims/{id}/unclaim"""

    async def approve_reward(self, claim_id: int, approver_id: int) -> dict:
        """Approve reward claim. POST /api/reward-claims/{id}/approve"""

    async def reject_reward(
        self,
        claim_id: int,
        approver_id: int,
        reason: str,
    ) -> dict:
        """Reject reward claim. POST /api/reward-claims/{id}/reject"""

    # Points
    async def adjust_points(
        self,
        user_id: int,
        points_delta: int,
        reason: str,
    ) -> dict:
        """Adjust points. POST /api/points/adjust"""
```

**Implementation Notes:**
- Use `aiohttp.ClientSession` for async HTTP calls
- Handle connection errors gracefully (return empty/False, log error)
- Set appropriate timeout (10 seconds)
- Include `X-Ingress-User` header for authentication (use "system" for polling)
- Parse JSON responses, handle non-200 status codes

#### 1.2 Update Coordinator Data Structure

File: `custom_components/chorecontrol/coordinator.py`

**Update `_async_update_data()` to return:**

```python
{
    "users": [...],           # All users
    "kids": [...],            # Just kids (for easy iteration)
    "chores": [...],          # Active chores
    "instances": [...],       # All instances (for filtering)
    "rewards": [...],         # Active rewards
    "api_connected": True,    # Health check result

    # Pre-computed for sensors
    "pending_approvals_count": 5,
    "instances_by_user": {
        3: {  # user_id
            "assigned": [...],
            "claimed": [...],
            "approved_today": [...],
            "approved_this_week": [...],
        },
        4: {...}
    },
    "claimable_instances": [
        # Instances that can show as buttons
        {
            "instance_id": 42,
            "chore_name": "Take out trash",
            "chore_id": 5,
            "due_date": "2025-01-15",
            "points": 5,
            "assigned_to": 3,  # or None for shared
            "assignment_type": "individual",  # or "shared"
        },
        ...
    ],
}
```

**Logic for `instances_by_user`:**
- Filter instances by `assigned_to` or `claimed_by` matching user_id
- `assigned`: status = 'assigned'
- `claimed`: status = 'claimed'
- `approved_today`: status = 'approved' AND approved_at is today
- `approved_this_week`: status = 'approved' AND approved_at is within current week

**Logic for `claimable_instances`:**
- Status = 'assigned'
- For individual chores: one entry per instance (with assigned_to set)
- For shared chores: one entry per instance (assigned_to = None, any kid can claim)

#### 1.3 Add Helper Methods to Coordinator

```python
def get_user_by_id(self, user_id: int) -> dict | None:
    """Get user data by ID."""

def get_kid_stats(self, user_id: int) -> dict:
    """Get computed stats for a kid."""
    return {
        "points": 0,
        "pending_count": 0,
        "claimed_count": 0,
        "completed_today": 0,
        "completed_this_week": 0,
    }

def get_claimable_for_user(self, user_id: int) -> list[dict]:
    """Get claimable instances for a specific user."""
    # Returns instances where user is assigned (individual) or anyone can claim (shared)
```

### Integration Points

- Sensors will call `coordinator.get_kid_stats(user_id)` for their values
- Buttons will use `coordinator.data["claimable_instances"]`
- Binary sensor will use `coordinator.data["api_connected"]`

### Testing Requirements

Create `tests/test_api_client.py`:
- Mock HTTP responses using `aiohttp` test utilities
- Test each API method with success and error cases
- Test timeout handling
- Test header inclusion

Create `tests/test_coordinator.py`:
- Mock API client responses
- Test data transformation logic
- Test `instances_by_user` computation
- Test `claimable_instances` for both individual and shared chores
- Test helper methods

### Acceptance Criteria

- [ ] All API client methods implemented and working
- [ ] Coordinator fetches and transforms data correctly
- [ ] Health check endpoint integrated
- [ ] Error handling doesn't crash the integration
- [ ] All tests pass

---

## Stream 2: Sensor Entity Implementation

**Goal:** Complete all sensor entities to display real data from the coordinator.

### Context

The sensor entities exist but have TODOs for actual data implementation. They need to pull data from the coordinator's organized structure.

### Tasks

#### 2.1 Update Global Sensors

File: `custom_components/chorecontrol/sensor.py`

**ChoreControlPendingApprovalsSensor:**
```python
@property
def native_value(self) -> int:
    if not self.coordinator.data:
        return 0
    return self.coordinator.data.get("pending_approvals_count", 0)
```

**ChoreControlTotalKidsSensor:**
```python
@property
def native_value(self) -> int:
    if not self.coordinator.data:
        return 0
    return len(self.coordinator.data.get("kids", []))
```

**ChoreControlActiveChoresSensor:**
```python
@property
def native_value(self) -> int:
    if not self.coordinator.data:
        return 0
    return len(self.coordinator.data.get("chores", []))
```

#### 2.2 Update Per-Kid Sensors

All per-kid sensors should use `coordinator.get_kid_stats(self.user_id)`:

**ChoreControlPointsSensor:**
```python
@property
def native_value(self) -> int:
    stats = self.coordinator.get_kid_stats(self.user_id)
    return stats["points"]

@property
def extra_state_attributes(self) -> dict:
    """Return additional attributes."""
    return {
        "user_id": self.user_id,
        "username": self.username,
    }
```

**ChoreControlPendingChoresSensor:**
```python
@property
def native_value(self) -> int:
    stats = self.coordinator.get_kid_stats(self.user_id)
    return stats["pending_count"]
```

**ChoreControlClaimedChoresSensor:**
```python
@property
def native_value(self) -> int:
    stats = self.coordinator.get_kid_stats(self.user_id)
    return stats["claimed_count"]
```

**ChoreControlCompletedTodaySensor:**
```python
@property
def native_value(self) -> int:
    stats = self.coordinator.get_kid_stats(self.user_id)
    return stats["completed_today"]
```

**ChoreControlCompletedThisWeekSensor:**
```python
@property
def native_value(self) -> int:
    stats = self.coordinator.get_kid_stats(self.user_id)
    return stats["completed_this_week"]
```

#### 2.3 Add Device Info

Each sensor should include device info to group them properly:

```python
@property
def device_info(self) -> dict:
    """Return device info."""
    return {
        "identifiers": {(DOMAIN, "chorecontrol")},
        "name": "ChoreControl",
        "manufacturer": "ChoreControl",
        "model": "Chore Management System",
    }
```

For per-kid sensors, optionally create per-kid devices:

```python
@property
def device_info(self) -> dict:
    return {
        "identifiers": {(DOMAIN, f"kid_{self.user_id}")},
        "name": f"{self.username}",
        "manufacturer": "ChoreControl",
        "model": "Kid",
        "via_device": (DOMAIN, "chorecontrol"),
    }
```

#### 2.4 Handle Dynamic Entity Creation

The `async_setup_entry` currently creates per-kid sensors on first load. Need to handle:
- New kids added after initial setup
- Entity registry management

Add listener for coordinator updates:

```python
async def async_setup_entry(...):
    # ... existing code ...

    # Listen for new kids
    async def async_add_new_kid_sensors():
        """Add sensors for newly discovered kids."""
        # Compare current kids with entities in registry
        # Add sensors for new kids
        pass

    entry.async_on_unload(
        coordinator.async_add_listener(async_add_new_kid_sensors)
    )
```

### Integration Points

- Depends on Stream 1 (coordinator must provide `get_kid_stats()` and proper data structure)

### Testing Requirements

Create `tests/test_sensor.py`:
- Test each sensor type with mocked coordinator data
- Test `native_value` returns correct data
- Test handling of missing data (returns 0, not error)
- Test `extra_state_attributes`
- Test device info

### Acceptance Criteria

- [ ] All global sensors show real data
- [ ] All per-kid sensors show real data
- [ ] Sensors update when coordinator refreshes
- [ ] No errors when data is missing/empty
- [ ] Device info groups entities correctly
- [ ] All tests pass

---

## Stream 3: Button Entity & Binary Sensor Implementation

**Goal:** Create dynamic button entities for claiming chores and a binary sensor for API health.

### Context

Button entities should be created dynamically based on claimable instances. When an instance is claimed, approved, or missed, its button should be removed. This requires entity registry management.

### Tasks

#### 3.1 Implement Binary Sensor for API Health

Create new file: `custom_components/chorecontrol/binary_sensor.py`

```python
"""Binary sensor platform for ChoreControl."""
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN
from .coordinator import ChoreControlDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreControl binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    async_add_entities([ChoreControlApiConnectedSensor(coordinator)])


class ChoreControlApiConnectedSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for API connection status."""

    def __init__(self, coordinator: ChoreControlDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_api_connected"
        self._attr_name = "API connected"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_has_entity_name = True

    @property
    def is_on(self) -> bool:
        """Return True if API is connected."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("api_connected", False)

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, "chorecontrol")},
            "name": "ChoreControl",
            "manufacturer": "ChoreControl",
            "model": "Chore Management System",
        }
```

#### 3.2 Update Platforms List

File: `custom_components/chorecontrol/const.py`

```python
from homeassistant.const import Platform

PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.BINARY_SENSOR]
```

#### 3.3 Implement Dynamic Button Entities

File: `custom_components/chorecontrol/button.py`

**Key Concepts:**
- Buttons are created based on `coordinator.data["claimable_instances"]`
- Each button represents one claimable instance for one user
- When coordinator updates, compare current buttons with needed buttons
- Remove buttons for instances no longer claimable
- Add buttons for new claimable instances

```python
"""Button platform for ChoreControl."""
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN
from .coordinator import ChoreControlDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreControl button platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    # Track current buttons
    current_buttons: dict[str, ChoreControlClaimButton] = {}

    @callback
    def async_update_buttons():
        """Update button entities based on claimable instances."""
        if not coordinator.data:
            return

        claimable = coordinator.data.get("claimable_instances", [])

        # Build set of needed button unique_ids
        needed_ids = set()
        new_buttons = []

        for instance in claimable:
            instance_id = instance["instance_id"]

            if instance["assignment_type"] == "shared":
                # Shared chore: one button per kid who can claim
                for kid in coordinator.data.get("kids", []):
                    unique_id = f"{DOMAIN}_claim_{instance_id}_{kid['id']}"
                    needed_ids.add(unique_id)

                    if unique_id not in current_buttons:
                        button = ChoreControlClaimButton(
                            coordinator, instance, kid["id"], kid["username"]
                        )
                        current_buttons[unique_id] = button
                        new_buttons.append(button)
            else:
                # Individual chore: one button for assigned user
                user_id = instance["assigned_to"]
                user = coordinator.get_user_by_id(user_id)
                if user:
                    unique_id = f"{DOMAIN}_claim_{instance_id}_{user_id}"
                    needed_ids.add(unique_id)

                    if unique_id not in current_buttons:
                        button = ChoreControlClaimButton(
                            coordinator, instance, user_id, user["username"]
                        )
                        current_buttons[unique_id] = button
                        new_buttons.append(button)

        # Remove buttons no longer needed
        entity_registry = er.async_get(hass)
        for unique_id in list(current_buttons.keys()):
            if unique_id not in needed_ids:
                button = current_buttons.pop(unique_id)
                # Remove from entity registry
                entity_id = entity_registry.async_get_entity_id(
                    "button", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed button %s", entity_id)

        # Add new buttons
        if new_buttons:
            async_add_entities(new_buttons)
            _LOGGER.debug("Added %d new claim buttons", len(new_buttons))

    # Initial button creation
    async_update_buttons()

    # Listen for updates
    entry.async_on_unload(
        coordinator.async_add_listener(async_update_buttons)
    )


class ChoreControlClaimButton(CoordinatorEntity, ButtonEntity):
    """Button to claim a chore instance."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
        instance: dict[str, Any],
        user_id: int,
        username: str,
    ) -> None:
        super().__init__(coordinator)
        self.instance_id = instance["instance_id"]
        self.chore_name = instance["chore_name"]
        self.user_id = user_id
        self.username = username
        self.points = instance.get("points", 0)

        self._attr_unique_id = f"{DOMAIN}_claim_{self.instance_id}_{user_id}"
        self._attr_name = f"Claim {self.chore_name} ({username})"
        self._attr_icon = "mdi:checkbox-marked-circle-outline"
        self._attr_has_entity_name = True

    async def async_press(self) -> None:
        """Handle button press - claim the chore."""
        await self.coordinator.api_client.claim_chore(
            self.instance_id, self.user_id
        )
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "chore_name": self.chore_name,
            "user_id": self.user_id,
            "username": self.username,
            "points": self.points,
        }

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, f"kid_{self.user_id}")},
            "name": self.username,
            "manufacturer": "ChoreControl",
            "model": "Kid",
            "via_device": (DOMAIN, "chorecontrol"),
        }
```

### Integration Points

- Depends on Stream 1 (coordinator provides `claimable_instances` and `get_user_by_id()`)
- Button press calls API client methods from Stream 1

### Testing Requirements

Create `tests/test_binary_sensor.py`:
- Test API connected state reflects coordinator data
- Test False when data missing

Create `tests/test_button.py`:
- Test button creation from claimable instances
- Test button removal when instance claimed
- Test `async_press` calls correct API method
- Test shared chores create buttons for all kids
- Test individual chores create button only for assigned kid

### Acceptance Criteria

- [ ] Binary sensor shows API connection status
- [ ] Buttons created for each claimable instance
- [ ] Buttons removed when no longer claimable
- [ ] Button press claims the chore via API
- [ ] Buttons show correct attributes (points, user, etc.)
- [ ] Entity registry is properly managed
- [ ] All tests pass

---

## Stream 4: Webhook Event Handling & Notifications

**Goal:** Set up the integration to receive webhook events from the add-on and send notifications.

### Context

The add-on sends webhook events when things happen (chore claimed, approved, etc.). The integration needs to:
1. Register a webhook endpoint in HA
2. Receive and parse events
3. Trigger data refresh
4. Send notifications to appropriate users

### Tasks

#### 4.1 Register Webhook Endpoint

File: `custom_components/chorecontrol/__init__.py`

Add webhook registration during setup:

```python
from homeassistant.components.webhook import (
    async_register,
    async_unregister,
)

WEBHOOK_ID = f"{DOMAIN}_events"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... existing setup ...

    # Register webhook
    webhook_url = async_register(
        hass,
        DOMAIN,
        "ChoreControl Events",
        WEBHOOK_ID,
        handle_webhook,
    )

    # Store webhook URL for add-on configuration
    hass.data[DOMAIN][entry.entry_id]["webhook_url"] = webhook_url

    _LOGGER.info("ChoreControl webhook registered at %s", webhook_url)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... existing unload ...

    # Unregister webhook
    async_unregister(hass, WEBHOOK_ID)

    return unload_ok


async def handle_webhook(
    hass: HomeAssistant,
    webhook_id: str,
    request,
) -> None:
    """Handle incoming webhook from add-on."""
    try:
        data = await request.json()
    except ValueError:
        _LOGGER.error("Invalid JSON in webhook")
        return

    event_type = data.get("event")
    event_data = data.get("data", {})
    timestamp = data.get("timestamp")

    _LOGGER.debug(
        "Received webhook event: %s at %s",
        event_type,
        timestamp,
    )

    # Get coordinator (assumes single entry)
    for entry_data in hass.data[DOMAIN].values():
        if COORDINATOR in entry_data:
            coordinator = entry_data[COORDINATOR]
            break
    else:
        _LOGGER.error("No coordinator found for webhook")
        return

    # Process event
    await process_webhook_event(hass, coordinator, event_type, event_data)

    # Trigger data refresh
    await coordinator.async_request_refresh()
```

#### 4.2 Create Event Processor

Add event processing with notifications:

```python
async def process_webhook_event(
    hass: HomeAssistant,
    coordinator: ChoreControlDataUpdateCoordinator,
    event_type: str,
    event_data: dict,
) -> None:
    """Process webhook event and send notifications."""

    # Fire HA event for automations
    hass.bus.async_fire(
        f"{DOMAIN}_{event_type}",
        event_data,
    )

    # Send notifications based on event type
    if event_type == "chore_instance_claimed":
        # Notify parents that kid claimed a chore
        await notify_parents(
            hass,
            coordinator,
            title="Chore Claimed",
            message=f"{event_data['username']} claimed '{event_data['chore_name']}'",
            data={"action": "approve_chore", "instance_id": event_data["instance_id"]},
        )

    elif event_type == "chore_instance_approved":
        # Notify kid their chore was approved
        await notify_user(
            hass,
            event_data["user_id"],
            title="Chore Approved!",
            message=f"'{event_data['chore_name']}' was approved! +{event_data.get('points_awarded', 0)} points",
        )

    elif event_type == "chore_instance_rejected":
        # Notify kid their chore was rejected
        await notify_user(
            hass,
            event_data["user_id"],
            title="Chore Rejected",
            message=f"'{event_data['chore_name']}' was rejected: {event_data.get('reason', '')}",
        )

    elif event_type == "reward_claimed":
        # Notify parents that kid claimed a reward
        await notify_parents(
            hass,
            coordinator,
            title="Reward Claimed",
            message=f"{event_data['username']} claimed '{event_data['reward_name']}'",
        )

    elif event_type == "reward_approved":
        await notify_user(
            hass,
            event_data["user_id"],
            title="Reward Approved!",
            message=f"'{event_data['reward_name']}' was approved!",
        )

    elif event_type == "reward_rejected":
        await notify_user(
            hass,
            event_data["user_id"],
            title="Reward Rejected",
            message=f"'{event_data['reward_name']}' was rejected: {event_data.get('reason', '')}",
        )


async def notify_parents(
    hass: HomeAssistant,
    coordinator: ChoreControlDataUpdateCoordinator,
    title: str,
    message: str,
    data: dict | None = None,
) -> None:
    """Send notification to all parents."""
    # For now, use persistent_notification
    # TODO: Map HA users to ChoreControl users for targeted mobile notifications
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": title,
            "message": message,
            "notification_id": f"{DOMAIN}_{title.lower().replace(' ', '_')}",
        },
    )


async def notify_user(
    hass: HomeAssistant,
    user_id: int,
    title: str,
    message: str,
) -> None:
    """Send notification to specific user."""
    # For now, use persistent_notification
    # TODO: Map ChoreControl user_id to HA user for mobile notifications
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": title,
            "message": message,
            "notification_id": f"{DOMAIN}_{user_id}_{title.lower().replace(' ', '_')}",
        },
    )
```

#### 4.3 Add Webhook URL to Config Flow

Update config flow to show webhook URL for add-on configuration:

File: `custom_components/chorecontrol/config_flow.py`

After setup, show the webhook URL so user can configure the add-on:

```python
async def async_step_init(self, user_input=None):
    # After successful config, show webhook URL
    webhook_url = self.hass.data[DOMAIN][self.config_entry.entry_id].get("webhook_url")
    if webhook_url:
        return self.async_show_form(
            step_id="webhook_info",
            description_placeholders={"webhook_url": webhook_url},
        )
```

#### 4.4 Update Webhook URL Constants

File: `custom_components/chorecontrol/const.py`

```python
# Webhook
WEBHOOK_ID = f"{DOMAIN}_events"

# Event types (for reference)
EVENT_CHORE_CLAIMED = "chore_instance_claimed"
EVENT_CHORE_APPROVED = "chore_instance_approved"
EVENT_CHORE_REJECTED = "chore_instance_rejected"
EVENT_REWARD_CLAIMED = "reward_claimed"
EVENT_REWARD_APPROVED = "reward_approved"
EVENT_REWARD_REJECTED = "reward_rejected"
EVENT_POINTS_AWARDED = "points_awarded"
EVENT_INSTANCE_CREATED = "chore_instance_created"
```

### Integration Points

- Webhook handler triggers coordinator refresh (Stream 1)
- Events can be used by automations

### Testing Requirements

Create `tests/test_webhook.py`:
- Test webhook registration on setup
- Test webhook handler parses events correctly
- Test events fire on HA event bus
- Test coordinator refresh triggered
- Test notification service calls

### Acceptance Criteria

- [ ] Webhook endpoint registered during setup
- [ ] Webhook URL available for add-on configuration
- [ ] Events parsed and processed correctly
- [ ] HA events fired for automations
- [ ] Notifications sent to appropriate users
- [ ] Data refresh triggered after events
- [ ] Webhook unregistered on unload
- [ ] All tests pass

---

## Stream 5: Services & Service Descriptions

**Goal:** Complete service implementations and add proper descriptions for the HA UI.

### Context

Services are registered but need complete implementations with proper error handling. Service descriptions are needed for the HA developer tools UI.

### Tasks

#### 5.1 Add services.yaml

Create file: `custom_components/chorecontrol/services.yaml`

```yaml
claim_chore:
  name: Claim chore
  description: Mark a chore instance as claimed by a kid
  fields:
    chore_instance_id:
      name: Chore instance ID
      description: The ID of the chore instance to claim
      required: true
      selector:
        number:
          min: 1
          mode: box
    user_id:
      name: User ID
      description: The ID of the kid claiming the chore
      required: true
      selector:
        number:
          min: 1
          mode: box

approve_chore:
  name: Approve chore
  description: Approve a claimed chore and award points
  fields:
    chore_instance_id:
      name: Chore instance ID
      description: The ID of the chore instance to approve
      required: true
      selector:
        number:
          min: 1
          mode: box
    approver_user_id:
      name: Approver user ID
      description: The ID of the parent approving
      required: true
      selector:
        number:
          min: 1
          mode: box
    points:
      name: Points override
      description: Override points to award (optional)
      required: false
      selector:
        number:
          mode: box

reject_chore:
  name: Reject chore
  description: Reject a claimed chore
  fields:
    chore_instance_id:
      name: Chore instance ID
      description: The ID of the chore instance to reject
      required: true
      selector:
        number:
          min: 1
          mode: box
    approver_user_id:
      name: Approver user ID
      description: The ID of the parent rejecting
      required: true
      selector:
        number:
          min: 1
          mode: box
    reason:
      name: Reason
      description: Reason for rejection
      required: true
      selector:
        text:

adjust_points:
  name: Adjust points
  description: Manually adjust a user's points balance
  fields:
    user_id:
      name: User ID
      description: The ID of the user to adjust points for
      required: true
      selector:
        number:
          min: 1
          mode: box
    points_delta:
      name: Points delta
      description: Amount to add (positive) or subtract (negative)
      required: true
      selector:
        number:
          mode: box
    reason:
      name: Reason
      description: Reason for adjustment
      required: true
      selector:
        text:

claim_reward:
  name: Claim reward
  description: Claim a reward for a user
  fields:
    reward_id:
      name: Reward ID
      description: The ID of the reward to claim
      required: true
      selector:
        number:
          min: 1
          mode: box
    user_id:
      name: User ID
      description: The ID of the user claiming the reward
      required: true
      selector:
        number:
          min: 1
          mode: box

approve_reward:
  name: Approve reward
  description: Approve a pending reward claim
  fields:
    claim_id:
      name: Claim ID
      description: The ID of the reward claim to approve
      required: true
      selector:
        number:
          min: 1
          mode: box
    approver_user_id:
      name: Approver user ID
      description: The ID of the parent approving
      required: true
      selector:
        number:
          min: 1
          mode: box

reject_reward:
  name: Reject reward
  description: Reject a pending reward claim
  fields:
    claim_id:
      name: Claim ID
      description: The ID of the reward claim to reject
      required: true
      selector:
        number:
          min: 1
          mode: box
    approver_user_id:
      name: Approver user ID
      description: The ID of the parent rejecting
      required: true
      selector:
        number:
          min: 1
          mode: box
    reason:
      name: Reason
      description: Reason for rejection
      required: true
      selector:
        text:

refresh_data:
  name: Refresh data
  description: Force refresh all ChoreControl data from the add-on
```

#### 5.2 Add Reward Approval Services

File: `custom_components/chorecontrol/__init__.py`

Add missing service handlers and schemas:

```python
# Add to imports
from .const import (
    # ... existing ...
    ATTR_CLAIM_ID,
    ATTR_POINTS,
    SERVICE_APPROVE_REWARD,
    SERVICE_REJECT_REWARD,
)

# Add new schemas
SERVICE_APPROVE_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CHORE_INSTANCE_ID): cv.positive_int,
        vol.Required(ATTR_APPROVER_USER_ID): cv.positive_int,
        vol.Optional(ATTR_POINTS): int,  # Allow points override
    }
)

SERVICE_APPROVE_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CLAIM_ID): cv.positive_int,
        vol.Required(ATTR_APPROVER_USER_ID): cv.positive_int,
    }
)

SERVICE_REJECT_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CLAIM_ID): cv.positive_int,
        vol.Required(ATTR_APPROVER_USER_ID): cv.positive_int,
        vol.Required(ATTR_REASON): cv.string,
    }
)

# Add handlers
async def handle_approve_reward(call: ServiceCall) -> None:
    """Handle approve_reward service call."""
    claim_id = call.data[ATTR_CLAIM_ID]
    approver_user_id = call.data[ATTR_APPROVER_USER_ID]

    await coordinator.api_client.approve_reward(claim_id, approver_user_id)
    await coordinator.async_request_refresh()

async def handle_reject_reward(call: ServiceCall) -> None:
    """Handle reject_reward service call."""
    claim_id = call.data[ATTR_CLAIM_ID]
    approver_user_id = call.data[ATTR_APPROVER_USER_ID]
    reason = call.data[ATTR_REASON]

    await coordinator.api_client.reject_reward(claim_id, approver_user_id, reason)
    await coordinator.async_request_refresh()

# Register services
hass.services.async_register(
    DOMAIN,
    SERVICE_APPROVE_REWARD,
    handle_approve_reward,
    schema=SERVICE_APPROVE_REWARD_SCHEMA,
)

hass.services.async_register(
    DOMAIN,
    SERVICE_REJECT_REWARD,
    handle_reject_reward,
    schema=SERVICE_REJECT_REWARD_SCHEMA,
)
```

#### 5.3 Update Constants

File: `custom_components/chorecontrol/const.py`

```python
# Service names
SERVICE_CLAIM_CHORE = "claim_chore"
SERVICE_APPROVE_CHORE = "approve_chore"
SERVICE_REJECT_CHORE = "reject_chore"
SERVICE_ADJUST_POINTS = "adjust_points"
SERVICE_CLAIM_REWARD = "claim_reward"
SERVICE_APPROVE_REWARD = "approve_reward"
SERVICE_REJECT_REWARD = "reject_reward"
SERVICE_REFRESH_DATA = "refresh_data"

# Service attributes
ATTR_CHORE_INSTANCE_ID = "chore_instance_id"
ATTR_USER_ID = "user_id"
ATTR_APPROVER_USER_ID = "approver_user_id"
ATTR_REASON = "reason"
ATTR_POINTS_DELTA = "points_delta"
ATTR_REWARD_ID = "reward_id"
ATTR_CLAIM_ID = "claim_id"
ATTR_POINTS = "points"
```

#### 5.4 Add Error Handling to Service Handlers

Wrap service calls with proper error handling:

```python
from homeassistant.exceptions import HomeAssistantError

async def handle_claim_chore(call: ServiceCall) -> None:
    """Handle claim_chore service call."""
    try:
        chore_instance_id = call.data[ATTR_CHORE_INSTANCE_ID]
        user_id = call.data[ATTR_USER_ID]

        result = await coordinator.api_client.claim_chore(chore_instance_id, user_id)

        if result is None:
            raise HomeAssistantError(
                f"Failed to claim chore instance {chore_instance_id}"
            )

        await coordinator.async_request_refresh()

    except Exception as err:
        _LOGGER.error("Error claiming chore: %s", err)
        raise HomeAssistantError(f"Error claiming chore: {err}") from err
```

### Integration Points

- Services call API client methods (Stream 1)
- Services trigger coordinator refresh (Stream 1)

### Testing Requirements

Create `tests/test_services.py`:
- Test each service handler calls correct API method
- Test service schemas validate properly
- Test error handling raises HomeAssistantError
- Test coordinator refresh triggered after service call

### Acceptance Criteria

- [ ] All services have descriptions in services.yaml
- [ ] Reward approval services added
- [ ] Points override supported in approve_chore
- [ ] Error handling in all service handlers
- [ ] Services appear correctly in HA developer tools
- [ ] All tests pass

---

## Stream 6: Testing Setup & Integration Tests

**Goal:** Set up pytest-homeassistant-custom-component and create comprehensive tests for all streams.

### Context

Tests should live in `tests/` at the project root (not in `addon/tests/`). Need to set up the HA testing framework and ensure all components are properly tested.

### Tasks

#### 6.1 Set Up Testing Infrastructure

Create `tests/conftest.py`:

```python
"""Fixtures for ChoreControl tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.chorecontrol.const import DOMAIN


@pytest.fixture
def hass(event_loop):
    """Return a Home Assistant instance for testing."""
    hass = HomeAssistant()
    hass.config.config_dir = "/tmp/test_config"
    yield hass
    event_loop.run_until_complete(hass.async_stop())


@pytest.fixture
def mock_api_client():
    """Return a mocked API client."""
    client = AsyncMock()

    # Default responses
    client.check_health.return_value = True
    client.get_users.return_value = [
        {"id": 1, "username": "parent1", "role": "parent", "points": 0},
        {"id": 2, "username": "emma", "role": "kid", "points": 45},
        {"id": 3, "username": "jack", "role": "kid", "points": 30},
    ]
    client.get_chores.return_value = [
        {"id": 1, "name": "Take out trash", "points": 5, "is_active": True},
        {"id": 2, "name": "Make bed", "points": 3, "is_active": True},
    ]
    client.get_instances.return_value = [
        {
            "id": 1,
            "chore_id": 1,
            "status": "assigned",
            "assigned_to": 2,
            "due_date": "2025-01-15",
        },
    ]
    client.get_rewards.return_value = [
        {"id": 1, "name": "Ice cream", "points_cost": 20, "is_active": True},
    ]

    return client


@pytest.fixture
def mock_coordinator(mock_api_client):
    """Return a mocked coordinator with test data."""
    coordinator = MagicMock()
    coordinator.api_client = mock_api_client
    coordinator.data = {
        "users": mock_api_client.get_users.return_value,
        "kids": [u for u in mock_api_client.get_users.return_value if u["role"] == "kid"],
        "chores": mock_api_client.get_chores.return_value,
        "instances": mock_api_client.get_instances.return_value,
        "rewards": mock_api_client.get_rewards.return_value,
        "api_connected": True,
        "pending_approvals_count": 2,
        "instances_by_user": {
            2: {
                "assigned": [{"id": 1}],
                "claimed": [],
                "approved_today": [{"id": 5}],
                "approved_this_week": [{"id": 5}, {"id": 6}],
            },
            3: {
                "assigned": [],
                "claimed": [{"id": 2}],
                "approved_today": [],
                "approved_this_week": [{"id": 7}],
            },
        },
        "claimable_instances": [
            {
                "instance_id": 1,
                "chore_name": "Take out trash",
                "chore_id": 1,
                "due_date": "2025-01-15",
                "points": 5,
                "assigned_to": 2,
                "assignment_type": "individual",
            },
        ],
    }

    def get_kid_stats(user_id):
        if user_id == 2:
            return {
                "points": 45,
                "pending_count": 1,
                "claimed_count": 0,
                "completed_today": 1,
                "completed_this_week": 2,
            }
        return {
            "points": 30,
            "pending_count": 0,
            "claimed_count": 1,
            "completed_today": 0,
            "completed_this_week": 1,
        }

    coordinator.get_kid_stats = get_kid_stats
    coordinator.get_user_by_id = lambda uid: next(
        (u for u in coordinator.data["users"] if u["id"] == uid), None
    )
    coordinator.async_request_refresh = AsyncMock()

    return coordinator
```

#### 6.2 Update requirements-dev.txt

Add to `addon/requirements-dev.txt` (or create `requirements-test.txt` at root):

```
pytest>=7.0
pytest-asyncio>=0.21
pytest-homeassistant-custom-component>=0.13
aiohttp
```

#### 6.3 Create pytest.ini

Create `pytest.ini` at project root:

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
python_files = test_*.py
python_functions = test_*
```

#### 6.4 Create Test Files

Each test file should comprehensively test its component:

**tests/test_init.py** - Integration setup
- Test `async_setup_entry` creates coordinator
- Test services are registered
- Test `async_unload_entry` cleans up

**tests/test_config_flow.py** - Configuration
- Test user can configure add-on URL
- Test validation of URL
- Test options flow

**tests/test_api_client.py** - API client
- Test each method with mock HTTP responses
- Test error handling
- Test timeouts

**tests/test_coordinator.py** - Data coordinator
- Test data fetching and transformation
- Test `instances_by_user` computation
- Test `claimable_instances` for shared/individual
- Test helper methods

**tests/test_sensor.py** - Sensor entities
- Test each sensor type
- Test `native_value` with various data
- Test handling of missing data

**tests/test_button.py** - Button entities
- Test dynamic creation/removal
- Test `async_press` calls API
- Test shared vs individual buttons

**tests/test_binary_sensor.py** - Binary sensor
- Test API connected status

**tests/test_services.py** - Service handlers
- Test each service handler
- Test error handling
- Test coordinator refresh

**tests/test_webhook.py** - Webhook handling
- Test event processing
- Test notifications
- Test HA event firing

#### 6.5 Example Test Implementation

```python
# tests/test_sensor.py
"""Tests for ChoreControl sensors."""
import pytest
from unittest.mock import MagicMock

from custom_components.chorecontrol.sensor import (
    ChoreControlPointsSensor,
    ChoreControlPendingApprovalsSensor,
)


class TestPendingApprovalsSensor:
    """Tests for pending approvals sensor."""

    def test_native_value(self, mock_coordinator):
        """Test sensor returns correct value."""
        sensor = ChoreControlPendingApprovalsSensor(mock_coordinator)
        assert sensor.native_value == 2

    def test_native_value_no_data(self, mock_coordinator):
        """Test sensor returns 0 when no data."""
        mock_coordinator.data = None
        sensor = ChoreControlPendingApprovalsSensor(mock_coordinator)
        assert sensor.native_value == 0


class TestPointsSensor:
    """Tests for kid points sensor."""

    def test_native_value(self, mock_coordinator):
        """Test sensor returns correct points."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlPointsSensor(mock_coordinator, user)
        assert sensor.native_value == 45

    def test_extra_state_attributes(self, mock_coordinator):
        """Test sensor has correct attributes."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlPointsSensor(mock_coordinator, user)
        attrs = sensor.extra_state_attributes
        assert attrs["user_id"] == 2
        assert attrs["username"] == "emma"
```

### Integration Points

- Tests verify all streams work correctly
- Tests use mocked API responses

### Acceptance Criteria

- [ ] pytest-homeassistant-custom-component configured
- [ ] conftest.py with shared fixtures
- [ ] Test file for each component
- [ ] All tests pass
- [ ] Good coverage of edge cases
- [ ] CI can run tests (pytest command works)

---

## Stream Execution Order

Execute streams in this order:

1. **Stream 1: API Client & Coordinator** - Foundation for all other streams
2. **Stream 2: Sensor Implementation** - Uses coordinator data
3. **Stream 3: Button & Binary Sensor** - Uses coordinator data and API client
4. **Stream 4: Webhook Handling** - Uses coordinator refresh
5. **Stream 5: Services** - Uses API client and coordinator
6. **Stream 6: Testing** - Tests all previous streams

Each stream should be fully tested before moving to the next.

---

## Cross-Stream Integration Points

### API Response Format

All streams depend on these API response formats. API client must return data in this structure:

**GET /api/users response:**
```json
[
  {
    "id": 1,
    "ha_user_id": "abc123",
    "username": "parent1",
    "role": "parent",
    "points": 0
  }
]
```

**GET /api/instances response:**
```json
[
  {
    "id": 42,
    "chore_id": 5,
    "chore": {
      "name": "Take out trash",
      "points": 5,
      "assignment_type": "individual"
    },
    "status": "assigned",
    "assigned_to": 3,
    "due_date": "2025-01-15",
    "claimed_by": null,
    "claimed_at": null
  }
]
```

### Coordinator Data Keys

All entity streams expect these keys in `coordinator.data`:
- `users`, `kids`, `chores`, `instances`, `rewards`
- `api_connected`
- `pending_approvals_count`
- `instances_by_user`
- `claimable_instances`

### Entity Unique IDs

Consistent naming for entity registry:
- Sensors: `{DOMAIN}_{type}` or `{DOMAIN}_{username}_{type}`
- Buttons: `{DOMAIN}_claim_{instance_id}_{user_id}`
- Binary sensors: `{DOMAIN}_api_connected`

### Service Names

Consistent service naming in all streams:
- `chorecontrol.claim_chore`
- `chorecontrol.approve_chore`
- `chorecontrol.reject_chore`
- `chorecontrol.adjust_points`
- `chorecontrol.claim_reward`
- `chorecontrol.approve_reward`
- `chorecontrol.reject_reward`
- `chorecontrol.refresh_data`

---

## Notes for AI Agents

### Before Starting Each Stream

1. Read this entire document for context
2. Read the existing code in `custom_components/chorecontrol/`
3. Understand the data flow described in the Integration Primer
4. Check what constants are already defined in `const.py`

### During Implementation

1. Follow Home Assistant coding standards
2. Use type hints throughout
3. Add logging at appropriate levels (debug for normal ops, error for failures)
4. Handle missing data gracefully (return defaults, don't crash)
5. Keep entity names user-friendly

### After Completing Stream

1. Run all tests: `pytest tests/`
2. Run linting: `ruff check custom_components/`
3. Verify no runtime errors by loading in HA (if possible)
4. Update any TODOs left in code

### Testing Philosophy

- Test the happy path
- Test error cases (API down, missing data)
- Test edge cases (no kids, no chores, empty lists)
- Mock external dependencies (API calls)
- Don't test HA internals (trust the framework)

---

## Stream 7: Dashboard Examples & Documentation

**Goal:** Create example dashboard configurations that work with dynamic entities, and document entity naming patterns.

### Context

ChoreControl creates many dynamic entities (buttons for each claimable chore, sensors per kid). Users need guidance on how to build dashboards that automatically adapt to these changing entities.

### Tasks

#### 7.1 Document Entity Naming Patterns

Create `docs/entity-reference.md`:

```markdown
# ChoreControl Entity Reference

## Entity Naming Conventions

All ChoreControl entities follow predictable naming patterns for easy dashboard templating.

### Sensors

| Entity ID Pattern | Description | Example |
|-------------------|-------------|---------|
| `sensor.chorecontrol_pending_approvals` | Global pending approvals count | - |
| `sensor.chorecontrol_total_kids` | Total number of kids | - |
| `sensor.chorecontrol_active_chores` | Number of active chores | - |
| `sensor.chorecontrol_{username}_points` | Kid's point balance | `sensor.chorecontrol_emma_points` |
| `sensor.chorecontrol_{username}_pending_chores` | Kid's assigned chores count | `sensor.chorecontrol_emma_pending_chores` |
| `sensor.chorecontrol_{username}_claimed_chores` | Kid's claimed (awaiting approval) count | `sensor.chorecontrol_emma_claimed_chores` |
| `sensor.chorecontrol_{username}_completed_today` | Kid's completions today | `sensor.chorecontrol_emma_completed_today` |
| `sensor.chorecontrol_{username}_completed_this_week` | Kid's completions this week | `sensor.chorecontrol_emma_completed_this_week` |

### Buttons

| Entity ID Pattern | Description | Example |
|-------------------|-------------|---------|
| `button.chorecontrol_claim_{instance_id}_{user_id}` | Claim button for specific chore instance | `button.chorecontrol_claim_42_3` |

### Binary Sensors

| Entity ID Pattern | Description | Example |
|-------------------|-------------|---------|
| `binary_sensor.chorecontrol_api_connected` | API connection status | - |

### Entity Attributes

All entities include useful attributes for filtering and templating:

**Button attributes:**
- `instance_id`: Chore instance ID
- `chore_name`: Human-readable chore name
- `user_id`: Kid's user ID
- `username`: Kid's username
- `points`: Points for completing this chore

**Per-kid sensor attributes:**
- `user_id`: Kid's user ID
- `username`: Kid's username

### Filtering Examples

Filter entities by attribute in auto-entities:
```yaml
filter:
  include:
    - domain: button
      attributes:
        user_id: 3  # Emma's user ID
```

Filter by entity_id pattern:
```yaml
filter:
  include:
    - entity_id: sensor.chorecontrol_emma_*
```
```

#### 7.2 Create Example Kid Dashboard

Create `docs/examples/kid-dashboard.yaml`:

```yaml
# Kid Dashboard Example
# Uses auto-entities card (install from HACS)
# Replace 'emma' and user_id '3' with actual values

title: Emma's Chores
views:
  - title: My Chores
    path: my-chores
    cards:
      # Points display
      - type: markdown
        content: |
          # My Points: {{ states('sensor.chorecontrol_emma_points') }} ⭐

      # Stats row
      - type: horizontal-stack
        cards:
          - type: entity
            entity: sensor.chorecontrol_emma_pending_chores
            name: To Do
            icon: mdi:clipboard-list
          - type: entity
            entity: sensor.chorecontrol_emma_claimed_chores
            name: Waiting
            icon: mdi:clock-outline
          - type: entity
            entity: sensor.chorecontrol_emma_completed_today
            name: Done Today
            icon: mdi:check-circle

      # Claimable chores - auto-populated
      - type: custom:auto-entities
        card:
          type: entities
          title: Chores I Can Claim
          show_header_toggle: false
        filter:
          include:
            - domain: button
              attributes:
                user_id: 3  # Emma's user ID
        sort:
          method: attribute
          attribute: chore_name
        show_empty: true
        empty_config:
          type: markdown
          content: "🎉 No chores right now!"

      # Weekly progress
      - type: entity
        entity: sensor.chorecontrol_emma_completed_this_week
        name: Completed This Week
        icon: mdi:calendar-check
```

#### 7.3 Create Example Parent Dashboard

Create `docs/examples/parent-dashboard.yaml`:

```yaml
# Parent Dashboard Example
# Shows pending approvals and all kids' status

title: ChoreControl
views:
  - title: Overview
    path: overview
    cards:
      # System status
      - type: entities
        title: System Status
        entities:
          - entity: binary_sensor.chorecontrol_api_connected
            name: API Status
          - entity: sensor.chorecontrol_pending_approvals
            name: Pending Approvals
          - entity: sensor.chorecontrol_active_chores
            name: Active Chores
          - entity: sensor.chorecontrol_total_kids
            name: Total Kids

      # Kids overview - one card per kid
      - type: horizontal-stack
        cards:
          - type: vertical-stack
            cards:
              - type: markdown
                content: "## Emma"
              - type: entity
                entity: sensor.chorecontrol_emma_points
                name: Points
              - type: entity
                entity: sensor.chorecontrol_emma_completed_today
                name: Done Today

          - type: vertical-stack
            cards:
              - type: markdown
                content: "## Jack"
              - type: entity
                entity: sensor.chorecontrol_jack_points
                name: Points
              - type: entity
                entity: sensor.chorecontrol_jack_completed_today
                name: Done Today

  - title: Approvals
    path: approvals
    cards:
      # Pending approval count
      - type: entity
        entity: sensor.chorecontrol_pending_approvals
        name: Chores Awaiting Approval

      # Note: Approval actions are best done in the add-on Web UI
      # or via service calls. Example service call button:
      - type: markdown
        content: |
          ## Quick Actions

          For detailed approvals with rejection reasons,
          use the [ChoreControl Web UI](/hassio/ingress/chorecontrol).

      # Example: Approve via service call
      # Requires knowing the instance ID
      - type: button
        name: Approve Instance #42
        tap_action:
          action: call-service
          service: chorecontrol.approve_chore
          service_data:
            chore_instance_id: 42
            approver_user_id: 1
```

#### 7.4 Create Dynamic Dashboard with Decluttering Card

Create `docs/examples/dynamic-dashboard.yaml`:

```yaml
# Dynamic Dashboard using Decluttering Card
# Install decluttering-card from HACS
# This allows you to define templates and reuse them

# First, add to your configuration.yaml:
# decluttering_templates: !include decluttering_templates.yaml

# decluttering_templates.yaml:
kid_card:
  card:
    type: vertical-stack
    cards:
      - type: markdown
        content: "## [[name]]"
      - type: horizontal-stack
        cards:
          - type: entity
            entity: sensor.chorecontrol_[[username]]_points
            name: Points
          - type: entity
            entity: sensor.chorecontrol_[[username]]_completed_today
            name: Today
      - type: custom:auto-entities
        card:
          type: entities
          title: Available Chores
        filter:
          include:
            - domain: button
              attributes:
                user_id: [[user_id]]
        show_empty: true
        empty_config:
          type: markdown
          content: "All done! 🎉"

# Dashboard usage:
views:
  - title: Kids
    cards:
      - type: custom:decluttering-card
        template: kid_card
        variables:
          - name: Emma
          - username: emma
          - user_id: 3

      - type: custom:decluttering-card
        template: kid_card
        variables:
          - name: Jack
          - username: jack
          - user_id: 4
```

#### 7.5 Create Mushroom Card Example (Modern UI)

Create `docs/examples/mushroom-dashboard.yaml`:

```yaml
# Modern dashboard using Mushroom cards (HACS)
# Cleaner, more mobile-friendly design

title: Chores
views:
  - title: Emma
    path: emma
    cards:
      # Points chip at top
      - type: custom:mushroom-chips-card
        chips:
          - type: template
            icon: mdi:star
            content: "{{ states('sensor.chorecontrol_emma_points') }} points"
            icon_color: amber

      # Stats in a nice grid
      - type: grid
        columns: 2
        cards:
          - type: custom:mushroom-entity-card
            entity: sensor.chorecontrol_emma_pending_chores
            name: To Do
            icon_color: orange
          - type: custom:mushroom-entity-card
            entity: sensor.chorecontrol_emma_claimed_chores
            name: Waiting
            icon_color: blue
          - type: custom:mushroom-entity-card
            entity: sensor.chorecontrol_emma_completed_today
            name: Done Today
            icon_color: green
          - type: custom:mushroom-entity-card
            entity: sensor.chorecontrol_emma_completed_this_week
            name: This Week
            icon_color: teal

      # Claim buttons
      - type: custom:auto-entities
        card:
          type: grid
          columns: 1
        card_param: cards
        filter:
          include:
            - domain: button
              attributes:
                user_id: 3
              options:
                type: custom:mushroom-entity-card
                tap_action:
                  action: toggle
                icon_color: cyan
        show_empty: true
        empty_config:
          type: custom:mushroom-template-card
          primary: All done!
          secondary: No chores available
          icon: mdi:party-popper
          icon_color: green
```

#### 7.6 Document Required HACS Integrations

Add to `docs/dashboard-setup.md`:

```markdown
# Dashboard Setup Guide

## Required Custom Cards

For the best dashboard experience, install these from HACS:

### Essential
- **auto-entities** - Automatically shows entities matching patterns
  - Required for dynamic button display
  - [GitHub](https://github.com/thomasloven/lovelace-auto-entities)

### Recommended
- **mushroom** - Modern, clean card designs
  - [GitHub](https://github.com/piitaya/lovelace-mushroom)

- **decluttering-card** - Reusable card templates
  - Great for multi-kid setups
  - [GitHub](https://github.com/custom-cards/decluttering-card)

- **card-mod** - CSS styling for cards
  - [GitHub](https://github.com/thomasloven/lovelace-card-mod)

## Installation

1. Install HACS if you haven't already
2. Go to HACS → Frontend
3. Search for each card and install
4. Restart Home Assistant
5. Clear browser cache

## Finding Your User IDs

To use these dashboards, you need to know each kid's user_id.

### Option 1: Developer Tools
1. Go to Developer Tools → States
2. Search for `sensor.chorecontrol_`
3. Click on a kid's sensor
4. Look at the `user_id` attribute

### Option 2: Add-on API
```bash
curl http://localhost:8099/api/users
```

### Option 3: Add-on Web UI
Go to the ChoreControl add-on → Users page
```

### Integration Points

- Uses entity naming patterns defined in Stream 2 and Stream 3
- Relies on entity attributes being set correctly

### Testing Requirements

Manual testing only:
- Load example dashboards in HA
- Verify auto-entities finds buttons correctly
- Verify attribute filtering works
- Test with 0, 1, and multiple claimable chores

### Acceptance Criteria

- [ ] Entity reference documentation complete
- [ ] Kid dashboard example works with auto-entities
- [ ] Parent dashboard example shows all sensors
- [ ] Decluttering template example works
- [ ] Mushroom card example provides modern UI
- [ ] HACS requirements documented
- [ ] User ID lookup instructions included

---

## Stream Execution Order

Execute streams in this order:

1. **Stream 1: API Client & Coordinator** - Foundation for all other streams
2. **Stream 2: Sensor Implementation** - Uses coordinator data
3. **Stream 3: Button & Binary Sensor** - Uses coordinator data and API client
4. **Stream 4: Webhook Handling** - Uses coordinator refresh
5. **Stream 5: Services** - Uses API client and coordinator
6. **Stream 6: Testing** - Tests all previous streams
7. **Stream 7: Dashboard Examples** - Documents how to use entities

Each stream should be fully tested before moving to the next.

---

---

## Agent Prompt Template

Use this prompt when starting each stream. Replace `{STREAM_NUMBER}` with the stream number (1-7).

```
You are implementing Stream {STREAM_NUMBER} of the ChoreControl Home Assistant integration.

## Your Task

Read TASKS.md thoroughly, focusing on:
1. The "Integration Primer" section at the top (understand the architecture)
2. Stream {STREAM_NUMBER} section (your specific tasks)
3. "Cross-Stream Integration Points" section (shared conventions)
4. "Notes for AI Agents" section (coding standards)

## Before You Start

1. Read the existing integration code in `custom_components/chorecontrol/`
2. Understand what's already implemented vs what you need to add
3. Check `const.py` for existing constants you should use

## Implementation Requirements

- Follow Home Assistant coding standards
- Use type hints throughout
- Add logging (debug for normal ops, error for failures)
- Handle missing data gracefully (return defaults, don't crash)
- Keep entity names user-friendly

## Testing

- Create tests in `tests/` directory (not `addon/tests/`)
- Use pytest-homeassistant-custom-component
- Mock external dependencies (API calls)
- Test happy path, error cases, and edge cases

## When Complete

1. Run all tests: `pytest tests/ -v`
2. Run linting: `ruff check custom_components/`
3. Verify all acceptance criteria in your stream are met
4. Report what was implemented and any issues encountered

## Important Notes

- This is Stream {STREAM_NUMBER} of 7 - previous streams may or may not be complete
- If you need something from a previous stream that doesn't exist, implement a minimal stub
- Don't modify code outside your stream's scope unless necessary for integration
- Ask if anything is unclear before proceeding
```

---

**Document Version**: 1.1
**Created**: 2025-01-21
**Updated**: 2025-01-21
**Status**: Ready for Implementation
