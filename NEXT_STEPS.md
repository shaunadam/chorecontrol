# Next Steps

## Current Milestone: First Deployment

**Goal**: Get ChoreControl running on a real Home Assistant instance with the add-on accessible via sidebar and the integration installed via HACS.

---

## Completed Development

The core application is complete and tested:

- **Backend Add-on**: Flask app with 28 REST API endpoints, SQLite database, business logic, 5 background jobs, webhook integration, and full web UI (13 templates, mobile-responsive)
- **HA Integration**: Sensors (global + per-kid), dynamic buttons, 8 services, config flow, coordinator, and webhook handling
- **Test Suite**: 245 tests covering all critical functionality
- **Documentation**: API reference, architecture, entity reference, dashboard examples

---

## Deployment Tasks

### 1. Create Docker Add-on Package

The add-on needs Docker containerization to run in Home Assistant.

**Files to create in `addon/`:**

- [ ] `Dockerfile` - Alpine-based Python container
- [ ] `config.yaml` - Home Assistant add-on configuration
- [ ] `run.sh` - Container startup script

**Key requirements:**
- Base image: `python:3.11-alpine`
- Install requirements from `requirements.txt`
- Configure ingress for sidebar access
- Mount `/data` for database persistence
- Set environment variables (DATABASE_URL, SECRET_KEY, etc.)

### 2. Test Add-on Installation

- [ ] Build and test Docker image locally
- [ ] Install add-on on Home Assistant instance
- [ ] Verify web UI accessible via sidebar
- [ ] Confirm database initializes correctly
- [ ] Test all API endpoints through ingress

### 3. Test Integration Installation

- [ ] Copy `custom_components/chorecontrol/` to HA config
- [ ] Restart Home Assistant
- [ ] Add integration via Settings → Devices & Services
- [ ] Verify sensors, buttons, and services appear
- [ ] Test service calls (claim, approve, reject, etc.)
- [ ] Confirm webhook events are received

### 4. End-to-End Testing

- [ ] Create users (parent, kids) via web UI
- [ ] Create chores with different recurrence patterns
- [ ] Create rewards
- [ ] Test full workflow: assign → claim → approve → points awarded
- [ ] Verify HA sensors update correctly
- [ ] Test claim buttons appear/disappear dynamically
- [ ] Confirm notifications fire for events

---

## Development Environment

### Running the Add-on Locally

```bash
cd addon
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export FLASK_APP=app.py
export FLASK_ENV=development
flask db upgrade
python seed.py --reset --verbose
python app.py
# Server starts on http://localhost:8099
```

### Testing the Integration

Copy the integration to your HA config:
```bash
cp -r custom_components/chorecontrol /path/to/ha/config/custom_components/
```

Restart Home Assistant and add the integration via the UI.

### Running Tests

```bash
cd addon
pytest -v
# Runs 245 tests
```

---

## After First Deployment

Once the add-on and integration are working together:

1. **Dashboard Testing** - Try the example dashboards in `docs/examples/`
2. **Bug Fixes** - Address any issues discovered during real-world use
3. **Enhancements** - Prioritize items from `BACKLOG.md` based on user feedback

---

## Reference

- [Project Plan](PROJECT_PLAN.md) - Architecture and data model
- [API Reference](docs/api-reference.md) - REST API documentation
- [Entity Reference](docs/entity-reference.md) - HA entities and services
- [Development Guide](docs/development.md) - Contributing guide

---

**Last Updated**: 2025-11-22
