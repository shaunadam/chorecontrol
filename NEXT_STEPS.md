# Next Steps

## Current Status

**Phase**: Step 3 Complete ✅ → Step 4: Web UI

**Completed:**
- ✅ Flask app structure with config management (dev/prod/test modes)
- ✅ Database models (7 tables, relationships, validation)
- ✅ Database migrations (2 migrations: initial schema + business logic fields)
- ✅ Flask app running and tested on http://localhost:8099
- ✅ HA integration framework (manifest, config flow, services, sensors)
- ✅ Development tooling (pytest, ruff, black, mypy, pre-commit)
- ✅ Seed data generator with system user support
- ✅ **REST API endpoints (28 endpoints complete!)**
  - ✅ Stream 1: User & Authentication API (5 endpoints)
  - ✅ Stream 2: Chore Management API (6 endpoints)
  - ✅ Stream 3: Instance Workflow API (8 endpoints: claim, approve, reject, unclaim, reassign, due-today)
  - ✅ Stream 4: Rewards & Points API (9 endpoints: rewards CRUD, claim, unclaim, approve/reject, points adjust)
- ✅ **Business Logic Layer (Phases 1-5 Complete!)**
  - ✅ Recurrence pattern parser (daily/weekly/monthly/simple/complex patterns)
  - ✅ Instance generator with lookahead window (2 months)
  - ✅ Late claim detection and tracking (`claimed_late` flag)
  - ✅ Points calculation with late_points support
  - ✅ Reward approval workflow with expiration
  - ✅ Instance reassignment and unclaim features
- ✅ **Background Jobs (5 scheduled jobs via APScheduler)**
  - ✅ Daily instance generation (midnight)
  - ✅ Auto-approval checker (every 5 minutes)
  - ✅ Missed instance marker (hourly)
  - ✅ Reward expiration (daily at 00:01)
  - ✅ Points balance audit (daily at 02:00)
- ✅ **Webhook Integration (all 8 event types)**
  - ✅ chore_instance_created, claimed, approved, rejected
  - ✅ points_awarded, reward_claimed, approved, rejected
- ✅ **Comprehensive test suite (245 tests, 5,325+ lines)**
  - ✅ test_background_jobs.py (878 lines)
  - ✅ test_instances.py (1,441 lines)
  - ✅ test_chores.py (730 lines)
  - ✅ test_rewards.py (646 lines)
  - ✅ test_points.py (472 lines)
  - ✅ test_users.py (608 lines)
  - ✅ test_webhooks.py (359 lines)
- ✅ Authentication middleware (`auth.py` module)

**Ready to Implement:**
- Web UI (Jinja2 templates for parent dashboard)
- Integration with Home Assistant sensors/services
- Docker containerization for HA add-on

---

## Step 1: Get Flask App Running ✅ COMPLETE

### 1. Install Dependencies

```bash
cd /mnt/c/Coding/chorecontrol
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install -r addon/requirements.txt
pip install pytest pytest-flask ruff black mypy pre-commit
```

### 2. Initialize Database

```bash
cd addon
export FLASK_APP=app.py
export FLASK_ENV=development

flask db init
flask db migrate -m "Initial schema"
flask db upgrade

ls -la data/  # Should see chorecontrol.db
```

### 3. Seed Test Data

```bash
python seed.py --reset --verbose
```

Creates: 2 parents, 3 kids, ~15 chores, ~20 instances, 7 rewards

### 4. Start Flask App

```bash
python app.py
# Should start on http://localhost:8099
```

### 5. Test Endpoints

```bash
# In another terminal:
curl http://localhost:8099/health
curl http://localhost:8099/
curl -H "X-Ingress-User: test-parent-1" http://localhost:8099/api/user
```

---

## Step 2: Implement Core API Endpoints ✅ COMPLETE

All REST API endpoints have been implemented across 4 parallel streams:

### Stream 1: User & Authentication API ✅
- ✅ GET /api/users (list all, filterable by role)
- ✅ POST /api/users (create)
- ✅ GET /api/users/{id}
- ✅ PUT /api/users/{id}
- ✅ GET /api/users/{id}/points (balance + history with verification)

### Stream 2: Chore Management API ✅
- ✅ GET /api/chores (list, filter by active/assigned/recurrence)
- ✅ POST /api/chores (create with validation and assignments)
- ✅ GET /api/chores/{id}
- ✅ PUT /api/chores/{id}
- ✅ DELETE /api/chores/{id} (soft delete)
- ✅ GET /api/chores/{id}/instances (paginated instances for a chore)

### Stream 3: Instance Workflow API ✅
- ✅ GET /api/instances (list with filters: status, user, date, chore)
- ✅ GET /api/instances/{id}
- ✅ POST /api/instances/{id}/claim (kid claims completion)
- ✅ POST /api/instances/{id}/approve (parent approves + awards points)
- ✅ POST /api/instances/{id}/reject (parent rejects with reason)

### Stream 4: Rewards & Points API ✅
- ✅ GET /api/rewards (list with filters)
- ✅ POST /api/rewards (create)
- ✅ GET /api/rewards/{id}
- ✅ PUT /api/rewards/{id}
- ✅ DELETE /api/rewards/{id} (soft delete)
- ✅ POST /api/rewards/{id}/claim (claim reward, deduct points)
- ✅ POST /api/points/adjust (manual adjustment, parent only)
- ✅ GET /api/points/history/{user_id} (paginated history)

