# ChoreControl User Guide

Complete guide for families using ChoreControl with Home Assistant.

## Table of Contents

- [Installation](#installation)
- [User Management](#user-management)
- [Using the Addon](#using-the-addon)
- [Home Assistant Integration](#home-assistant-integration)
- [Dashboards](#dashboards)
- [Notifications](#notifications)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- Home Assistant OS 2024.1.0 or higher
- Supervisor access (for add-on installation)
- Terminal/SSH access (for manual installation)

### Step 1: Install the Add-on

**Local Add-on Installation:**

1. Clone/download this repository
2. Copy the `chorecontrol` directory to your HA add-ons folder:
   ```bash
   cp -r chorecontrol /usr/share/hassio/addons/local/chorecontrol
   ```
3. Restart Home Assistant to detect the new add-on
4. Go to **Settings > Add-ons > Local Add-ons**
5. Find "ChoreControl" and click **Install**
6. Click **Start**, enable **Start on boot** and **Watchdog**
7. Access via HA sidebar or click "Open Web UI"

### Step 2: Install the Integration

1. Copy integration files:
   ```bash
   cp -r custom_components/chorecontrol /config/custom_components/
   ```
2. Restart Home Assistant
3. Go to **Settings > Devices & Services > Add Integration**
4. Search for "ChoreControl"
5. Configure:
   - **Add-on URL**: `http://chorecontrol` (auto-detected)
   - **Scan Interval**: 30 seconds (recommended)

### Step 3: First Login

1. Access ChoreControl via the HA sidebar
2. Login with default credentials: `admin` / `admin`
3. **Important**: Change this password immediately

### Verification Checklist

- [ ] Add-on starts successfully (check logs for "Running on http://0.0.0.0:8099")
- [ ] Web UI accessible via HA sidebar
- [ ] Integration shows in Devices & Services
- [ ] `binary_sensor.chorecontrol_api_connected` is "on"
- [ ] Global sensors appear (pending_approvals, total_kids, etc.)

---

## User Management

### How Authentication Works

ChoreControl integrates with Home Assistant users:

1. **Auto-Discovery**: When HA users access the addon via ingress, they're auto-created
2. **Role Assignment**: New users get role='unmapped' until a parent assigns them
3. **Access Control**: Based on role (parent gets full access, kids use HA dashboards)

### User Roles

| Role | Addon Access | HA Dashboard | Description |
|------|--------------|--------------|-------------|
| **parent** | Full access | Yes | Manage chores, rewards, users; approve actions |
| **kid** | Locked out | Yes | Earn points, claim chores via HA integration |
| **unmapped** | Locked out | No | Needs parent to assign role |
| **claim_only** | Limited | Yes | Can only claim chores, see today view |

### Mapping Users

1. Have family members access the addon once (this creates their accounts)
2. Login as admin/parent
3. Navigate to **Users > Mapping**
4. Assign each unmapped user to parent or kid role
5. Save changes

**Example workflow:**
- Dad accesses addon → Auto-created as 'unmapped'
- Mom accesses addon → Auto-created as 'unmapped'
- Admin logs in, maps Dad → parent, Mom → parent, Kid1 → kid
- Next login: Parents see full interface, kids are redirected to HA dashboard

### Local Admin Account

ChoreControl creates a fallback local admin account:
- Username: `admin`
- Password: `admin`
- **Change this immediately after installation**

---

## Using the Addon

### Creating Chores

1. Navigate to **Chores** section
2. Click **New Chore**
3. Fill in:
   - **Name**: e.g., "Take out trash"
   - **Description**: Additional details
   - **Points**: Reward value (e.g., 5)
   - **Recurrence**: One-time, Daily, Weekly, or Monthly
   - **Assignment**: Specific kid(s) or shared (first to claim)
   - **Requires Approval**: Toggle on/off
   - **Allow Late Claims**: Let kids claim after due date (optional reduced points)
4. Click **Create**

### Recurrence Patterns

- **One-time**: Single occurrence, optionally on specific date
- **Daily**: Every day
- **Weekly**: Specific days (e.g., Monday, Wednesday, Friday)
- **Monthly**: Specific dates (e.g., 1st and 15th)

### Creating Rewards

1. Navigate to **Rewards** section
2. Click **New Reward**
3. Fill in:
   - **Name**: e.g., "Ice cream trip"
   - **Description**: What the reward includes
   - **Points Cost**: e.g., 20
   - **Cooldown Days**: Days before same kid can claim again (optional)
   - **Max Claims**: Total/per-kid limits (optional)
   - **Requires Approval**: Toggle for parent approval
4. Click **Create**

### Approving Chores

1. Navigate to **Approvals** or dashboard
2. See pending chore claims
3. Click **Approve** to award points, or **Reject** with feedback

### Managing Points

- Points are automatically awarded when chores are approved
- Points are automatically deducted when rewards are claimed
- Manual adjustments: **Users > [Kid] > Adjust Points**

---

## Home Assistant Integration

### Entities Created

**Global Sensors:**
- `sensor.chorecontrol_pending_approvals` - Chores awaiting approval
- `sensor.chorecontrol_pending_reward_approvals` - Rewards awaiting approval
- `sensor.chorecontrol_total_kids` - Number of kids
- `sensor.chorecontrol_active_chores` - Active chore count

**Per-Kid Sensors:**
- `sensor.chorecontrol_{username}_points` - Current points
- `sensor.chorecontrol_{username}_pending_chores` - Assigned, not claimed
- `sensor.chorecontrol_{username}_claimed_chores` - Claimed, awaiting approval
- `sensor.chorecontrol_{username}_completed_today` - Approved today
- `sensor.chorecontrol_{username}_completed_this_week` - Approved this week
- `sensor.chorecontrol_{username}_chores_due_today` - Due today (incl. anytime chores)
- `sensor.chorecontrol_{username}_pending_reward_claims` - Pending reward claims

**Dynamic Buttons:**
- `button.chorecontrol_claim_{chore}_{username}` - Claim buttons for each claimable chore

**Calendar:**
- `calendar.chorecontrol_chores` - Calendar showing chore schedules

**Binary Sensors:**
- `binary_sensor.chorecontrol_api_connected` - Connection status

### Services

| Service | Description |
|---------|-------------|
| `chorecontrol.claim_chore` | Claim a chore instance |
| `chorecontrol.approve_chore` | Approve a claimed chore |
| `chorecontrol.reject_chore` | Reject with reason |
| `chorecontrol.claim_reward` | Claim a reward |
| `chorecontrol.approve_reward` | Approve reward claim |
| `chorecontrol.reject_reward` | Reject reward claim |
| `chorecontrol.adjust_points` | Manual point adjustment |
| `chorecontrol.refresh_data` | Force data refresh |

### Events

ChoreControl fires events for automations:

| Event | When |
|-------|------|
| `chorecontrol_chore_instance_claimed` | Kid claims a chore |
| `chorecontrol_chore_instance_approved` | Parent approves |
| `chorecontrol_chore_instance_rejected` | Parent rejects |
| `chorecontrol_reward_claimed` | Kid claims reward |
| `chorecontrol_reward_approved` | Parent approves reward |
| `chorecontrol_reward_rejected` | Parent rejects reward |

---

## Dashboards

### Required Custom Cards (HACS)

- **auto-entities** - Dynamic button display (required)
- **mushroom** - Modern card designs (recommended)

### Finding User IDs

1. Go to **Developer Tools > States**
2. Search for `sensor.chorecontrol_`
3. Click any kid's sensor
4. Check `user_id` in Attributes

### Example: Kid Dashboard

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: "# My Chores"

  - type: entities
    entities:
      - entity: sensor.chorecontrol_emma_points
        name: My Points
      - entity: sensor.chorecontrol_emma_chores_due_today
        name: Chores Due Today
      - entity: sensor.chorecontrol_emma_pending_reward_claims
        name: Pending Rewards

  - type: custom:auto-entities
    card:
      type: entities
      title: "Chores to Claim"
    filter:
      include:
        - entity_id: "button.chorecontrol_claim_*"
          attributes:
            user_id: 3  # Replace with actual user_id
```

### Example: Parent Dashboard

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: "# ChoreControl Overview"

  - type: entities
    entities:
      - entity: sensor.chorecontrol_pending_approvals
        name: Chores to Approve
      - entity: sensor.chorecontrol_pending_reward_approvals
        name: Rewards to Approve

  - type: horizontal-stack
    cards:
      - type: entity
        entity: sensor.chorecontrol_emma_points
        name: Emma
      - type: entity
        entity: sensor.chorecontrol_jack_points
        name: Jack
```

---

## Notifications

### Basic: Notify Parent When Chore Claimed

```yaml
alias: "ChoreControl: Notify Parent of Claimed Chores"
trigger:
  - platform: event
    event_type: chorecontrol_chore_instance_claimed
action:
  - service: notify.mobile_app_parent_phone
    data:
      title: "Chore Claimed"
      message: "{{ trigger.event.data.claimed_by_name }} claimed: {{ trigger.event.data.chore_name }}"
```

### Actionable: Quick Approve from Notification

```yaml
alias: "ChoreControl: Chore Claimed with Actions"
trigger:
  - platform: event
    event_type: chorecontrol_chore_instance_claimed
action:
  - service: notify.mobile_app_parent_phone
    data:
      title: "Chore Claimed"
      message: "{{ trigger.event.data.claimed_by_name }} claimed: {{ trigger.event.data.chore_name }}"
      data:
        actions:
          - action: "APPROVE_CHORE_{{ trigger.event.data.instance_id }}"
            title: "Approve"
          - action: "REJECT_CHORE_{{ trigger.event.data.instance_id }}"
            title: "Reject"
```

```yaml
alias: "ChoreControl: Handle Approve Action"
trigger:
  - platform: event
    event_type: mobile_app_notification_action
condition:
  - condition: template
    value_template: "{{ trigger.event.data.action.startswith('APPROVE_CHORE_') }}"
action:
  - service: chorecontrol.approve_chore
    data:
      chore_instance_id: "{{ trigger.event.data.action.split('_')[-1] | int }}"
      approver_user_id: 1  # Your parent user ID
```

### Notify Kid When Approved

```yaml
alias: "ChoreControl: Notify Kid of Approval"
trigger:
  - platform: event
    event_type: chorecontrol_chore_instance_approved
variables:
  kid_notify_services:
    Emma: notify.mobile_app_emma_phone
    Jack: notify.mobile_app_jack_tablet
  kid_name: "{{ trigger.event.data.claimed_by_name }}"
  notify_service: "{{ kid_notify_services.get(kid_name, 'notify.persistent_notification') }}"
action:
  - service: "{{ notify_service }}"
    data:
      title: "Chore Approved!"
      message: "Great job! You earned {{ trigger.event.data.points_awarded }} points for {{ trigger.event.data.chore_name }}"
```

### Reward Claim with Actions

```yaml
alias: "ChoreControl: Reward Claimed with Actions"
trigger:
  - platform: event
    event_type: chorecontrol_reward_claimed
action:
  - service: notify.mobile_app_parent_phone
    data:
      title: "Reward Claim"
      message: "{{ trigger.event.data.user_name }} wants: {{ trigger.event.data.reward_name }} ({{ trigger.event.data.points_spent }} points)"
      data:
        actions:
          - action: "APPROVE_REWARD_{{ trigger.event.data.claim_id }}"
            title: "Approve"
          - action: "REJECT_REWARD_{{ trigger.event.data.claim_id }}"
            title: "Reject"
```

```yaml
alias: "ChoreControl: Handle Reward Approve Action"
trigger:
  - platform: event
    event_type: mobile_app_notification_action
condition:
  - condition: template
    value_template: "{{ trigger.event.data.action.startswith('APPROVE_REWARD_') }}"
action:
  - service: chorecontrol.approve_reward
    data:
      claim_id: "{{ trigger.event.data.action.split('_')[-1] | int }}"
      approver_user_id: 1
```

---

## Troubleshooting

### Add-on Won't Start

**Check logs:**
```bash
ha addons logs chorecontrol
```

**Common issues:**
- Port 8099 already in use
- Database permissions in `/data`
- Missing dependencies

### Integration Not Found

- Verify files in `/config/custom_components/chorecontrol/`
- Check `manifest.json` exists
- Clear browser cache
- Restart Home Assistant

### API Connection Failed

`binary_sensor.chorecontrol_api_connected` shows "off":
- Verify add-on is running
- Try URL: `http://chorecontrol` or `http://localhost:8099`
- Check add-on logs

### Users Not Auto-Creating

- Users must access the addon (not just HA)
- Check add-on logs for auto-create messages
- Manually create users via Users page

### Can't Login

Default credentials rejected:
- Password may have been changed
- Check add-on logs for "Created default admin user"
- Verify database exists in `/data/`

### Notifications Not Working

- Check automation is enabled
- Verify event fires (Developer Tools > Events > Listen to `chorecontrol_*`)
- Check notify service exists (`notify.mobile_app_*`)
- Review automation traces

---

## Support

- **Issues**: [GitHub Issues](https://github.com/shaunadam/chorecontrol/issues)
- **Documentation**: See [Technical Reference](technical.md) for API and development details
