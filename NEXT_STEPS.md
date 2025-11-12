# Next Steps - Post Stream Integration

## ✅ Completed (Streams 1-5)

All parallel stream work is complete and integrated:

- **Stream 1**: Add-on project structure (Flask, Docker, config)
- **Stream 2**: Database models and schemas (7 tables, relationships, validation)
- **Stream 3**: HA integration structure (manifest, config flow, services)
- **Stream 4**: Development tooling (pytest, ruff, black, mypy, pre-commit)
- **Stream 5**: Seed data scripts (realistic test data generation)

**Integration fixes applied:**
- Fixed duplicate imports in requirements.txt
- Fixed SQLAlchemy db instance sharing between app.py and models.py
- Added missing files to Dockerfile (models, schemas, seed scripts)
- Fixed relative import in models.py

---

## 📋 For You: Local Environment Setup & Testing

Before we continue with API development, you should set up a local environment and verify everything works:

### 1. Set Up Local Development Environment

```bash
cd /home/user/chorecontrol

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r addon/requirements.txt

# Install dev dependencies
pip install pytest pytest-cov pytest-flask ruff black mypy pre-commit
```

### 2. Initialize Database

```bash
cd addon

# Initialize Flask-Migrate
export FLASK_APP=app.py
export FLASK_ENV=development
flask db init

# Create initial migration from models
flask db migrate -m "Initial database schema"

# Apply migration
flask db upgrade

# Verify database was created
ls -la data/
```

### 3. Seed Test Data

```bash
# Run seed script to populate database with test data
python seed.py --reset --verbose

# This creates:
# - 2 parent users
# - 3 kid users (Alex, Bailey, Charlie)
# - ~15 chores (various recurrence patterns)
# - ~20 chore instances (assigned, claimed, approved, rejected)
# - 5-7 rewards
# - Points history
```

### 4. Test Flask Application

```bash
# Start Flask development server
python app.py

# In another terminal, test endpoints:
curl http://localhost:8099/health
curl http://localhost:8099/
curl -H "X-Ingress-User: test-parent-1" http://localhost:8099/api/user
```

**Expected results:**
- `/health` returns `{"status": "healthy", "database": "healthy"}`
- `/` returns app info with version 0.1.0
- `/api/user` returns authenticated user info

### 5. Run Tests

```bash
# Run linting
pre-commit run --all-files

# Run tests (will mostly be skeletons for now)
pytest tests/ -v

# Check test coverage
pytest --cov=addon tests/
```

### 6. Test Docker Build (Optional)

```bash
cd addon
docker build -t chorecontrol-test .

# If build succeeds, the container is ready for HA
```

---

## 🎯 What to Look For / Test

### Database Tests
- [ ] SQLite database created in `addon/data/chorecontrol.db`
- [ ] All 7 tables exist (users, chores, chore_assignments, chore_instances, rewards, reward_claims, points_history)
- [ ] Seed data populated (query with `sqlite3 data/chorecontrol.db "SELECT * FROM users;"`)
- [ ] Foreign keys working (no constraint violations)

### Application Tests
- [ ] Flask app starts without errors
- [ ] Health endpoint accessible
- [ ] Database connectivity working
- [ ] HA user authentication (via X-Ingress-User header) working

### Code Quality Tests
- [ ] Pre-commit hooks run successfully
- [ ] Ruff linting passes
- [ ] Black formatting passes
- [ ] Mypy type checking passes (with --ignore-missing-imports)

### Issues to Report
- Any import errors
- Database schema issues
- Migration failures
- Docker build failures
- Linting errors you can't resolve

---

## 🚀 Next Phase: API & Business Logic Implementation

Once you've verified the local setup works, we'll proceed with:

### Week 1: Core API Endpoints
1. **User endpoints** (CRUD operations)
   - GET /api/users
   - POST /api/users
   - GET /api/users/{id}
   - PUT /api/users/{id}

2. **Chore endpoints** (CRUD operations)
   - GET /api/chores
   - POST /api/chores
   - GET /api/chores/{id}
   - PUT /api/chores/{id}
   - DELETE /api/chores/{id} (soft delete)

3. **Chore instance endpoints** (workflow)
   - GET /api/instances
   - POST /api/instances/{id}/claim
   - POST /api/instances/{id}/approve
   - POST /api/instances/{id}/reject

4. **Reward endpoints**
   - GET /api/rewards
   - POST /api/rewards/{id}/claim

5. **Points endpoint**
   - POST /api/points/adjust

### Week 2: Business Logic
- Chore scheduler (generate instances from recurrence patterns)
- Points calculation and awarding
- Reward claim validation
- Background task runner (APScheduler)
- Event notifications to HA

### Week 3: Integration Implementation
- REST API client for integration
- Data coordinator
- Sensor platform (points, counts)
- Button platform (claim buttons)
- Service implementations

### Week 4: Web UI (Basic)
- Base template and navigation
- Chores list and management
- Kids management
- Parent dashboard (pending approvals)

---

## 📊 Current Stats

**Lines of Code Written:**
- Models: ~520 lines
- Schemas: ~480 lines
- Seed scripts: ~350 lines
- Integration: ~600 lines
- Tests/Config: ~300 lines
- **Total: ~2,250 lines**

**Files Created:**
- 14 Python files
- 4 YAML/JSON configs
- 7 documentation files
- 5 test files

**Dependencies:**
- 8 production packages
- 7 development packages

---

## 💡 Questions?

If you encounter any issues during local setup:
1. Check Python version (`python --version` should be 3.11+)
2. Verify virtual environment is activated
3. Check migrations directory exists (`addon/migrations/`)
4. Review error messages in Flask logs
5. Report issues with full error traces

**Ready to start API implementation when you are!**

---

**Last Updated**: 2025-11-11
**Phase**: Foundation Complete → API Implementation Next
