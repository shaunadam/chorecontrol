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

## Current Issue: 404 on Home Assistant Ingress Access

**Status**: Add-on builds and starts successfully, but accessing via Home Assistant shows 404.

**Symptoms**:
- Local access at `localhost:8099` works fine
- Add-on installs and starts in Home Assistant
- Logs show `302` redirects for all requests to `/`
- Browser ends up at 404 after redirect

**Root Cause**: Flask's `url_for()` generates URLs without the Home Assistant ingress path prefix.

When Home Assistant proxies a request from `/api/hassio_ingress/c1f18b53_chorecontrol/` to the app:
1. HA strips the ingress prefix and forwards to `http://addon:8099/`
2. App generates redirect with `url_for('ui.dashboard')` → returns `/`
3. Browser redirects to `/` (not `/api/hassio_ingress/.../`)
4. HA doesn't recognize `/` and returns 404

**Fix Required**: Configure Flask to understand the ingress base path using `SCRIPT_NAME` or middleware.

### Fix: Add Ingress Path Support

Add middleware in `app.py` to handle the `X-Ingress-Path` header from Home Assistant:

```python
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app():
    app = Flask(__name__)

    # ... existing config ...

    # Add reverse proxy support
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    @app.before_request
    def set_ingress_path():
        """Set SCRIPT_NAME from X-Ingress-Path header for correct URL generation."""
        ingress_path = request.headers.get('X-Ingress-Path', '')
        if ingress_path:
            request.environ['SCRIPT_NAME'] = ingress_path
            # Remove trailing slash to avoid double slashes
            if request.environ.get('PATH_INFO', '').startswith(ingress_path):
                request.environ['PATH_INFO'] = request.environ['PATH_INFO'][len(ingress_path):]
```

This makes `url_for()` generate URLs with the correct ingress prefix.

**Also fix**: Hardcoded `/health` link in `templates/base.html:77` - change to `{{ url_for('ui.health') }}` or similar.

---

## Deployment Tasks

### 1. Create Docker Add-on Package ✅

The add-on Docker containerization is complete:

- [x] `Dockerfile` - Alpine-based Python container
- [x] `config.yaml` - Home Assistant add-on configuration
- [x] `run.sh` - Container startup script

### 2. Test Add-on Installation (In Progress)

- [x] Build and test Docker image locally
- [x] Install add-on on Home Assistant instance
- [ ] **Fix ingress path handling** (see above)
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
