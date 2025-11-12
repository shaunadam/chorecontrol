# ChoreControl Development Guide

This guide will help you set up a development environment and contribute to ChoreControl.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Setup](#development-setup)
3. [Project Structure](#project-structure)
4. [Running Locally](#running-locally)
5. [Testing](#testing)
6. [Code Style](#code-style)
7. [Contributing](#contributing)
8. [Release Process](#release-process)

## Prerequisites

- **Python 3.11 or higher**
- **Git**
- **Home Assistant** (for testing integration)
- **SQLite 3**
- **Basic knowledge of**:
  - Flask web framework
  - SQLAlchemy ORM
  - Home Assistant custom components

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/shaunadam/chorecontrol.git
cd chorecontrol
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install all dependencies including dev tools
pip install -e ".[dev]"

# Or just the core dependencies
pip install -r addon/requirements.txt

# Install pre-commit hooks
pre-commit install
```

> **TODO**: Create addon/requirements.txt when add-on is implemented

### 4. Set Up Database

```bash
# Navigate to add-on directory
cd addon

# Initialize database
flask db init

# Run migrations
flask db upgrade

# (Optional) Load seed data
python seed.py
```

> **TODO**: Complete when Flask app and migrations are ready

### 5. Configure Environment

Create a `.env` file in the `addon/` directory:

```bash
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=sqlite:///chorecontrol.db
SECRET_KEY=dev-secret-key-change-in-production
LOG_LEVEL=DEBUG
```

> **TODO**: Update with actual configuration variables

## Project Structure

```
chorecontrol/
├── addon/                      # Flask add-on application
│   ├── app.py                  # Main Flask application
│   ├── models.py               # SQLAlchemy models
│   ├── routes/                 # API route handlers
│   │   ├── users.py
│   │   ├── chores.py
│   │   ├── instances.py
│   │   ├── rewards.py
│   │   └── ...
│   ├── services/               # Business logic
│   │   ├── scheduler.py        # Chore scheduling
│   │   ├── points.py           # Points management
│   │   └── notifications.py    # Notification handling
│   ├── templates/              # Jinja2 templates
│   ├── static/                 # CSS, JS, images
│   ├── migrations/             # Alembic migrations
│   ├── requirements.txt        # Python dependencies
│   ├── config.json             # HA add-on config
│   ├── Dockerfile              # Container definition
│   └── run.sh                  # Startup script
│
├── custom_components/          # Home Assistant integration
│   └── chorecontrol/
│       ├── __init__.py         # Integration setup
│       ├── manifest.json       # Integration metadata
│       ├── config_flow.py      # Configuration UI
│       ├── const.py            # Constants
│       ├── coordinator.py      # Data update coordinator
│       ├── sensor.py           # Sensor entities
│       ├── button.py           # Button entities
│       ├── services.yaml       # Service definitions
│       └── api_client.py       # REST API client
│
├── tests/                      # Test suite
│   ├── conftest.py             # Pytest fixtures
│   ├── test_models.py          # Model tests
│   ├── test_api.py             # API tests
│   └── integration/            # Integration tests
│       └── test_e2e.py         # End-to-end tests
│
├── docs/                       # Documentation
│   ├── installation.md
│   ├── user-guide.md
│   ├── api-reference.md
│   ├── development.md          # This file
│   └── architecture.md
│
├── .pre-commit-config.yaml     # Pre-commit hooks
├── pyproject.toml              # Project config and tool settings
├── CONTRIBUTING.md             # Contribution guidelines
├── PROJECT_PLAN.md             # Project planning
├── DECISIONS.md                # Technology decisions
├── NEXT_STEPS.md               # Implementation roadmap
└── README.md                   # Project overview
```

## Running Locally

### Run the Flask Add-on

```bash
cd addon
flask run --debug
```

The API will be available at `http://localhost:5000`

> **TODO**: Complete when Flask app is implemented

### Run with Docker (Optional)

```bash
docker build -t chorecontrol-addon ./addon
docker run -p 5000:5000 -v $(pwd)/data:/data chorecontrol-addon
```

> **TODO**: Complete when Dockerfile is created

### Install Integration in Home Assistant

1. Copy the integration to your HA config:

```bash
cp -r custom_components/chorecontrol /path/to/ha/config/custom_components/
```

2. Restart Home Assistant

3. Add the integration via UI:
   - Settings → Devices & Services → Add Integration
   - Search for "ChoreControl"
   - Configure with your local add-on URL

> **TODO**: Complete when integration is implemented

## Testing

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_models.py

# Run specific test class
pytest tests/test_models.py::TestUserModel

# Run specific test
pytest tests/test_models.py::TestUserModel::test_user_creation
```

### Run Tests by Marker

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only e2e tests
pytest -m e2e

# Skip slow tests
pytest -m "not slow"
```

### Generate Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=addon --cov-report=html

# Open in browser
open htmlcov/index.html  # On Mac
xdg-open htmlcov/index.html  # On Linux
```

### Run Tests in Watch Mode

```bash
# Install pytest-watch
pip install pytest-watch

# Run in watch mode
ptw
```

## Code Style

ChoreControl uses several tools to maintain code quality:

### Linting and Formatting

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific tools
ruff check .                    # Linting
ruff format .                   # Formatting
black .                         # Alternative formatter
mypy addon/                     # Type checking
bandit -r addon/                # Security checks
```

### Code Style Guidelines

1. **Python Version**: Python 3.11+
2. **Line Length**: 100 characters (configured in `pyproject.toml`)
3. **Import Sorting**: Automated by ruff/isort
4. **Type Hints**: Use type hints for function signatures
5. **Docstrings**: Use Google-style docstrings

**Example**:

```python
from typing import List, Optional

def get_user_chores(
    user_id: int,
    status: Optional[str] = None
) -> List[Chore]:
    """
    Get all chores for a specific user.

    Args:
        user_id: The ID of the user
        status: Optional status filter (assigned, claimed, approved, rejected)

    Returns:
        List of Chore objects

    Raises:
        ValueError: If user_id is invalid
    """
    # Implementation here
    pass
```

### Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add reward cooldown enforcement
fix: correct points calculation for approved chores
docs: update API reference with new endpoints
test: add unit tests for User model
refactor: simplify chore scheduling logic
chore: update dependencies
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed contribution guidelines.

### Quick Contribution Workflow

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feat/my-feature`
3. **Make changes** and commit: `git commit -m "feat: add my feature"`
4. **Write tests** for your changes
5. **Run tests**: `pytest`
6. **Run linters**: `pre-commit run --all-files`
7. **Push**: `git push origin feat/my-feature`
8. **Create Pull Request** on GitHub

## Development Tips

### Working with the Database

```bash
# Create a new migration
flask db migrate -m "Add new column to chores table"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade

# Reset database (WARNING: deletes all data)
rm chorecontrol.db
flask db upgrade
python seed.py
```

> **TODO**: Complete when Flask-Migrate is set up

### Debugging

```python
# Use Python debugger
import pdb; pdb.set_trace()

# Or use breakpoint (Python 3.7+)
breakpoint()

# Flask debugging
app.logger.debug("Debug message")
app.logger.info("Info message")
app.logger.error("Error message")
```

### Testing HA Integration Locally

1. Set up a development Home Assistant instance
2. Point integration to your local add-on
3. Use HA logs to debug: `Settings → System → Logs`
4. Check integration logs: `homeassistant.components.chorecontrol`

### Performance Profiling

```python
# Profile a specific function
from werkzeug.middleware.profiler import ProfilerMiddleware

app.wsgi_app = ProfilerMiddleware(app.wsgi_app)
```

## Common Development Tasks

### Add a New API Endpoint

1. Define route in `addon/routes/`
2. Add business logic in `addon/services/`
3. Update models if needed
4. Write tests in `tests/test_api.py`
5. Update API documentation in `docs/api-reference.md`

### Add a New Database Model

1. Define model in `addon/models.py`
2. Create migration: `flask db migrate -m "Add new model"`
3. Apply migration: `flask db upgrade`
4. Write tests in `tests/test_models.py`
5. Update seed data if needed

### Add a New Integration Entity

1. Create entity class in `custom_components/chorecontrol/`
2. Register in `__init__.py` or platform file
3. Update `manifest.json` if new dependencies
4. Test in Home Assistant

## Troubleshooting

### Pre-commit hooks failing

```bash
# Update hooks
pre-commit autoupdate

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

### Import errors in tests

```bash
# Install package in editable mode
pip install -e .
```

### Database locked error

```bash
# SQLite doesn't handle concurrent writes well
# Make sure you're not running multiple Flask instances
```

## Resources

- **Flask Documentation**: [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)
- **SQLAlchemy Documentation**: [https://docs.sqlalchemy.org/](https://docs.sqlalchemy.org/)
- **Home Assistant Developer Docs**: [https://developers.home-assistant.io/](https://developers.home-assistant.io/)
- **pytest Documentation**: [https://docs.pytest.org/](https://docs.pytest.org/)
- **Project Planning**: See [PROJECT_PLAN.md](../PROJECT_PLAN.md)
- **Technology Decisions**: See [DECISIONS.md](../DECISIONS.md)

## Getting Help

- **Issues**: [Report bugs or request features](https://github.com/shaunadam/chorecontrol/issues)
- **Discussions**: [Ask questions](https://github.com/shaunadam/chorecontrol/discussions)
- **Discord**: [Join our community](#) (TODO: Add Discord link if created)

## Release Process

> **TODO**: Document release process when established

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag -a v0.1.0 -m "Release v0.1.0"`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions builds and publishes (TODO: Set up CI/CD)

---

**Ready to contribute? Check out [NEXT_STEPS.md](../NEXT_STEPS.md) for current development priorities!**
