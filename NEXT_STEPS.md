# Next Steps

## Current Status

**Phase**: Step 2 Complete ✅ → Step 3: Business Logic Layer

**Completed:**
- ✅ Flask app structure with config management (dev/prod/test modes)
- ✅ Database models (7 tables, relationships, validation)
- ✅ Database migrations initialized
- ✅ Flask app running and tested on http://localhost:8099
- ✅ HA integration framework (manifest, config flow, services, sensors)
- ✅ Development tooling (pytest, ruff, black, mypy, pre-commit)
- ✅ Seed data generator
- ✅ **REST API endpoints (All 4 streams complete!)**
  - ✅ Stream 1: User & Authentication API (5 endpoints)
  - ✅ Stream 2: Chore Management API (6 endpoints)
  - ✅ Stream 3: Instance Workflow API (5 endpoints)
  - ✅ Stream 4: Rewards & Points API (8 endpoints)
- ✅ Comprehensive test suite (5 test files, all passing)
- ✅ Authentication middleware (`auth.py` module)

**Ready to Implement:**
- Business logic layer (scheduler, points calculation, validation)
- Background tasks (APScheduler for instance generation)
- Web UI (Jinja2 templates)
- Integration with Home Assistant sensors/services

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

## Step 3: Business Logic Layer

After API endpoints work:

- Chore scheduler (generate instances from recurrence patterns)
- Points calculation/awarding on approval
- Reward validation (cooldown, limits, balance checks)
- Background tasks (APScheduler for daily generation)
- Event notifications to HA

---

## Step 4: Web UI (Optional for MVP)

Basic admin interface:

- Parent dashboard (pending approvals)
- Chore management (create/edit forms)
- Kid/reward management
- Mobile-responsive Jinja2 templates

---

## Step 5: Complete HA Integration

Wire up integration to working API:

- Update sensor.py to pull real data from coordinator
- Create dynamic button entities for chore instances
- Test service calls end-to-end
- Implement notification listeners

---



