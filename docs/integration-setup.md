# ChoreControl Home Assistant Integration Setup

This guide covers setting up the ChoreControl Home Assistant integration after the add-on is installed.

## Prerequisites

Before setting up the integration, ensure:

1. ChoreControl add-on is installed and running
2. You can access the ChoreControl web UI
3. You have created at least one parent and one kid user in the add-on

## Installation

### Method 1: Manual Installation

1. Copy the `custom_components/chorecontrol` directory to your Home Assistant `config/custom_components/` folder:

   ```bash
   # Example from command line
   cp -r custom_components/chorecontrol /config/custom_components/
   ```

2. Restart Home Assistant:
   - Go to **Settings** > **System** > **Restart**
   - Or use the command line: `ha core restart`

3. Clear your browser cache to ensure the integration is detected

### Method 2: HACS Installation (When Available)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click **+ Explore & Download Repositories**
4. Search for "ChoreControl"
5. Click **Download**
6. Restart Home Assistant

## Configuration

### Step 1: Add the Integration

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "ChoreControl"
4. Click on it to start configuration

### Step 2: Configure Connection

1. **Add-on URL**: Enter the URL to your ChoreControl add-on
   - Default: `http://chorecontrol` (auto-detected if running as add-on)
   - For Docker: `http://localhost:8099` or your host IP

2. **Scan Interval**: How often to poll for updates (default: 30 seconds)
   - Lower values = more responsive but more API calls
   - Recommended: 30-60 seconds

3. Click **Submit**

### Step 3: Verify Connection

After configuration:

1. Check that `binary_sensor.chorecontrol_api_connected` shows `on`
2. Verify sensors are populated in **Developer Tools** > **States**
3. Check for any errors in the Home Assistant logs

## What Gets Created

After successful setup, the integration creates:

### Sensors

**Global Sensors:**
- `sensor.chorecontrol_pending_approvals` - Number of chores awaiting approval
- `sensor.chorecontrol_total_kids` - Number of registered kids
- `sensor.chorecontrol_active_chores` - Number of active chore definitions

**Per-Kid Sensors** (for each kid in the system):
- `sensor.chorecontrol_{username}_points` - Current point balance
- `sensor.chorecontrol_{username}_pending_chores` - Assigned chores count
- `sensor.chorecontrol_{username}_claimed_chores` - Claimed (awaiting approval) count
- `sensor.chorecontrol_{username}_completed_today` - Completed today
- `sensor.chorecontrol_{username}_completed_this_week` - Completed this week

### Binary Sensors

- `binary_sensor.chorecontrol_api_connected` - API connection status

### Buttons

Dynamic buttons are created for each claimable chore instance:
- `button.chorecontrol_claim_{instance_id}_{user_id}` - Press to claim the chore

Buttons automatically appear and disappear as chores become available or are claimed.

### Services

The integration registers these services for automations:
- `chorecontrol.claim_chore`
- `chorecontrol.approve_chore`
- `chorecontrol.reject_chore`
- `chorecontrol.adjust_points`
- `chorecontrol.claim_reward`
- `chorecontrol.approve_reward`
- `chorecontrol.reject_reward`
- `chorecontrol.refresh_data`

See the [Entity Reference](entity-reference.md) for detailed service documentation.

## Webhook Configuration

The integration registers a webhook to receive real-time events from the add-on.

### Automatic Setup

The webhook URL is automatically generated during setup. You can find it in:

1. Home Assistant logs during integration setup
2. Integration diagnostics (if implemented)

### Manual Configuration

If you need to manually configure the webhook in the add-on:

1. Find the webhook URL:
   - Format: `http://{ha_address}/api/webhook/chorecontrol_events`
   - Example: `http://homeassistant.local:8123/api/webhook/chorecontrol_events`

2. Configure in add-on (if required):
   - Open add-on configuration
   - Set webhook URL

### Webhook Events

The integration receives these events:
- `chore_instance_claimed` - When a kid claims a chore
- `chore_instance_approved` - When a parent approves a chore
- `chore_instance_rejected` - When a parent rejects a chore
- `reward_claimed` - When a kid claims a reward
- `reward_approved` - When a parent approves a reward
- `reward_rejected` - When a parent rejects a reward

## Verifying the Installation

### Check Entity States

1. Go to **Developer Tools** > **States**
2. Filter by `chorecontrol`
3. Verify:
   - Binary sensor shows `on`
   - Sensors show numeric values
   - No errors in state

