# Implementation Notes & Final Checklist

Critical information before starting parallel development.

---

## 🔀 Git Workflow for Parallel Streams

### Branch Strategy
- **All streams work on the same branch**: `claude/kidschores-ha-review-011CV1aKQricdhqohW9i8bos`
- Each stream commits to this branch as work completes
- Conflicts should be minimal since streams work on different directories

### Alternative (if conflicts are a concern):
- Each stream creates a sub-branch:
  - `claude/.../stream-1-addon-setup`
  - `claude/.../stream-2-database`
  - `claude/.../stream-3-integration`
  - `claude/.../stream-4-docs`
  - `claude/.../stream-5-seed`
- Merge all to main branch when complete

### Commit Messages
Use conventional commits:
- `feat(addon): add Flask application structure`
- `feat(models): implement User and Chore models`
- `feat(integration): add custom component scaffold`
- `docs: add pre-commit configuration`
- `test: add seed data script`

---

## 🏗️ Directory Structure (Final)

After all streams complete, structure should be:

```
chorecontrol/
├── addon/                          # Stream 1 + 2 + 5
│   ├── app.py                      # Flask app (Stream 1)
│   ├── config.py                   # Configuration (Stream 1)
│   ├── models.py                   # SQLAlchemy models (Stream 2)
│   ├── schemas.py                  # JSON schemas (Stream 2)
│   ├── seed.py                     # Seed script (Stream 5)
│   ├── seed_helpers.py             # Seed utilities (Stream 5)
│   ├── requirements.txt            # Python deps (Stream 1)
│   ├── Dockerfile                  # Container (Stream 1)
│   ├── config.json                 # HA metadata (Stream 1)
│   ├── run.sh                      # Startup script (Stream 1)
│   └── README.md                   # Add-on docs (Stream 1)
│
├── custom_components/chorecontrol/ # Stream 3
│   ├── __init__.py
│   ├── manifest.json
│   ├── const.py
│   ├── config_flow.py
│   ├── strings.json
│   ├── services.yaml
│   ├── sensor.py (placeholder)
│   ├── button.py (placeholder)
│   ├── coordinator.py (placeholder)
│   └── api_client.py (placeholder)
│
├── tests/                          # Stream 4
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_api.py
│   └── integration/
│       └── test_e2e.py
│
├── docs/                           # Stream 4
│   ├── installation.md
│   ├── user-guide.md
│   ├── api-reference.md
│   ├── development.md
│   └── architecture.md
│
├── .pre-commit-config.yaml         # Stream 4
├── pyproject.toml                  # Stream 4
├── .gitignore                      # Stream 4
├── CONTRIBUTING.md                 # Stream 4
├── Makefile                        # Stream 4 (optional)
│
├── PROJECT_PLAN.md                 # Already exists
├── DECISIONS.md                    # Already exists
├── BACKLOG.md                      # Already exists
├── NEXT_STEPS.md                   # Already exists
├── STREAM_PROMPTS.md               # Just created
├── IMPLEMENTATION_NOTES.md         # This file
└── README.md                       # Already exists
```

---

## 🔌 API Contract (for parallel development)

Define API endpoints now so integration (Stream 3) can stub them:

### Base URL
- Development: `http://localhost:5000`
- In HA: `http://slug_name` (ingress handles routing)

### Endpoints (Stream 1 should create stubs)

#### Health Check
- `GET /health`
- Returns: `{"status": "ok", "version": "0.1.0"}`

#### Users
- `GET /api/users` - List all users
- `POST /api/users` - Create user (requires: username, role, ha_user_id)
- `GET /api/users/{id}` - Get user details
- `PUT /api/users/{id}` - Update user
- `GET /api/users/{id}/points` - Get points balance and history

#### Chores
- `GET /api/chores` - List chores (query params: active, assigned_to)
- `POST /api/chores` - Create chore
- `GET /api/chores/{id}` - Get chore details
- `PUT /api/chores/{id}` - Update chore
- `DELETE /api/chores/{id}` - Soft delete

#### Chore Instances
- `GET /api/instances` - List instances (query params: status, user_id, date_from, date_to)
- `GET /api/instances/{id}` - Get instance details
- `POST /api/instances/{id}/claim` - Claim completion
- `POST /api/instances/{id}/approve` - Approve instance
- `POST /api/instances/{id}/reject` - Reject instance (requires: reason)

#### Rewards
- `GET /api/rewards` - List rewards
- `POST /api/rewards` - Create reward
- `GET /api/rewards/{id}` - Get reward details
- `PUT /api/rewards/{id}` - Update reward
- `DELETE /api/rewards/{id}` - Soft delete
- `POST /api/rewards/{id}/claim` - Claim reward

#### Points
- `POST /api/points/adjust` - Manual adjustment (requires: user_id, points_delta, reason)

#### Calendar
- `GET /api/calendar/{user_id}.ics` - ICS feed for user's chores

#### Dashboard (aggregated data)
- `GET /api/dashboard/kid/{user_id}` - Kid dashboard data
- `GET /api/dashboard/parent` - Parent dashboard data

### Authentication
- All requests include `X-Ingress-User` header (from HA)
- Extract and validate against User.ha_user_id

---

## 🐳 Docker & Container Details

### Add-on Slug
- **Proposed**: `chorecontrol`
- **Full name**: ChoreControl Chore Management
- **URL in HA**: `http://chorecontrol`

### Port Configuration
- Flask runs on port **5000** inside container
- HA ingress handles external routing (no port exposed)

