# ChoreControl

A comprehensive chore management system for Home Assistant that helps families track chores, manage points, and reward kids for completing tasks.

## Features

- **Flexible Chore Scheduling** - One-off or recurring (daily, weekly, monthly)
- **Points & Rewards** - Kids earn points, claim rewards from a marketplace
- **Approval Workflow** - Kids claim, parents approve (with mobile notifications)
- **Home Assistant Integration** - Sensors, buttons, services, calendar, and events
- **Web Interface** - Mobile-first admin UI via HA sidebar

## Architecture

ChoreControl consists of two components:

1. **Add-on** - Flask backend with SQLite database, REST API, and web UI
2. **Integration** - HA custom component exposing entities, services, and events

## Quick Start

### 1. Install the Add-on

```bash
# Copy to HA add-ons directory
cp -r chorecontrol /usr/share/hassio/addons/local/chorecontrol
```

Then in Home Assistant: **Settings → Add-ons → Local Add-ons → ChoreControl → Install → Start**

### 2. Install the Integration

```bash
# Copy to HA custom_components
cp -r custom_components/chorecontrol /config/custom_components/
```

Restart HA, then: **Settings → Devices & Services → Add Integration → ChoreControl**

### 3. First Login

1. Access ChoreControl via HA sidebar
2. Login: `admin` / `admin` (change immediately!)
3. Map HA users to roles (parent/kid) via **Users → Mapping**

## Documentation

| Document | Purpose |
|----------|---------|
| [User Guide](docs/user-guide.md) | Complete family guide - installation, addon usage, dashboards, notifications |
| [Technical Reference](docs/technical.md) | API reference, database schema, development guide |
| [Backlog](BACKLOG.md) | Planned features and enhancements |
| [Changelog](CHANGELOG.md) | Version history |

## What Gets Created

**Sensors:**
- Global: pending approvals, pending reward approvals, total kids, active chores
- Per-kid: points, pending chores, claimed chores, completed today/week, chores due today, pending reward claims

**Other Entities:**
- Dynamic claim buttons for each claimable chore
- Calendar showing chore schedules
- API connection status binary sensor

**Services:**
- `claim_chore`, `approve_chore`, `reject_chore`
- `claim_reward`, `approve_reward`, `reject_reward`
- `adjust_points`, `refresh_data`

**Events** (for automations):
- `chorecontrol_chore_instance_claimed/approved/rejected`
- `chorecontrol_reward_claimed/approved/rejected`

## Example: Actionable Notification

```yaml
# Notify parent when chore claimed, with quick approve button
automation:
  - alias: "ChoreControl: Chore Claimed"
    trigger:
      - platform: event
        event_type: chorecontrol_chore_instance_claimed
    action:
      - service: notify.mobile_app_parent
        data:
          title: "Chore Claimed"
          message: "{{ trigger.event.data.claimed_by_name }} claimed {{ trigger.event.data.chore_name }}"
          data:
            actions:
              - action: "APPROVE_{{ trigger.event.data.instance_id }}"
                title: "Approve"
```

See [User Guide - Notifications](docs/user-guide.md#notifications) for complete examples.

## Technology Stack

- **Backend**: Python 3.11, Flask, SQLAlchemy, SQLite, APScheduler
- **Integration**: Python custom component, aiohttp, DataUpdateCoordinator
- **Testing**: pytest with 245+ tests

## Contributing

See [Technical Reference - Development](docs/technical.md#development-setup) for setup instructions.

## License

MIT License - See LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/shaunadam/chorecontrol/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shaunadam/chorecontrol/discussions)
