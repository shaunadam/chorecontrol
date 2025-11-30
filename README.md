# ChoreControl

A comprehensive chore management system for Home Assistant that helps families track chores, manage points, and reward kids for completing tasks.

## Features

### Chore Management
- **Flexible Scheduling**: Create one-off or recurring chores (daily, weekly, monthly)
- **Assignment Options**: Assign chores to individual kids or make them shared (first-come, first-served)
- **Late Claim Support**: Optionally allow late completion with reduced points
- **Auto-Approval**: Configure chores to auto-approve after a set time

### Points & Rewards
- **Points System**: Kids earn points for completing chores
- **Reward Marketplace**: Create rewards kids can claim with their points
- **Approval Workflow**: Optional parent approval for high-value rewards
- **Cooldowns & Limits**: Set cooldown periods and claim limits on rewards
- **Points Auditing**: Automatic nightly verification of point balances

### Approval Workflow
- **Claim → Approve Flow**: Kids claim chores, parents approve
- **Rejection with Feedback**: Provide reasons when rejecting claims
- **Mobile Notifications**: Get notified when kids claim chores

### Home Assistant Integration
- **Native Entities**: Sensors for points, chore counts, and pending approvals
- **Dynamic Buttons**: Claim buttons appear automatically for available chores
- **Services**: Full API access through HA services for automations
- **Real-time Events**: Webhook integration for instant updates

### Web Interface
- **Mobile-First Design**: Manage everything from your phone via HA sidebar
- **Dashboard**: View pending approvals, kid stats, and recent activity
- **Calendar View**: See all scheduled chores at a glance
- **Points History**: Track all point transactions

## Architecture

ChoreControl consists of two components:

1. **Add-on** (Backend Service)
   - Flask web application with SQLite database
   - REST API (28 endpoints) for all operations
   - Web UI for parent administration
   - Background jobs for automation (auto-approval, instance generation)
   - Accessible via HA sidebar (ingress)

2. **Integration** (Custom Component)
   - Exposes entities (sensors, buttons) to Home Assistant
   - Provides services for automations
   - Handles real-time event notifications via webhooks

## Installation

### Prerequisites
- Home Assistant 2024.1.0 or higher
- Supervisor access (for add-on installation)

### Quick Start

**Note:** ChoreControl is currently in development. HACS integration and add-on repository publishing coming soon.

#### 1. Install the Add-on (Manual)

For now, install as a local add-on:

1. Clone or download this repository
2. Copy the `addon` directory to your HA add-ons folder
3. Restart Home Assistant
4. Install from **Settings** → **Add-ons** → **Local Add-ons**
5. Start the add-on and enable **Start on boot**
6. Access via HA sidebar

#### 2. Install the Integration (Manual)

1. Copy `custom_components/chorecontrol` to your HA config:
   ```bash
   cp -r custom_components/chorecontrol /config/custom_components/
   ```
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration**
4. Search for "ChoreControl"
4. Enter the add-on URL: `http://chorecontrol` (or auto-detected)
5. Configure update interval (default: 30 seconds)

See [docs/installation.md](docs/installation.md) for detailed instructions.

## Quick Start

### 1. First Login

1. Access ChoreControl via the HA sidebar
2. Login with default credentials: `admin` / `admin`
3. **Important:** Change the admin password immediately

### 2. User Management

ChoreControl integrates with Home Assistant users:
- When HA users access the addon, they're auto-created with role='unmapped'
- Parents use the User Mapping page to assign roles (parent/kid)
- Parents get full addon access; kids see their chores via HA dashboards only

See [docs/USER_MANAGEMENT.md](docs/USER_MANAGEMENT.md) (coming soon) for details.

### 3. Set Up Chores

Create chores with:
- Name and description
- Point value
- Recurrence pattern (one-time, daily, weekly, monthly)
- Assignment (specific kids or shared)
- Approval requirements

### 4. Create Rewards

Set up rewards kids can claim:
- Name and description
- Point cost
- Optional cooldown period
- Optional claim limits

### 5. Set Up Dashboards

Use the example dashboard configurations in [docs/examples/](docs/examples/) to create:
- Kid dashboards (view chores, claim completion, see points)
- Parent dashboards (approve chores, adjust points, overview)

## Documentation

- [Installation Guide](docs/installation.md) - Detailed setup instructions
- [User Guide](docs/user-guide.md) - How to use ChoreControl
- [API Reference](docs/api-reference.md) - REST API documentation
- [Entity Reference](docs/entity-reference.md) - HA entity naming and attributes
- [Dashboard Setup](docs/dashboard-setup.md) - Creating HA dashboards
- [Integration Setup](docs/integration-setup.md) - Configuring the HA integration
- [Architecture](docs/architecture.md) - Technical details and design decisions
- [Development Guide](docs/development.md) - Contributing to ChoreControl

## Technology Stack

**Backend**
- Python 3.11+
- Flask with SQLAlchemy ORM
- SQLite database
- APScheduler for background jobs
- Alembic for migrations

**Integration**
- Python custom component
- aiohttp for async API calls
- DataUpdateCoordinator pattern

**Testing**
- pytest with 245+ tests
- Comprehensive coverage of business logic

## Future Enhancements

See [BACKLOG.md](BACKLOG.md) for planned features including:
- Complex scheduling (cron-like patterns)
- Photo proof of completion
- Achievements and gamification
- Analytics and reporting
- ICS calendar integration
- Voice assistant integration

## Comparison to Alternatives

### vs kidschores-ha
ChoreControl improves on existing solutions by:
- Using proper database storage instead of entity-based storage
- Providing a dedicated admin UI via add-on
- Offering more robust scheduling and workflow options
- Better separation of concerns (add-on + integration)

### vs Skylight Chore Chart
- Fully integrated with Home Assistant
- Self-hosted and private
- Extensible via HA automations
- Open source

## Contributing

Contributions welcome! See [docs/development.md](docs/development.md) for setup instructions.

### Development Principles
- Mobile-first design
- HA-native integration
- Proper data modeling
- User-friendly for non-technical parents
- Clean, documented, testable code

## License

MIT License - See LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/shaunadam/chorecontrol/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shaunadam/chorecontrol/discussions)

## Acknowledgments

- Inspired by [kidschores-ha](https://github.com/ad-ha/kidschores-ha)
- UI/UX ideas from [Skylight Chore Chart](https://myskylight.com/lp/chore-chart/)
- Built for the Home Assistant community