### Check Services

1. Go to **Developer Tools** > **Services**
2. Search for `chorecontrol`
3. Verify all services appear with descriptions

### Test a Service Call

1. Go to **Developer Tools** > **Services**
2. Select `chorecontrol.refresh_data`
3. Click **Call Service**
4. Check logs for successful refresh

## Setting Up Notifications

The integration sends notifications for various events. To customize:

### Mobile App Notifications

Create automations to send mobile notifications:

```yaml
automation:
  - alias: "Notify parent when chore claimed"
    trigger:
      - platform: event
        event_type: chorecontrol_chore_instance_claimed
    action:
      - service: notify.mobile_app_parent_phone
        data:
          title: "Chore Claimed"
          message: >
            {{ trigger.event.data.username }} claimed
            {{ trigger.event.data.chore_name }}
          data:
            actions:
              - action: "APPROVE"
                title: "Approve"
              - action: "VIEW"
                title: "View"
```

### Actionable Notifications

Handle notification actions:

```yaml
automation:
  - alias: "Handle chore approval action"
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: "APPROVE"
    action:
      - service: chorecontrol.approve_chore
        data:
          chore_instance_id: "{{ trigger.event.data.instance_id }}"
          approver_user_id: 1  # Parent's user ID
```

## Setting Up Dashboards

After the integration is configured, create dashboards to display the data.

See:
- [Dashboard Setup Guide](dashboard-setup.md) - How to set up dashboards
- [Entity Reference](entity-reference.md) - Entity naming and attributes
- [examples/](examples/) - Ready-to-use dashboard configurations

## Options Flow

To change settings after initial configuration:

1. Go to **Settings** > **Devices & Services**
2. Find **ChoreControl**
3. Click **Configure**
4. Update settings:
   - Scan interval
   - Add-on URL (if changed)
5. Click **Submit**

## Troubleshooting

### Integration Not Found

1. Verify files are in `config/custom_components/chorecontrol/`
2. Check that `__init__.py` exists
3. Restart Home Assistant
4. Clear browser cache

### API Connection Failed

1. Check add-on is running
2. Verify URL is correct:
   - Try `http://chorecontrol` (add-on)
   - Try `http://localhost:8099` (Docker)
3. Check network connectivity
4. Review add-on logs for errors

### Sensors Show 0 or Unknown

1. Verify users exist in ChoreControl
2. Check API is returning data:
   ```bash
   curl http://chorecontrol/api/users
   ```
3. Click refresh in Developer Tools
4. Check Home Assistant logs

### Buttons Not Appearing

1. Ensure there are assigned chore instances
2. Check that instances are in "assigned" status
3. Verify user IDs match between sensors and filters
4. Call `chorecontrol.refresh_data` service

### Services Not Working

1. Check logs for error messages
2. Verify required parameters are provided
3. Ensure user IDs exist in the system
4. Check API endpoint responses

### Webhook Events Not Received

1. Verify webhook URL is correct
2. Check add-on is configured to send webhooks
3. Look for webhook events in HA logs
4. Test with manual API call to webhook

## Logs and Debugging

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.chorecontrol: debug
```

Restart Home Assistant to apply.

### View Logs

1. Go to **Settings** > **System** > **Logs**
2. Search for "chorecontrol"
3. Check for errors or warnings

### Common Log Messages

- `Data refreshed successfully` - Normal operation
- `API call failed` - Check add-on connection
- `Webhook received` - Event was processed
- `Service called` - Service was executed

## Uninstalling

### Remove Integration

1. Go to **Settings** > **Devices & Services**
2. Find **ChoreControl**
3. Click the three-dot menu
4. Select **Delete**
5. Confirm deletion

### Remove Files

1. Delete `config/custom_components/chorecontrol/`
2. Restart Home Assistant

### Keep Add-on Data

The add-on data remains intact. You can:
- Reinstall the integration later
- Continue using the web UI
- Keep your chore history

## Next Steps

1. Set up [dashboards](dashboard-setup.md) for kids and parents
2. Create [automations](#setting-up-notifications) for notifications
3. Configure [actionable notifications](#actionable-notifications)
4. Explore the [Entity Reference](entity-reference.md) for advanced usage

## Getting Help

- **Documentation**: See other docs in this folder
- **Issues**: Report bugs on GitHub
- **Logs**: Always include relevant log entries when reporting issues
