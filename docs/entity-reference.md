# ChoreControl Entity Reference

This document describes all entities created by the ChoreControl Home Assistant integration and their naming conventions for dashboard templating.

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

## Entity Attributes

All entities include useful attributes for filtering and templating:

### Button Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `instance_id` | int | Chore instance ID |
| `chore_name` | string | Human-readable chore name |
| `user_id` | int | Kid's user ID |
| `username` | string | Kid's username |
| `points` | int | Points for completing this chore |

### Per-Kid Sensor Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `user_id` | int | Kid's user ID |
| `username` | string | Kid's username |

## Services

ChoreControl registers the following services for use in automations and scripts:

### chorecontrol.claim_chore

Claim a chore instance for a kid.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `chore_instance_id` | Yes | The ID of the chore instance |
| `user_id` | Yes | The ID of the kid claiming |

### chorecontrol.approve_chore

Approve a claimed chore and award points.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `chore_instance_id` | Yes | The ID of the chore instance |
| `approver_user_id` | Yes | The ID of the parent approving |
| `points` | No | Override points to award |

### chorecontrol.reject_chore

Reject a claimed chore.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `chore_instance_id` | Yes | The ID of the chore instance |
| `approver_user_id` | Yes | The ID of the parent rejecting |
| `reason` | Yes | Reason for rejection |

### chorecontrol.adjust_points

Manually adjust a user's points balance.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `user_id` | Yes | The ID of the user |
| `points_delta` | Yes | Amount to add (positive) or subtract (negative) |
| `reason` | Yes | Reason for adjustment |

### chorecontrol.claim_reward

Claim a reward for a user.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `reward_id` | Yes | The ID of the reward |
| `user_id` | Yes | The ID of the user claiming |

### chorecontrol.approve_reward

Approve a pending reward claim.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `claim_id` | Yes | The ID of the reward claim |
| `approver_user_id` | Yes | The ID of the parent approving |

### chorecontrol.reject_reward

Reject a pending reward claim.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `claim_id` | Yes | The ID of the reward claim |
| `approver_user_id` | Yes | The ID of the parent rejecting |
| `reason` | Yes | Reason for rejection |

### chorecontrol.refresh_data

Force refresh all ChoreControl data from the add-on.

No parameters required.

## Filtering Examples

### Filter by Entity Attribute

Filter entities by attribute in auto-entities card:

```yaml
filter:
  include:
    - domain: button
      attributes:
        user_id: 3  # Emma's user ID
```

### Filter by Entity ID Pattern

Filter by entity_id pattern:

```yaml
filter:
  include:
    - entity_id: sensor.chorecontrol_emma_*
```

### Filter All Kid Sensors

Get all sensors for all kids:

```yaml
filter:
  include:
    - entity_id: sensor.chorecontrol_*_points
    - entity_id: sensor.chorecontrol_*_pending_chores
    - entity_id: sensor.chorecontrol_*_claimed_chores
    - entity_id: sensor.chorecontrol_*_completed_today
    - entity_id: sensor.chorecontrol_*_completed_this_week
```

### Template Examples

Display a kid's points:

```yaml
{{ states('sensor.chorecontrol_emma_points') }}
```

Check if there are pending approvals:

```yaml
{% if states('sensor.chorecontrol_pending_approvals') | int > 0 %}
  You have chores to approve!
{% endif %}
```

Get username from sensor attribute:

```yaml
{{ state_attr('sensor.chorecontrol_emma_points', 'username') }}
```

## Events

The integration fires events that can be used in automations:

| Event | Description | Data |
|-------|-------------|------|
| `chorecontrol_chore_instance_claimed` | A chore was claimed | `instance_id`, `chore_name`, `user_id`, `username`, `points` |
| `chorecontrol_chore_instance_approved` | A chore was approved | `instance_id`, `chore_name`, `user_id`, `username`, `points_awarded` |
| `chorecontrol_chore_instance_rejected` | A chore was rejected | `instance_id`, `chore_name`, `user_id`, `username`, `reason` |
| `chorecontrol_reward_claimed` | A reward was claimed | `claim_id`, `reward_name`, `user_id`, `username`, `points_cost` |
| `chorecontrol_reward_approved` | A reward was approved | `claim_id`, `reward_name`, `user_id`, `username` |
| `chorecontrol_reward_rejected` | A reward was rejected | `claim_id`, `reward_name`, `user_id`, `username`, `reason` |

### Automation Example

Send a notification when a chore is claimed:

```yaml
automation:
  - alias: "Notify when chore claimed"
    trigger:
      - platform: event
        event_type: chorecontrol_chore_instance_claimed
    action:
      - service: notify.mobile_app
        data:
          title: "Chore Claimed"
          message: >
            {{ trigger.event.data.username }} claimed
            {{ trigger.event.data.chore_name }}
```
