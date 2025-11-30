# Notifications in ChoreControl

ChoreControl provides targeted notifications to family members through Home Assistant automations. This guide explains the notification architecture and provides example automations.

## Overview

ChoreControl fires webhook events whenever significant actions occur (chore claimed, approved, reward claimed, etc.). You create Home Assistant automations that listen for these events and send notifications to the appropriate users.

**Key Principle**: ChoreControl provides the events and data; you control the notification logic via automations.

## Architecture

```
ChoreControl Addon
    ↓ (fires webhook event)
Home Assistant Event Bus
    ↓ (triggers automation)
Your Automation
    ↓ (sends notification)
User's Device (notify.mobile_app_*)
```

### Why Automations?

This approach gives you complete control over:
- **Who** gets notified (parents, specific kids, everyone)
- **When** notifications are sent (quiet hours, delays, etc.)
- **How** notifications look (custom messages, actions, images)
- **What** triggers notifications (filter by chore type, points threshold, etc.)

## Webhook Events

ChoreControl fires these events to `http://supervisor/core/api/events/<event_name>`:

| Event | Fired When | Key Data |
|-------|------------|----------|
| `chorecontrol_chore_claimed` | Kid claims a chore | `kid_id`, `kid_name`, `chore_name`, `instance_id` |
| `chorecontrol_chore_approved` | Parent approves chore | `kid_id`, `kid_name`, `chore_name`, `points_awarded`, `approver_name` |
| `chorecontrol_chore_rejected` | Parent rejects chore | `kid_id`, `kid_name`, `chore_name`, `rejection_reason`, `rejecter_name` |
| `chorecontrol_reward_claimed` | Kid claims reward | `kid_id`, `kid_name`, `reward_name`, `points_cost` |
| `chorecontrol_reward_approved` | Parent approves reward | `kid_id`, `kid_name`, `reward_name`, `approver_name` |
| `chorecontrol_reward_rejected` | Parent rejects reward | `kid_id`, `kid_name`, `reward_name`, `rejection_reason` |
| `chorecontrol_chore_assigned` | New chore instance created | `assignee_id`, `assignee_name`, `chore_name`, `due_date` |
| `chorecontrol_chore_missed` | Chore not completed by due date | `assignee_id`, `assignee_name`, `chore_name`, `due_date` |

## User Mapping for Notifications

To send targeted notifications, you need to map ChoreControl users to Home Assistant notify services.

### Step 1: Identify Your Users

From the ChoreControl addon, go to **Users → User Mapping** and note each user's:
- **Username** (display name)
- **HA User ID** (unique identifier)

### Step 2: Map to Notify Services

Create a mapping in your `configuration.yaml` or use input_text helpers:

```yaml
# configuration.yaml
homeassistant:
  customize:
    automation.chorecontrol_notifications:
      chorecontrol_user_mapping:
        # Map ChoreControl usernames to HA notify services
        "Alice": "notify.mobile_app_alice_phone"
        "Bob": "notify.mobile_app_bob_phone"
        "Parent": "notify.mobile_app_parent_phone"
```

Or use template helpers in your automations (shown in examples below).

## Example Automations

### Basic: Notify Parent When Chore Claimed

```yaml
alias: "ChoreControl: Notify Parent of Claimed Chores"
description: "Send notification to parent when any kid claims a chore"
trigger:
  - platform: event
    event_type: chorecontrol_chore_claimed
action:
  - service: notify.mobile_app_parent_phone
    data:
      message: "{{ trigger.event.data.kid_name }} claimed: {{ trigger.event.data.chore_name }}"
      title: "Chore Claimed"
      data:
        actions:
          - action: "APPROVE_CHORE"
            title: "Approve"
          - action: "VIEW_CHORE"
            title: "View"
        tag: "chore_{{ trigger.event.data.instance_id }}"
```

### Advanced: Notify Kid When Chore Approved

This example shows how to map kids to their notify services:

