# Next Steps - Implementation Roadmap

All technology decisions are complete! Ready to begin coding.

---

## Immediate Next Steps (Can Run in Parallel)

These tasks are **independent** and can be worked on concurrently by multiple sessions:

### 🔧 Stream 1: Add-on Project Setup
**Goal**: Set up the Flask add-on project structure

**Tasks**:
- [ ] Create `addon/` directory structure
- [ ] Create `addon/requirements.txt` with dependencies
- [ ] Create `addon/Dockerfile` for HA add-on
- [ ] Create `addon/config.json` (HA add-on metadata)
- [ ] Create `addon/run.sh` (startup script)
- [ ] Set up basic Flask app skeleton (`addon/app.py`)
- [ ] Configure Flask-SQLAlchemy connection
- [ ] Set up development virtual environment

**Dependencies to include**:
```
Flask>=2.3.0
Flask-SQLAlchemy>=3.0.0
Flask-Migrate>=4.0.0
APScheduler>=3.10.0
ics>=0.7
jsonschema>=4.17.0
requests>=2.31.0
```

**Why parallel-safe**: No dependencies on other work

---

### 📊 Stream 2: Database Schema & Models
**Goal**: Design and implement the database layer

**Tasks**:
- [ ] Create `addon/models.py` with SQLAlchemy models
- [ ] Define User model (ha_user_id, username, role, points)
- [ ] Define Chore model (with recurrence_pattern JSON)
- [ ] Define ChoreAssignment model
- [ ] Define ChoreInstance model (status workflow)
- [ ] Define Reward model (cooldown, limits)
- [ ] Define RewardClaim model
- [ ] Define PointsHistory model
- [ ] Add model relationships (foreign keys, backrefs)
- [ ] Create JSON schema for recurrence patterns
- [ ] Write helper functions for recurrence parsing
- [ ] Initialize Flask-Migrate and create initial migration

**Reference**: PROJECT_PLAN.md data model section

**Why parallel-safe**: Models are self-contained, don't depend on API or UI

---

### 🏠 Stream 3: Integration Project Setup
**Goal**: Set up the Home Assistant custom integration structure

**Tasks**:
- [ ] Create `custom_components/chorecontrol/` directory structure
- [ ] Create `manifest.json` with metadata and dependencies
- [ ] Create `__init__.py` with integration setup
- [ ] Create `const.py` with constants (domain, default scan interval, etc.)
- [ ] Create `config_flow.py` skeleton (UI configuration)
- [ ] Create `strings.json` for translations
- [ ] Set up integration development environment
- [ ] Create `hacs.json` for HACS compatibility (future)

**Why parallel-safe**: Integration structure is independent of add-on implementation

---

### 📝 Stream 4: Documentation & Tooling
**Goal**: Set up documentation and development tools

**Tasks**:
- [ ] Create `docs/` directory structure
- [ ] Set up `.pre-commit-config.yaml` with ruff, black, mypy
- [ ] Create `pyproject.toml` for tool configuration
- [ ] Set up pytest structure (`tests/` directory)
- [ ] Create API documentation template (OpenAPI/Swagger)
- [ ] Write installation guide skeleton
- [ ] Write user guide skeleton
- [ ] Create contributing guide
- [ ] Set up GitHub Actions workflows (future)

**Why parallel-safe**: Documentation doesn't depend on implementation

---

### 🧪 Stream 5: Test Data & Seed Scripts
**Goal**: Create seed data for development and testing

**Tasks**:
- [ ] Create `addon/seed.py` script
- [ ] Generate sample users (2 parents, 3 kids)
- [ ] Generate sample chores (daily, weekly, one-off)
- [ ] Generate sample rewards
- [ ] Generate sample chore instances (various states)
- [ ] Generate sample points history
- [ ] Make seed script idempotent (can run multiple times)
- [ ] Document how to seed development database

**Why parallel-safe**: Seed data is independent, uses models once they exist

---

## Phase 2: Sequential Work (After Parallel Streams)

These tasks have dependencies and should be done sequentially:

