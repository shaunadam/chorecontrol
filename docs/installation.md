# ChoreControl Installation Guide

Complete installation instructions for ChoreControl in Home Assistant.

## Prerequisites

- Home Assistant OS 2024.1.0 or higher
- Supervisor access (for add-on installation)
- Terminal/SSH access (for manual installation)
- Basic familiarity with Home Assistant configuration

## Installation Overview

ChoreControl requires installing two components:
1. **Add-on** - Backend service with web UI
2. **Integration** - HA entities, sensors, and services

**Note:** HACS support and public repository coming soon. For now, manual installation required.

## Part 1: Install the Add-on

### Option A: Local Add-on (Development)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/shaunadam/chorecontrol.git
   cd chorecontrol
   ```

2. **Copy to HA add-ons directory**:
   ```bash
   # For HA OS / Supervised
   cp -r chorecontrol/addon /usr/share/hassio/addons/local/chorecontrol

   # Or via Samba/SSH, copy to:
   # \\homeassistant\addons\chorecontrol\
   ```

3. **Restart Home Assistant** to detect the new local add-on

4. **Install the add-on**:
   - Go to **Settings** → **Add-ons**
   - Look under "Local Add-ons"
   - Find "ChoreControl"
   - Click **Install**

5. **Start the add-on**:
   - Click **Start**
   - Enable **Start on boot**
   - Enable **Watchdog** (recommended)

6. **Verify installation**:
   - Check add-on logs for "Running on http://0.0.0.0:8099"
   - Click "Open Web UI" or access via HA sidebar

### Option B: Repository Add-on (Coming Soon)

When published to add-on repository:

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click menu (⋮) → **Repositories**
3. Add: `https://github.com/shaunadam/chorecontrol`
4. Find "ChoreControl" and click **Install**

## Part 2: Install the Integration

### Manual Installation

1. **Copy integration files**:
   ```bash
   # Via terminal/SSH
   cd /config
   mkdir -p custom_components
   cp -r /path/to/chorecontrol/custom_components/chorecontrol custom_components/

   # Or via Samba, copy to:
   # \\homeassistant\config\custom_components\chorecontrol\
   ```

2. **Restart Home Assistant**:
   - **Settings** → **System** → **Restart**
   - Wait for restart to complete

3. **Add the integration**:
   - Go to **Settings** → **Devices & Services**
   - Click **+ Add Integration**
   - Search for "ChoreControl"
   - Click to configure

4. **Configure integration**:
   - **Add-on URL**: `http://chorecontrol` (auto-detected for add-on)
   - **Scan Interval**: 30 seconds (recommended)
   - Click **Submit**

5. **Verify integration**:
   - Check **Developer Tools** → **States**
   - Filter for "chorecontrol"
   - Verify `binary_sensor.chorecontrol_api_connected` shows "on"

## First-Time Setup

### Step 1: Initial Login

1. **Access the addon**:
   - Click ChoreControl in HA sidebar
   - Or navigate to add-on and click "Open Web UI"

2. **Login with default credentials**:
   ```
   Username: admin
   Password: admin
   ```

3. **Important**: Change this password immediately via User settings

### Step 2: User Mapping

ChoreControl auto-discovers Home Assistant users:

1. **Have family members access the addon**:
   - Each HA user who accesses gets auto-created
   - Initial role: 'unmapped' (needs assignment)

2. **Map users to roles**:
   - Login as admin/parent
   - Navigate to **Users** → **Mapping**
   - Assign each unmapped user to:
     - **parent** - Full addon access, can approve chores
     - **kid** - Locked out of addon, uses HA dashboards only

3. **Save changes**

See [User Management Guide](USER_MANAGEMENT.md) for detailed information.

### Step 3: Create Chores

1. Navigate to **Chores** section
2. Click **New Chore**
3. Fill in the form:
   - **Name**: e.g., "Take out trash"
   - **Description**: e.g., "Roll bins to curb Monday night"
   - **Points**: e.g., 5
   - **Recurrence**: Daily, Weekly, Monthly, or One-time
   - **Assignment**: Specific kid(s) or shared (first to claim)
   - **Requires Approval**: Yes/No
4. Click **Create**

### Step 4: Create Rewards

1. Navigate to **Rewards** section
2. Click **New Reward**
3. Fill in:
   - **Name**: e.g., "Ice cream trip"
   - **Description**: e.g., "Family trip to ice cream shop"
   - **Points Cost**: e.g., 20
   - **Cooldown**: Optional (days between claims)
   - **Max Claims**: Optional (total or per-kid limits)
4. Click **Create**

### Step 5: Set Up HA Dashboards

Create dashboards for kids to interact with chores:

1. **Copy example dashboards** from [docs/examples/](examples/)
2. **Customize** for your family
3. **Add to HA** via dashboard editor

See [Dashboard Setup Guide](dashboard-setup.md) for examples.

## Verification Checklist

After installation, verify:

- [ ] Add-on starts successfully
- [ ] Web UI accessible via HA sidebar
- [ ] Database migrations applied (check logs)
- [ ] Default admin user created
- [ ] Integration shows in Devices & Services
- [ ] `binary_sensor.chorecontrol_api_connected` is "on"
- [ ] Global sensors appear (pending_approvals, total_kids, etc.)
- [ ] HA users auto-create when accessing addon
- [ ] User mapping interface works
- [ ] Can create chores and rewards
- [ ] Services available in Developer Tools → Services

## Troubleshooting

### Add-on Won't Start

**Check logs**:
```bash
ha addons logs chorecontrol
```

**Common issues**:
- Port 8099 already in use
- Database permissions
- Missing dependencies

**Solutions**:
- Stop conflicting services
- Check `/data` permissions
- Restart add-on

### Integration Not Found

**Symptoms**: Can't find "ChoreControl" in Add Integration

**Solutions**:
- Verify files in `/config/custom_components/chorecontrol/`
- Check `manifest.json` exists
- Clear browser cache
- Restart Home Assistant
- Check logs for errors

### API Connection Failed

**Symptoms**: `binary_sensor.chorecontrol_api_connected` shows "off"

**Solutions**:
- Verify add-on is running
- Check add-on URL in integration config
- Try `http://chorecontrol` or `http://localhost:8099`
- Review add-on logs for errors
- Verify network connectivity

### Users Not Auto-Creating

**Symptoms**: HA users don't appear in ChoreControl

**Solutions**:
- Ensure users actually accessed the addon (not just HA)
- Check add-on logs for auto-create messages
- Verify database connectivity
- Manually create users via Users page

### Can't Login with admin:admin

**Symptoms**: Default credentials rejected

**Possible causes**:
- Password was changed
- Database not initialized
- Admin user not created

**Solutions**:
- Check add-on logs for "Created default admin user"
- Verify database file exists in `/data/`
- Reset database (caution: loses all data)

## Next Steps

- [User Management Guide](USER_MANAGEMENT.md) - Understanding roles and mapping
- [Integration Setup](integration-setup.md) - Advanced integration configuration
- [Dashboard Setup](dashboard-setup.md) - Creating kid and parent dashboards
- [User Guide](user-guide.md) - Daily usage instructions

## Support

For issues and questions:
- GitHub Issues: https://github.com/shaunadam/chorecontrol/issues
- Documentation: See [docs/](.) directory
- Logs: Add-on logs and Home Assistant logs

---

**Last Updated**: 2025-11-29