```yaml
alias: "ChoreControl: Notify Kid of Approved Chore"
description: "Send notification to kid when their chore is approved"
trigger:
  - platform: event
    event_type: chorecontrol_chore_approved
variables:
  # Map kid usernames to notify services
  kid_notify_services:
    Alice: notify.mobile_app_alice_phone
    Bob: notify.mobile_app_bob_phone
    Charlie: notify.mobile_app_charlie_tablet

  kid_name: "{{ trigger.event.data.kid_name }}"
  notify_service: "{{ kid_notify_services.get(kid_name, 'notify.persistent_notification') }}"

action:
  - service: "{{ notify_service }}"
    data:
      message: >
        Great job! You earned {{ trigger.event.data.points_awarded }} points
        for completing "{{ trigger.event.data.chore_name }}".
      title: "✅ Chore Approved!"
      data:
        image: "/local/chore_approved.png"
        tag: "chore_{{ trigger.event.data.instance_id }}"
```

### Notify Kid When Chore Rejected

```yaml
alias: "ChoreControl: Notify Kid of Rejected Chore"
description: "Send notification when chore is rejected with reason"
trigger:
  - platform: event
    event_type: chorecontrol_chore_rejected
variables:
  kid_notify_services:
    Alice: notify.mobile_app_alice_phone
    Bob: notify.mobile_app_bob_phone
    Charlie: notify.mobile_app_charlie_tablet

  kid_name: "{{ trigger.event.data.kid_name }}"
  notify_service: "{{ kid_notify_services.get(kid_name, 'notify.persistent_notification') }}"

action:
  - service: "{{ notify_service }}"
    data:
      message: >
        Your chore "{{ trigger.event.data.chore_name }}" needs to be redone.
        Reason: {{ trigger.event.data.rejection_reason }}
      title: "Chore Needs Work"
      data:
        actions:
          - action: "RECLAIM_CHORE"
            title: "Try Again"
        tag: "chore_{{ trigger.event.data.instance_id }}"
```

### Notify Kid of New Assigned Chore

```yaml
alias: "ChoreControl: Notify Kid of New Chore"
description: "Notify kid when a new chore is assigned to them"
trigger:
  - platform: event
    event_type: chorecontrol_chore_assigned
condition:
  # Only notify if due date is set (optional)
  - condition: template
    value_template: "{{ trigger.event.data.due_date is not none }}"
variables:
  kid_notify_services:
    Alice: notify.mobile_app_alice_phone
    Bob: notify.mobile_app_bob_phone

  assignee_name: "{{ trigger.event.data.assignee_name }}"
  notify_service: "{{ kid_notify_services.get(assignee_name, 'notify.persistent_notification') }}"

action:
  - service: "{{ notify_service }}"
    data:
      message: >
        New chore assigned: {{ trigger.event.data.chore_name }}.
        Due: {{ trigger.event.data.due_date | as_datetime | as_local | strftime('%b %d at %I:%M %p') }}
      title: "New Chore!"
      data:
        actions:
          - action: "CLAIM_CHORE"
            title: "Claim Now"
```

### Notify Parent When Reward Claimed

```yaml
alias: "ChoreControl: Notify Parent of Reward Claims"
description: "Alert parent when kid claims a reward for approval"
trigger:
  - platform: event
    event_type: chorecontrol_reward_claimed
action:
  - service: notify.mobile_app_parent_phone
    data:
      message: >
        {{ trigger.event.data.kid_name }} wants to claim:
        {{ trigger.event.data.reward_name }}
        ({{ trigger.event.data.points_cost }} points)
      title: "Reward Claim"
      data:
        actions:
          - action: "APPROVE_REWARD"
            title: "Approve"
          - action: "REJECT_REWARD"
            title: "Reject"
        tag: "reward_{{ trigger.event.data.claim_id }}"
```

### Daily Digest: Pending Approvals