### Week 1: Core Backend
1. **API Endpoints** (depends on Stream 1 & 2)
   - Implement user CRUD endpoints
   - Implement chore CRUD endpoints
   - Implement instance claim/approve/reject endpoints
   - Implement reward endpoints
   - Implement points adjustment endpoint

2. **Business Logic** (depends on models)
   - Chore scheduler (generate instances from patterns)
   - Points calculator
   - Reward claim validator
   - HA event bus integration (notifications)

3. **Web UI - Basic Pages** (depends on Flask setup)
   - Base template with navigation
   - Chores list page
   - Create/edit chore form
   - Kids management page
   - Parent dashboard

### Week 2: Integration & Calendar
4. **Integration Components** (depends on API)
   - REST API client (`api_client.py`)
   - Data update coordinator (`coordinator.py`)
   - Sensor platform (points, counts)
   - Button platform (claim buttons)
   - Services (claim, approve, reject)

5. **Calendar Integration** (depends on API)
   - ICS generation endpoint
   - Calendar caching logic
   - Test with HA calendar

### Week 3: Polish & Testing
6. **Dashboard Examples**
   - Kid dashboard YAML
   - Parent dashboard YAML
   - Documentation

7. **Testing & Bug Fixes**
   - Unit tests
   - Integration tests
   - End-to-end testing
   - Bug fixes

---

## Recommended Parallel Execution Strategy

If you have **5 concurrent sessions** available:

**Session 1**: Stream 1 (Add-on Setup)
**Session 2**: Stream 2 (Database Models)
**Session 3**: Stream 3 (Integration Setup)
**Session 4**: Stream 4 (Docs & Tooling)
**Session 5**: Stream 5 (Seed Data)

**Estimated Time**: 2-4 hours for all parallel streams

If you have **2-3 concurrent sessions**:

**Batch A** (Most critical):
- Session 1: Stream 1 + Stream 2 (Add-on + Database)
- Session 2: Stream 3 (Integration Setup)

**Batch B** (After Batch A):
- Session 1: Stream 4 (Docs)
- Session 2: Stream 5 (Seed Data)

---

## Completion Criteria for Parallel Streams

**Stream 1 Complete When**:
- [ ] Flask app runs without errors
- [ ] Database connection works
- [ ] Dockerfile builds successfully
- [ ] Add-on installs in HA (even if non-functional)

**Stream 2 Complete When**:
- [ ] All 7 models defined with relationships
- [ ] Initial migration created
- [ ] Can create/query all models in Python shell
- [ ] Seed script creates sample data

**Stream 3 Complete When**:
- [ ] Integration loads in HA without errors
- [ ] Config flow appears in HA UI
- [ ] Manifest is valid
- [ ] Directory structure matches HA requirements

**Stream 4 Complete When**:
- [ ] Pre-commit hooks run successfully
- [ ] Test framework executes (even with no tests)
- [ ] Documentation structure exists with placeholders
- [ ] Linting passes on existing code

**Stream 5 Complete When**:
- [ ] Seed script creates full dataset
- [ ] Script is idempotent (no errors on re-run)
- [ ] Data includes all edge cases (claimed, approved, rejected chores)

---

## Quick Start Commands

Once parallel work is complete, you'll be able to:

**Start Add-on Development**:
```bash
cd addon
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
flask db upgrade
python seed.py
flask run
```

**Start Integration Development**:
```bash
# Copy to HA config directory
cp -r custom_components/chorecontrol /path/to/ha/config/custom_components/
# Restart HA
# Configure integration via UI
```

**Run Tests**:
```bash
pytest
pre-commit run --all-files
```

---

## After Parallel Work: Integration Point

Once all 5 streams are complete, you'll have:

1. ✅ Working Flask app structure with database
2. ✅ Complete data models with migrations
3. ✅ Integration skeleton that loads in HA
4. ✅ Linting and testing infrastructure
5. ✅ Seed data for development

**Next step**: Begin sequential work on API endpoints, business logic, and UI.

---

## Questions?

- Which streams do you want to tackle first?
- How many parallel sessions can you run?
- Any specific stream you want to start with?

**Recommendation**: Start with Streams 1 & 2 together (they're the most critical foundation).

---

**Last Updated**: 2025-11-11
