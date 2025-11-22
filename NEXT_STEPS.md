# Next Steps

## Current Status

**Phase**: Step 4 Complete ✅ → Step 5: HA Integration

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
- ✅ **Web UI (Step 4 Complete!)**
  - ✅ Base template with mobile-first navigation and flash messages
  - ✅ Dashboard with stats, pending approvals, kids' points, recent activity
  - ✅ Chores management (list, detail, create/edit forms with pagination)
  - ✅ Rewards management (list, forms, pending claims)
  - ✅ Approval queue for chores and rewards
  - ✅ Users management with points history
  - ✅ Calendar view with FullCalendar integration
  - ✅ Available chores view for claiming
  - ✅ Local auth support with login page
  - ✅ Mobile-responsive CSS with CSS variables
  - ✅ JavaScript for modals and form handling

**Ready to Implement:**
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

## Step 4: Web UI ✅ COMPLETE

Parent-focused web interface accessible via Home Assistant sidebar.

### Implemented Pages:

1. **Dashboard** (`/`) ✅
   - Stats overview (pending approvals, reward claims, today completed, active chores)
   - Pending approval cards with one-click approve/reject
   - Kids' points balances with adjust modal
   - Recent activity feed (approved, rejected, missed)

2. **Chores Management** (`/chores`) ✅
   - List with pagination and filters (active/inactive, assigned to)
   - Create/edit forms with recurrence patterns
   - Detail view with instance history
   - Soft delete support

3. **Rewards Management** (`/rewards`) ✅
   - List with pagination and filters
   - Create/edit forms (points cost, cooldown, limits)
   - Pending claims display
   - Approve/reject workflow

4. **Users Management** (`/users`) ✅
   - List all users with role filter
   - Create/update users with password support
   - Kid detail with stats (completed, points earned, rewards claimed)
   - Points history with pagination

5. **Approval Queue** (`/approvals`) ✅
   - Combined view: pending chore instances + reward claims
   - Quick approve/reject actions with reason modal

6. **Calendar** (`/calendar`) ✅
   - FullCalendar integration
   - Color-coded by status (assigned, claimed, approved, rejected, missed)
   - Instances without due dates shown in table

7. **Available Chores** (`/available`) ✅
   - Claimable instances (status='assigned')
   - Shows eligible kids for each instance
   - Supports shared and individual chores

### Technical Implementation:

**Templates** (in `addon/templates/`):
- ✅ `base.html` - Mobile-first navigation, flash messages, auth display
- ✅ `dashboard.html` - Stats grid, approval cards, points modals
- ✅ `chores/list.html`, `form.html`, `detail.html`
- ✅ `rewards/list.html`, `form.html`
- ✅ `approvals/queue.html`
- ✅ `users/list.html`, `detail.html`
- ✅ `calendar.html`, `available.html`
- ✅ `auth/login.html`

**Static Assets** (in `addon/static/`):
- ✅ `css/style.css` - 500+ lines of mobile-first responsive CSS
- ✅ `js/app.js` - Form handling, modals, JSON API calls

**Routes** (in `addon/routes/ui.py` - 577+ lines):
- All UI routes with pagination, filtering, and POST handlers
- Context processor for current user and pending count
- User create/update endpoints

### Design Achievements:

- ✅ **Mobile-First**: Sticky header, horizontal scroll nav, touch-friendly
- ✅ **Quick Actions**: One-click approve from dashboard
- ✅ **Clear Status**: Color-coded status badges
- ✅ **Modals**: For rejection reasons and points adjustments
- ✅ **Flash Messages**: Success/error feedback

---

## Step 5: Complete HA Integration

Wire up integration to working API:

- Update sensor.py to pull real data from coordinator
- Create dynamic button entities for chore instances
- Test service calls end-to-end
- Implement notification listeners

---