```yaml
alias: "ChoreControl: Daily Pending Approvals Digest"
description: "Send parent a daily summary of pending items"
trigger:
  - platform: time
    at: "20:00:00"
condition:
  - condition: or
    conditions:
      - condition: numeric_state
        entity_id: sensor.chorecontrol_pending_approvals
        above: 0
      - condition: numeric_state
        entity_id: sensor.chorecontrol_pending_rewards
        above: 0
action:
  - service: notify.mobile_app_parent_phone
    data:
      message: >
        You have {{ states('sensor.chorecontrol_pending_approvals') }} chores
        and {{ states('sensor.chorecontrol_pending_rewards') }} rewards pending approval.
      title: "ChoreControl Daily Digest"
      data:
        actions:
          - action: "OPEN_APPROVALS"
            title: "Review"
```

### Reminder: Chore Due Soon

```yaml
alias: "ChoreControl: Remind Kid of Due Chores"
description: "Send reminder 1 hour before chore is due"
trigger:
  - platform: time_pattern
    minutes: "0"  # Check every hour
variables:
  kid_notify_services:
    Alice: notify.mobile_app_alice_phone
    Bob: notify.mobile_app_bob_phone

action:
  # This is a simplified example - you'd iterate through assigned instances
  # In practice, you might create separate automations per kid or use more complex logic
  - service: notify.mobile_app_alice_phone
    data:
      message: "Reminder: Your chore is due in 1 hour!"
      title: "Chore Reminder"
```

## Advanced Patterns

### Conditional Notifications Based on Points

Only notify if high-value chores are completed:

```yaml
trigger:
  - platform: event
    event_type: chorecontrol_chore_approved
condition:
  - condition: template
    value_template: "{{ trigger.event.data.points_awarded >= 10 }}"
action:
  # Send special notification for high-value chores
  - service: notify.family_group
    data:
      message: >
        🎉 {{ trigger.event.data.kid_name }} earned {{ trigger.event.data.points_awarded }}
        points for {{ trigger.event.data.chore_name }}!
      title: "Big Achievement!"
```

### Quiet Hours

Don't send notifications during bedtime:

```yaml
trigger:
  - platform: event
    event_type: chorecontrol_chore_claimed
condition:
  - condition: time
    after: "07:00:00"
    before: "21:00:00"
action:
  - service: notify.mobile_app_parent_phone
    data:
      message: "{{ trigger.event.data.kid_name }} claimed a chore"
```

### Group Notifications

Notify all parents or all kids:

```yaml
# Notify all parents when any reward is claimed
trigger:
  - platform: event
    event_type: chorecontrol_reward_claimed
action:
  - service: notify.parents_group
    data:
      message: "Reward claim pending approval"
```

## Actionable Notifications

Make notifications interactive with actions:

```yaml
alias: "ChoreControl: Actionable Chore Claim Notification"
trigger:
  - platform: event
    event_type: chorecontrol_chore_claimed
action:
  - service: notify.mobile_app_parent_phone
    data:
      message: "{{ trigger.event.data.kid_name }} claimed: {{ trigger.event.data.chore_name }}"
      title: "Chore Claimed"
      data:
        actions:
          - action: "APPROVE_CHORE_{{ trigger.event.data.instance_id }}"
            title: "✅ Approve"
          - action: "REJECT_CHORE_{{ trigger.event.data.instance_id }}"
            title: "❌ Reject"
        tag: "chore_{{ trigger.event.data.instance_id }}"

# Handle the action
- alias: "ChoreControl: Handle Approve Action"
  trigger:
    - platform: event
      event_type: mobile_app_notification_action
      event_data:
        action: "APPROVE_CHORE_*"  # Wildcard match
  action:
    - service: chorecontrol.approve_chore
      data:
        instance_id: "{{ trigger.event.data.action.split('_')[-1] }}"
```

## Event Data Reference

### chorecontrol_chore_claimed

```yaml
event_data:
  instance_id: 123
  chore_id: 45
  chore_name: "Take out trash"
  kid_id: 2
  kid_name: "Alice"
  claimed_at: "2025-11-29T10:30:00"
```

### chorecontrol_chore_approved

