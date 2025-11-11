# ChoreControl Add-on

## About

ChoreControl is a Home Assistant add-on that provides a comprehensive chore management system for families. It helps manage kids' chores, track points, handle rewards, and provide approval workflows for parents.

## Features

- **Chore Management**: Create and manage recurring and one-time chores
- **User Roles**: Support for parents (admin) and kids (users)
- **Points System**: Award points for completed chores
- **Rewards**: Kids can claim rewards by spending earned points
- **Approval Workflow**: Parents review and approve completed chores
- **Calendar Integration**: ICS feed for calendar apps
- **Home Assistant Integration**: Full HA integration via custom component
- **Web UI**: Mobile-friendly admin interface accessible via HA sidebar

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the ChoreControl add-on
3. Start the add-on
4. Access ChoreControl from the Home Assistant sidebar

## Configuration

### Options

- `timezone`: Set your timezone (default: UTC)
- `debug`: Enable debug logging (default: false)

Example configuration:

```yaml
timezone: "America/New_York"
debug: false
```

## How to Use

1. **Access the Web UI**: Click on ChoreControl in the Home Assistant sidebar
2. **Set Up Users**: Map your Home Assistant users to parent/kid roles
3. **Create Chores**: Define chores with points, schedules, and assignments
4. **Create Rewards**: Set up rewards kids can claim with their points
5. **Install Integration**: Install the ChoreControl custom component for HA entities and dashboards

## Architecture

This add-on provides:

- **Flask web application** for the admin interface
- **REST API** for integration with Home Assistant
- **SQLite database** for persistent storage
- **APScheduler** for background tasks (chore generation, auto-approval)
- **ICS feed generation** for calendar integration

## Data Storage

All data is stored in `/data/chorecontrol.db` (SQLite database). This directory is persisted across add-on updates and restarts.

## API Endpoints

The add-on exposes a REST API at `http://homeassistant.local:8099/api/`:

- `/health` - Health check endpoint
- `/api/user` - Current user information
- `/api/chores` - Chore management (CRUD)
- `/api/rewards` - Reward management (CRUD)
- `/api/calendar/{user_id}.ics` - Calendar feed

See the [API documentation](https://github.com/shaunadam/chorecontrol) for complete endpoint reference.

## Home Assistant Integration

This add-on is designed to work with the ChoreControl custom integration:

1. Install the ChoreControl add-on (this)
2. Install the ChoreControl custom component in `/config/custom_components/`
3. Configure the integration via HA UI
4. Use the provided entities in your dashboards

## Development

### Local Development

```bash
cd addon
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
export FLASK_ENV=development
export DATA_DIR=./data
flask run
```

### Building the Docker Image

```bash
docker build -t chorecontrol-addon .
docker run -p 8099:8099 -v $(pwd)/data:/data chorecontrol-addon
```

## Support

For issues, feature requests, or contributions, please visit:
https://github.com/shaunadam/chorecontrol

## License

See [LICENSE](../LICENSE) file in the repository root.

## Changelog

### 0.1.0 (Initial Release)

- Flask web application with SQLAlchemy ORM
- Basic project structure and configuration
- Health check and authentication endpoints
- Home Assistant ingress support
- Ready for model and API implementation
