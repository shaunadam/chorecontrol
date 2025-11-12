# ChoreControl Installation Guide

This guide will help you install and configure ChoreControl in your Home Assistant instance.

## Prerequisites

- Home Assistant OS, Supervised, or Container installation
- Python 3.11 or higher (for add-on)
- Basic familiarity with Home Assistant configuration

## Installation Methods

### Method 1: HACS (Recommended)

> **TODO**: Complete when HACS repository is set up

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the "+" button
4. Search for "ChoreControl"
5. Click "Install"

### Method 2: Manual Installation

#### Step 1: Install the Add-on

> **TODO**: Complete when add-on is ready for distribution

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the menu (three dots) in the top right
3. Select "Repositories"
4. Add this repository URL: `https://github.com/shaunadam/chorecontrol`
5. Find "ChoreControl" in the list
6. Click "Install"
7. Wait for installation to complete
8. Click "Start"
9. Enable "Start on boot" and "Watchdog"

#### Step 2: Install the Integration

> **TODO**: Complete when integration is ready

1. Copy the `custom_components/chorecontrol` directory to your Home Assistant `config/custom_components/` folder
2. Restart Home Assistant
3. Navigate to **Settings** → **Devices & Services**
4. Click "+ Add Integration"
5. Search for "ChoreControl"
6. Follow the configuration steps

## Initial Configuration

### Add-on Configuration

> **TODO**: Complete when add-on config options are implemented

The add-on can be configured via the Configuration tab in the add-on UI.

Available options:

- **Database Path**: Path to SQLite database (default: `/data/chorecontrol.db`)
- **Log Level**: Logging verbosity (default: `info`)
- **Port**: Internal port for the web UI (default: `5000`)

Example configuration:

```yaml
database_path: /data/chorecontrol.db
log_level: info
port: 5000
```

### Integration Configuration

> **TODO**: Complete when integration config flow is implemented

1. Enter the add-on URL (usually auto-detected)
2. Configure the update interval (default: 30 seconds)
3. Map Home Assistant users to roles (parent or kid)

## First-Time Setup

### 1. Create Users

> **TODO**: Complete when user management is implemented

1. Open the ChoreControl sidebar in Home Assistant
2. Navigate to **Kids** section
3. Click "Add Kid"
4. Map each Home Assistant user to a ChoreControl user
5. Assign roles (parent or kid)

### 2. Create Your First Chore

> **TODO**: Complete when chore management is implemented

1. Navigate to **Chores** section
2. Click "New Chore"
3. Fill in the form:
   - Name: e.g., "Take out trash"
   - Description: e.g., "Roll bins to curb on Monday night"
   - Points: e.g., 5
   - Recurrence: e.g., Weekly on Mondays
   - Assigned to: Select kid(s)
4. Click "Save"

### 3. Create Rewards

> **TODO**: Complete when reward management is implemented

1. Navigate to **Rewards** section
2. Click "New Reward"
3. Fill in the form:
   - Name: e.g., "Ice cream trip"
   - Description: e.g., "Go get ice cream together"
   - Points cost: e.g., 20
   - Optional: Set cooldown period
4. Click "Save"

### 4. Set Up Dashboards

> **TODO**: Complete when dashboard examples are ready

See the [User Guide](user-guide.md) for dashboard configuration examples.

## Troubleshooting

### Add-on won't start

> **TODO**: Add common troubleshooting steps

- Check the add-on logs for errors
- Verify database file permissions
- Ensure no port conflicts

### Integration not discovered

> **TODO**: Add troubleshooting steps

- Restart Home Assistant after copying integration files
- Check Home Assistant logs for errors
- Verify integration files are in correct directory

### Database errors

> **TODO**: Add database troubleshooting

- Check database file permissions
- Verify database migrations have run
- Restore from backup if corrupted

## Upgrading

### Upgrading the Add-on

> **TODO**: Complete when versioning is implemented

1. Go to the add-on page
2. Click "Update" if available
3. Review changelog
4. Click "Update" to confirm
5. Restart the add-on

### Upgrading the Integration

> **TODO**: Complete when versioning is implemented

1. Update the files in `custom_components/chorecontrol/`
2. Restart Home Assistant
3. Check for any breaking changes in the changelog

## Uninstallation

### Removing the Integration

1. Go to **Settings** → **Devices & Services**
2. Find ChoreControl
3. Click the menu (three dots)
4. Select "Delete"

### Removing the Add-on

1. Stop the add-on
2. Click "Uninstall"
3. Confirm deletion

**Note**: Your data will remain in the database file unless you manually delete it.

## Backup and Restore

### Backing Up

> **TODO**: Complete when backup procedures are defined

1. Stop the add-on
2. Copy `/addon/data/chorecontrol.db` to a safe location
3. Restart the add-on

### Restoring

> **TODO**: Complete when backup procedures are defined

1. Stop the add-on
2. Replace `/addon/data/chorecontrol.db` with backup file
3. Restart the add-on

## Next Steps

- Read the [User Guide](user-guide.md) to learn how to use ChoreControl
- Check out the [API Reference](api-reference.md) for integration details
- Join our community for support and feature requests

## Getting Help

- **Documentation**: [https://github.com/shaunadam/chorecontrol/docs](https://github.com/shaunadam/chorecontrol/docs)
- **Issues**: [https://github.com/shaunadam/chorecontrol/issues](https://github.com/shaunadam/chorecontrol/issues)
- **Discussions**: [https://github.com/shaunadam/chorecontrol/discussions](https://github.com/shaunadam/chorecontrol/discussions)