### Data Persistence
- Database path: `/data/chorecontrol.db`
- `/data` is persisted by HA add-on system
- Migrations directory: `/data/migrations` (if using separate location)

### Environment Variables
```bash
FLASK_APP=app.py
FLASK_ENV=production
DATABASE_URL=sqlite:////data/chorecontrol.db
SECRET_KEY=${SECRET_KEY} # Generated by HA
HA_SUPERVISOR_TOKEN=${SUPERVISOR_TOKEN} # For event bus
```

---

## 🧪 Testing Strategy

### Unit Tests (Stream 4 sets up)
- Test models independently
- Test API endpoints with mock DB
- Test business logic functions

### Integration Tests
- Test API + database together
- Use in-memory SQLite or temp DB
- Test full workflows (claim → approve → points awarded)

### E2E Tests
- Requires both add-on and integration running
- Test from HA service call → API → database → response
- Defer until both components are functional

---

## 🔍 Common Pitfalls & Solutions

### 1. Stream 2 (Models) depends on Stream 1 (Flask app)
**Solution**: Stream 2 can develop models independently. Just import `db` from flask_sqlalchemy directly.

```python
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
```

Later, Stream 1 will initialize it:
```python
from models import db
db.init_app(app)
```

### 2. Database doesn't exist on first run
**Solution**: Stream 1's `run.sh` should:
```bash
if [ ! -f /data/chorecontrol.db ]; then
    flask db upgrade
fi
```

### 3. Migrations conflict between streams
**Solution**: Only Stream 2 creates initial migration. Others should not run `flask db migrate` until integrated.

### 4. HA user ID format unknown
**Solution**: Use format `abc123def456` (32 char hex). Real HA user IDs look like this.

### 5. Integration can't reach add-on
**Solution**: In config_flow, default to `http://chorecontrol` (add-on slug). Allow user to override.

---

## 📝 Environment Setup (For Each Stream)

### Prerequisites
- Python 3.11+
- Git
- Home Assistant OS (for testing integration) - optional for initial streams

### Setup Commands
```bash
# Clone repo
git clone <repo-url>
cd chorecontrol
git checkout claude/kidschores-ha-review-011CV1aKQricdhqohW9i8bos

# Create venv
python3.11 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dev dependencies (after Stream 1 completes)
pip install -r addon/requirements.txt
pip install -r requirements-dev.txt  # If Stream 4 creates this

# Set up pre-commit (after Stream 4 completes)
pre-commit install
```

---

## 🔗 Integration Points Between Streams

### Stream 1 ↔ Stream 2
- Stream 1 creates `app.py` with `db = SQLAlchemy()`
- Stream 2 creates `models.py` that imports `db`
- **Integration**: Import models in app.py: `from models import *`

### Stream 1 ↔ Stream 3
- Stream 1 defines API endpoints (stubs)
- Stream 3 defines integration API client
- **Integration**: Integration points to add-on URL

### Stream 2 ↔ Stream 5
- Stream 2 defines models
- Stream 5 uses models to create seed data
- **Integration**: Stream 5 imports from `models.py`

### Stream 4 ↔ All
- Stream 4 sets up linting/testing
- All other streams should pass linting
- **Integration**: Run `pre-commit run --all-files` after integration

---

## ✅ Post-Integration Checklist

After all streams complete, verify:

- [ ] Flask app runs: `flask run`
- [ ] Database initializes: `flask db upgrade`
- [ ] Seed data loads: `python seed.py`
- [ ] Linting passes: `pre-commit run --all-files`
- [ ] Tests run: `pytest`
- [ ] Docker builds: `docker build -t chorecontrol addon/`
- [ ] Integration loads in HA (copy to custom_components/)
- [ ] Integration config flow works in HA UI
- [ ] Health endpoint returns 200: `curl http://localhost:5000/health`

---

## 🚦 What to Do If You Get Stuck

### Stream 1 Issues
- Flask won't start: Check requirements.txt has all deps
- Database error: Ensure `/data` directory exists
- Ingress not working: Verify config.json format

### Stream 2 Issues
- Foreign key errors: Check relationship definitions
- Migration fails: Ensure Flask-Migrate initialized correctly
- JSON validation fails: Double-check schema format

### Stream 3 Issues
- Integration won't load: Check manifest.json syntax
- Config flow error: Verify async/await usage
- Services not registering: Check services.yaml format

### Stream 4 Issues
- Pre-commit fails: May need to adjust rules for now
- Tests fail: Expected if no code yet, just ensure pytest runs
- Linting errors: Configure pyproject.toml to be less strict initially

### Stream 5 Issues
- Import error: Stream 2 must be complete first
- Database error: Ensure Flask app context is set up
- Seed data invalid: Check model constraints

---

## 📞 Support & Questions

- **For architectural questions**: Read PROJECT_PLAN.md
- **For tech decisions**: Read DECISIONS.md
- **For task details**: Read NEXT_STEPS.md
- **For API questions**: Refer to "API Contract" section above
- **For HA integration help**: https://developers.home-assistant.io/

---

## 🎯 Success Metrics

After parallel work, you should have:

1. **Runnable add-on** (even if API endpoints return stubs)
2. **Complete data model** (all tables, relationships, migrations)
3. **Loadable integration** (even if entities don't populate yet)
4. **Working dev tools** (linting, testing, docs structure)
5. **Seed data** (realistic dataset for development)

**Next step after parallel work**: Implement API endpoints (Week 1 of sequential work)

---

**Last Updated**: 2025-11-11