```yaml
event_data:
  instance_id: 123
  chore_id: 45
  chore_name: "Take out trash"
  kid_id: 2
  kid_name: "Alice"
  points_awarded: 5
  approver_id: 1
  approver_name: "Parent"
  approved_at: "2025-11-29T11:00:00"
```

### chorecontrol_chore_rejected

```yaml
event_data:
  instance_id: 123
  chore_id: 45
  chore_name: "Take out trash"
  kid_id: 2
  kid_name: "Alice"
  rejection_reason: "Trash not fully taken out"
  rejecter_id: 1
  rejecter_name: "Parent"
  rejected_at: "2025-11-29T11:00:00"
```

### chorecontrol_reward_claimed

```yaml
event_data:
  claim_id: 78
  reward_id: 12
  reward_name: "30 minutes screen time"
  kid_id: 2
  kid_name: "Alice"
  points_cost: 25
  claimed_at: "2025-11-29T15:00:00"
```

### chorecontrol_reward_approved

```yaml
event_data:
  claim_id: 78
  reward_id: 12
  reward_name: "30 minutes screen time"
  kid_id: 2
  kid_name: "Alice"
  approver_id: 1
  approver_name: "Parent"
  approved_at: "2025-11-29T15:30:00"
```

### chorecontrol_chore_assigned

```yaml
event_data:
  instance_id: 124
  chore_id: 46
  chore_name: "Clean room"
  assignee_id: 2
  assignee_name: "Alice"
  due_date: "2025-11-30T18:00:00"  # null if no due date
  created_at: "2025-11-29T08:00:00"
```

### chorecontrol_chore_missed

```yaml
event_data:
  instance_id: 124
  chore_id: 46
  chore_name: "Clean room"
  assignee_id: 2
  assignee_name: "Alice"
  due_date: "2025-11-30T18:00:00"
  missed_at: "2025-11-30T18:01:00"
```

## Testing Notifications

### Manual Event Firing

Test your automations by manually firing events:

```yaml
# In Home Assistant Developer Tools → Events
Event Type: chorecontrol_chore_claimed

Event Data:
instance_id: 999
chore_id: 1
chore_name: "Test Chore"
kid_id: 2
kid_name: "Alice"
claimed_at: "2025-11-29T10:00:00"
```

### Debugging

Enable automation debugging:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    homeassistant.components.automation: debug
```

Check automation traces in **Settings → Automations & Scenes → [Your Automation] → Traces**.

## Best Practices

1. **Use Variables**: Define user mappings as variables for easy updates
2. **Tag Notifications**: Use unique tags to replace old notifications
3. **Test Thoroughly**: Fire test events before going live
4. **Respect Quiet Hours**: Don't spam notifications at night
5. **Group Similar Notifications**: Use notification groups for families
6. **Make Actions Clear**: Use descriptive action titles
7. **Handle Edge Cases**: What if notify service doesn't exist? Use fallbacks
8. **Document Your Mappings**: Keep a list of who maps to which service

## Troubleshooting

**Problem**: Notifications not sending

**Solutions**:
- Check automation is enabled
- Verify event is firing (Developer Tools → Events → Listen to `chorecontrol_*`)
- Check notify service exists (`notify.mobile_app_*`)
- Review automation traces for errors

**Problem**: Wrong user gets notification

**Solutions**:
- Verify user mapping in automation variables
- Check ChoreControl user names match exactly (case-sensitive)
- Review event data to ensure correct kid_name

**Problem**: Duplicate notifications

**Solutions**:
- Use notification `tag` to replace old notifications
- Check multiple automations aren't listening to same event

## Future Enhancements

Planned improvements:
- Built-in notification service mapping in addon
- Pre-built notification blueprints
- Rich notification templates with images
- Parent/kid notification preferences in UI

---

**See Also**:
- [Entity Reference](entity-reference.md) - ChoreControl sensors
- [API Reference](api-reference.md) - Service calls for actions
- [User Management](USER_MANAGEMENT.md) - User role mapping