**Files Created:**
- `addon/auth.py` - Authentication utilities (ha_auth_required decorator)
- `addon/routes/users.py` - User management endpoints
- `addon/routes/chores.py` - Chore CRUD endpoints
- `addon/routes/instances.py` - Instance workflow endpoints
- `addon/routes/rewards.py` - Reward management endpoints
- `addon/routes/points.py` - Points management endpoints
- `addon/tests/test_users.py` - User API tests
- `addon/tests/test_chores.py` - Chore API tests
- `addon/tests/test_instances.py` - Instance workflow tests
- `addon/tests/test_rewards.py` - Reward API tests
- `addon/tests/test_points.py` - Points API tests
- `addon/tests/conftest.py` - Pytest fixtures

---

## Step 3: Business Logic Layer ✅ COMPLETE

All business logic has been fully implemented and tested:

- ✅ Chore scheduler (generate instances from recurrence patterns)
  - See: [addon/utils/recurrence.py](addon/utils/recurrence.py) (248 lines)
  - See: [addon/utils/instance_generator.py](addon/utils/instance_generator.py) (174 lines)
- ✅ Points calculation/awarding on approval
  - See: [addon/models.py](addon/models.py) - `ChoreInstance.award_points()`, `User.adjust_points()`
- ✅ Reward validation (cooldown, limits, balance checks)
  - See: [addon/models.py](addon/models.py) - `Reward.can_claim()`, `RewardClaim` model
- ✅ Background tasks (APScheduler for daily generation)
  - See: [addon/scheduler.py](addon/scheduler.py) (163 lines)
  - See: [addon/jobs/](addon/jobs/) (5 job modules)
- ✅ Event notifications to HA
  - See: [addon/utils/webhooks.py](addon/utils/webhooks.py) (91 lines)

**Test Coverage**: 245 tests across 7 test files verify all business logic works correctly.

---

## Step 4: Web UI

Build a parent-focused web interface accessible via Home Assistant sidebar.

### Core Pages to Implement:

1. **Dashboard** (`/`)
   - Today's pending approvals
   - Recently completed chores
   - Kids' points balances
   - Quick actions

2. **Chores Management** (`/chores`)
   - List all chores (active/inactive filter)
   - Create new chore form
   - Edit existing chore
   - View generated instances

3. **Rewards Management** (`/rewards`)
   - List all rewards
   - Create/edit reward forms
   - View pending reward claims
   - Approve/reject claims

4. **Kids Management** (`/users`)
   - List all users
   - Edit user details
   - View points history
   - Manual points adjustment

5. **Approval Queue** (`/approvals`)
   - Pending chore approvals
   - Pending reward claims
   - Quick approve/reject actions

### Technical Implementation:

**Templates to Create** (in `addon/templates/`):
- `base.html` - Base template with navigation
- `dashboard.html` - Main dashboard
- `chores/list.html` - Chore list view
- `chores/form.html` - Create/edit chore form
- `chores/detail.html` - Single chore with instances
- `rewards/list.html` - Reward list view
- `rewards/form.html` - Create/edit reward form
- `approvals/queue.html` - Pending approvals view
- `users/list.html` - User management
- `users/detail.html` - User profile with points history

**Static Assets** (in `addon/static/`):
- `css/style.css` - Mobile-first responsive styles
- `js/app.js` - Interactive features (HTMX or vanilla JS)

**Routes to Add** (in `addon/routes/ui.py`):
```python
@ui_bp.route('/')
def dashboard():
    # Render dashboard with pending approvals, today's chores, etc.

@ui_bp.route('/chores')
def chores_list():
    # List chores with pagination

@ui_bp.route('/chores/new')
@ui_bp.route('/chores/<int:id>/edit')
def chore_form():
    # Create/edit chore form

@ui_bp.route('/approvals')
def approval_queue():
    # Pending approvals view
```

### Key Files to Reference During UI Development:

**Models & Data**: [addon/models.py](addon/models.py:1-670)
- All models have `to_dict()` methods for easy serialization
- Understand relationships between models
- Use `can_claim()`, `can_approve()` validation methods

**API Routes** (use these as reference for data flow):
- [addon/routes/instances.py](addon/routes/instances.py:1-686) - Instance workflow logic
- [addon/routes/chores.py](addon/routes/chores.py:1-520) - Chore CRUD patterns
- [addon/routes/rewards.py](addon/routes/rewards.py:1-544) - Reward claim flow
- [addon/routes/points.py](addon/routes/points.py:1-184) - Points history patterns

**Forms & Validation**:
- [addon/schemas.py](addon/schemas.py) - Validation helpers
- [addon/utils/recurrence.py](addon/utils/recurrence.py) - Pattern validation

**Config**: [addon/config.py](addon/config.py:1-63)
- Environment-based configuration
- Database and scheduler settings

**App Setup**: [addon/app.py](addon/app.py:1-146)
- See how blueprints are registered
- Middleware setup for HA ingress authentication

### UI Design Principles:

- **Mobile-First**: Parents will primarily use this on phones
- **Quick Actions**: One-click approve/reject from dashboard
- **Clear Status**: Visual indicators for pending/approved/missed
- **Minimal Friction**: Auto-save forms, inline editing where possible
- **HA Native Feel**: Match Home Assistant's design language

### Optional Enhancements:

- HTMX for dynamic updates without full page reloads
- Toast notifications for actions
- Drag-and-drop chore reordering
- Bulk approval actions
- Inline editing of chore instances

---

## Step 5: Complete HA Integration

Wire up integration to working API:

- Update sensor.py to pull real data from coordinator
- Create dynamic button entities for chore instances
- Test service calls end-to-end
- Implement notification listeners

---



