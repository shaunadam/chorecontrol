# Stream Prompts for Parallel Development

Copy and paste these prompts into separate Claude sessions to work on multiple streams concurrently.

---

## 🔧 STREAM 1: Add-on Project Setup

```
I'm working on ChoreControl, a Home Assistant chore management system. This is one of 5 parallel work streams.

PROJECT CONTEXT:
- Repository: /home/user/chorecontrol
- Branch: claude/kidschores-ha-review-011CV1aKQricdhqohW9i8bos
- Architecture: Flask add-on + SQLite + Home Assistant integration
- Documentation: Read PROJECT_PLAN.md, DECISIONS.md, NEXT_STEPS.md in the repo

MY TASK (Stream 1):
Set up the Flask add-on project structure for a Home Assistant add-on.

SPECIFIC DELIVERABLES:
1. Create addon/ directory structure:
   - addon/app.py (Flask application entry point)
   - addon/config.py (Flask configuration)
   - addon/requirements.txt (Python dependencies)
   - addon/Dockerfile (HA add-on container)
   - addon/config.json (HA add-on metadata)
   - addon/run.sh (startup script)
   - addon/README.md (add-on specific docs)

2. requirements.txt should include:
   - Flask>=2.3.0
   - Flask-SQLAlchemy>=3.0.0
   - Flask-Migrate>=4.0.0
   - APScheduler>=3.10.0
   - ics>=0.7
   - jsonschema>=4.17.0
   - requests>=2.31.0

3. app.py should:
   - Initialize Flask app
   - Configure Flask-SQLAlchemy
   - Set up basic routes (/, /health)
   - Handle HA ingress authentication (X-Ingress-User header)
   - Be ready for models to be imported later

4. Dockerfile should:
   - Use Python 3.11 base (homeassistant base image preferred)
   - Copy application files
   - Install dependencies
   - Set up data directory for SQLite
   - Run migrations on startup
   - Start Flask app

5. config.json should:
   - Define add-on metadata (name, description, version)
   - Configure ingress for sidebar access
   - Define required capabilities
   - Set startup type

6. run.sh should:
   - Check for database and create if needed
   - Run Flask-Migrate upgrade
   - Start Flask app with appropriate settings

SUCCESS CRITERIA:
- [ ] Flask app runs without errors (even without models)
- [ ] Dockerfile builds successfully
- [ ] config.json is valid HA add-on format
- [ ] Directory structure matches HA add-on requirements
- [ ] Ready to add models and routes

REFERENCE DOCS:
- See PROJECT_PLAN.md "Component Breakdown -> Add-on" section
- See DECISIONS.md for technology choices
- See NEXT_STEPS.md "Stream 1" for details

IMPORTANT NOTES:
- This stream is independent - don't wait for models
- Use Flask-SQLAlchemy but models will come from Stream 2
- Authentication via HA ingress headers (read X-Ingress-User)
- Database path should be /data/chorecontrol.db

Commit your work when complete. Good luck!
```

---

## 📊 STREAM 2: Database Schema & Models

```
I'm working on ChoreControl, a Home Assistant chore management system. This is one of 5 parallel work streams.

PROJECT CONTEXT:
- Repository: /home/user/chorecontrol
- Branch: claude/kidschores-ha-review-011CV1aKQricdhqohW9i8bos
- Architecture: Flask add-on + SQLite + SQLAlchemy ORM
- Documentation: Read PROJECT_PLAN.md (Data Model section), DECISIONS.md

MY TASK (Stream 2):
Design and implement all SQLAlchemy models for the database layer.

SPECIFIC DELIVERABLES:
1. Create addon/models.py with 7 models:
   - User (ha_user_id, username, role, points)
   - Chore (name, recurrence_pattern as JSON, assignment_type, requires_approval)
   - ChoreAssignment (links chores to users)
   - ChoreInstance (tracks individual completions, status workflow)
   - Reward (points_cost, cooldown_days, max_claims)
   - RewardClaim (tracks redemptions)
   - PointsHistory (audit log of all point changes)

2. Create addon/schemas.py:
   - JSON schema for recurrence patterns
   - Validation functions for pattern types (simple, complex)
   - Helper functions to parse/generate patterns

3. Define all relationships:
   - Foreign keys properly set up
   - Backrefs for easy navigation
   - Cascade deletes where appropriate

4. Add model methods:
   - User: calculate_current_points() from history
   - Chore: generate_next_instance(), is_due()
   - ChoreInstance: can_claim(), can_approve(), award_points()
   - Reward: can_claim(), is_on_cooldown()

5. Create initial Alembic migration:
   - Initialize Flask-Migrate
   - Generate initial migration from models
   - Test migration up/down

SUCCESS CRITERIA:
- [ ] All 7 models defined with proper types
- [ ] Relationships work (can navigate user.chores, etc.)
- [ ] Initial migration created and tested
- [ ] Can create and query all models in Python shell
- [ ] JSON schema validates recurrence patterns

REFERENCE DOCS:
- See PROJECT_PLAN.md "Data Model" section (has complete SQL schemas)
- See DECISIONS.md DEC-003 (SQLAlchemy ORM) and DEC-010 (JSON patterns)

IMPORTANT NOTES:
- This stream is independent - don't wait for Flask app
- Use Flask-SQLAlchemy decorators (db.Model, db.Column)
- ChoreInstance status: 'assigned', 'claimed', 'approved', 'rejected'
- User role: 'parent' or 'kid'
- Soft delete: use is_active boolean flag
- Points are stored denormalized in User.points but verified against PointsHistory

EXAMPLE RECURRENCE PATTERN:
Simple: {"type": "daily", "interval": 1}
Weekly: {"type": "weekly", "days": [1, 3, 5], "time": "18:00"}

Commit your work when complete. Good luck!
```

---

## 🏠 STREAM 3: Integration Project Setup

```
I'm working on ChoreControl, a Home Assistant chore management system. This is one of 5 parallel work streams.

PROJECT CONTEXT:
- Repository: /home/user/chorecontrol
- Branch: claude/kidschores-ha-review-011CV1aKQricdhqohW9i8bos
- Architecture: HA custom integration that talks to Flask add-on
- Documentation: Read PROJECT_PLAN.md, DECISIONS.md

MY TASK (Stream 3):
Set up the Home Assistant custom integration structure.

SPECIFIC DELIVERABLES:
1. Create custom_components/chorecontrol/ directory structure:
   - __init__.py (integration setup and entry point)
   - manifest.json (integration metadata)
   - const.py (constants: DOMAIN, DEFAULT_SCAN_INTERVAL, etc.)
   - config_flow.py (UI configuration flow)
   - strings.json (translations)
   - services.yaml (service definitions)

2. manifest.json should include:
   - domain: "chorecontrol"
   - name: "ChoreControl"
   - version: "0.1.0"
   - dependencies: []
   - codeowners: []
   - iot_class: "local_polling"
   - requirements: ["aiohttp"]

3. __init__.py should:
   - async_setup_entry function
   - Load platforms (sensor, button)
   - Set up services
   - Handle integration lifecycle

4. config_flow.py should:
   - User input form for add-on URL
   - Optional: scan interval configuration
   - Validation that add-on is reachable
   - Store config in config entry

5. const.py should define:
   - DOMAIN = "chorecontrol"
   - DEFAULT_SCAN_INTERVAL = 30
   - Event types (chorecontrol_chore_claimed, etc.)
   - Sensor types
   - Service names

6. services.yaml should define:
   - claim_chore (parameters: chore_instance_id, user_id)
   - approve_chore (parameters: chore_instance_id, approver_user_id)
   - reject_chore (parameters: chore_instance_id, approver_user_id, reason)
   - adjust_points (parameters: user_id, points_delta, reason)
   - claim_reward (parameters: reward_id, user_id)

7. Create placeholder files (empty but ready):
   - sensor.py (will contain sensor platform)
   - button.py (will contain button platform)
   - coordinator.py (will contain data update coordinator)
   - api_client.py (will contain REST API client)

8. Set up for HACS compatibility:
   - Create hacs.json
   - Add required metadata

SUCCESS CRITERIA:
- [ ] Integration loads in HA without errors (even without functionality)
- [ ] Config flow appears in HA UI
- [ ] manifest.json is valid
- [ ] Directory structure matches HA requirements
- [ ] Services are registered (even if not implemented)

REFERENCE DOCS:
- See PROJECT_PLAN.md "Component Breakdown -> Integration" section
- See DECISIONS.md DEC-004 (auth), DEC-007 (events), DEC-009 (polling)
- Home Assistant integration docs: https://developers.home-assistant.io/

IMPORTANT NOTES:
- This stream is independent - don't implement actual functionality
- Use async/await patterns (HA requirement)
- Integration communicates with add-on via REST API
- Add-on URL will be user-configurable (default: http://addon_slug)
- Event types should match DEC-007 decision

Commit your work when complete. Good luck!
```

---

## 📝 STREAM 4: Documentation & Tooling

```
I'm working on ChoreControl, a Home Assistant chore management system. This is one of 5 parallel work streams.

PROJECT CONTEXT:
- Repository: /home/user/chorecontrol
- Branch: claude/kidschores-ha-review-011CV1aKQricdhqohW9i8bos
- Tech stack: Flask, SQLAlchemy, Python 3.11+
- Documentation: Read PROJECT_PLAN.md, DECISIONS.md

MY TASK (Stream 4):
Set up development tooling, testing infrastructure, and documentation templates.

SPECIFIC DELIVERABLES:
1. Create .pre-commit-config.yaml:
   - ruff (linting and formatting)
   - black (code formatting)
   - mypy (type checking)
   - trailing whitespace removal
   - yaml/json validation

2. Create pyproject.toml:
   - Configure ruff (line length, rules)
   - Configure black (line length, target version)
   - Configure mypy (strict mode, ignore missing imports for now)
   - Configure pytest

3. Set up testing structure:
   - tests/ directory
   - tests/conftest.py (pytest fixtures)
   - tests/test_models.py (placeholder)
   - tests/test_api.py (placeholder)
   - tests/integration/test_e2e.py (placeholder)
   - pytest.ini or pyproject.toml test config

4. Create docs/ structure:
   - docs/installation.md (template with TODOs)
   - docs/user-guide.md (template with TODOs)
   - docs/api-reference.md (template for API docs)
   - docs/development.md (setup instructions for contributors)
   - docs/architecture.md (link to PROJECT_PLAN.md)

5. Create CONTRIBUTING.md:
   - How to set up development environment
   - How to run tests
   - Code style guidelines
   - PR process
   - Link to NEXT_STEPS.md for tasks

6. Update .gitignore:
   - Python artifacts (__pycache__, *.pyc)
   - Virtual environments (venv/, .venv/)
   - IDE files (.vscode/, .idea/)
   - Database files (*.db, *.db-journal)
   - Flask/migration artifacts

7. Create Makefile (optional):
   - make install (pip install requirements)
   - make test (run pytest)
   - make lint (run pre-commit)
   - make format (black + ruff fix)
   - make migrate (flask db migrate)

SUCCESS CRITERIA:
- [ ] pre-commit hooks run successfully on existing code
- [ ] pytest runs without errors (even with no tests)
- [ ] Linting passes on all Python files
- [ ] Documentation structure exists with placeholders
- [ ] CONTRIBUTING.md provides clear setup instructions

REFERENCE DOCS:
- See PROJECT_PLAN.md "Development Principles" section
- See DECISIONS.md for chosen technologies
- See NEXT_STEPS.md "Stream 4" for checklist

IMPORTANT NOTES:
- This stream is independent - don't wait for code
- Configure tools to be strict but not annoying
- pre-commit should auto-fix when possible
- pytest should work with Flask app context
- Document Python 3.11+ requirement

TOOL VERSIONS:
- ruff >= 0.1.0
- black >= 23.0.0
- mypy >= 1.5.0
- pytest >= 7.4.0
- pytest-cov (for coverage)

Commit your work when complete. Good luck!
```

---

## 🧪 STREAM 5: Test Data & Seed Scripts

```
I'm working on ChoreControl, a Home Assistant chore management system. This is one of 5 parallel work streams.

PROJECT CONTEXT:
- Repository: /home/user/chorecontrol
- Branch: claude/kidschores-ha-review-011CV1aKQricdhqohW9i8bos
- Database: SQLite with SQLAlchemy models
- Documentation: Read PROJECT_PLAN.md (Data Model section)

MY TASK (Stream 5):
Create seed data scripts for development and testing.

SPECIFIC DELIVERABLES:
1. Create addon/seed.py script that:
   - Can be run multiple times (idempotent)
   - Clears existing data (with confirmation)
   - Creates realistic sample data
   - Outputs summary of what was created

2. Sample data to create:
   - 2 parent users (linked to HA user IDs)
   - 3 kid users (different ages/points)
   - 10-15 chores (mix of daily, weekly, one-off)
   - Assignments linking chores to kids
   - 20+ chore instances in various states:
     * Some assigned (not started)
     * Some claimed (pending approval)
     * Some approved (completed)
     * Some rejected (with reasons)
   - 5-7 rewards (different point costs)
   - 3-5 reward claims (some redeemed)
   - Points history matching all the above

3. Make it realistic:
   - Kid names: Alex, Bailey, Charlie
   - Parent names: ParentOne, ParentTwo
   - Chores: "Take out trash", "Do dishes", "Clean room", "Homework", "Walk dog"
   - Rewards: "Ice cream trip", "Extra screen time", "Stay up late", "Choose dinner"
   - Points: Kids have 0-50 points
   - Dates: Use recent dates (last 7 days)

4. Create addon/seed_helpers.py:
   - Functions to generate random dates
   - Functions to create recurrence patterns
   - Helper to generate realistic chore names
   - Helper to assign chores to appropriate kids (age-based)

5. Make it configurable:
   - Command-line args for number of users/chores
   - Flag to preserve existing data vs full reset
   - Verbose mode to show what's being created

6. Create test fixtures:
   - tests/fixtures/sample_data.json
   - Contains minimal dataset for unit tests
   - Can be loaded by pytest fixtures

SUCCESS CRITERIA:
- [ ] seed.py runs without errors
- [ ] Can be run multiple times safely
- [ ] Creates full, realistic dataset
- [ ] All relationships are valid (no foreign key errors)
- [ ] Points balance matches history
- [ ] Sample data covers all edge cases (claimed, approved, rejected)

REFERENCE DOCS:
- See PROJECT_PLAN.md "Data Model" section for all tables
- See DECISIONS.md DEC-010 for recurrence pattern JSON format

IMPORTANT NOTES:
- This stream depends on Stream 2 (models) being complete
- If models aren't ready, write the seed logic and add imports later
- Use faker library for realistic data if desired
- Seed script should be usable in production for demos
- HA user IDs should be fake but valid format

EXAMPLE USAGE:
```bash
python seed.py --reset --verbose
python seed.py --kids 5 --chores 20
python seed.py --preserve
```

EDGE CASES TO COVER:
- Chore with auto-approval enabled
- Chore claimed but overdue
- Kid with negative points
- Reward on cooldown
- Reward at claim limit
- Chore assigned to multiple kids (shared)

Commit your work when complete. Good luck!
```

---

## 📋 How to Use These Prompts

1. **Copy the prompt** for the stream you want to work on
2. **Paste into a new Claude session** (or assign to a team member)
3. **Claude will read the existing docs** and implement the stream
4. **Each stream commits** its work independently
5. **Reconvene** when all streams are done to integrate

## 🔄 Integration After Parallel Work

Once all 5 streams are complete:
1. Pull latest changes from all streams
2. Resolve any minor conflicts (shouldn't be many)
3. Test that addon/ runs with models loaded
4. Test that integration/ loads in HA
5. Begin sequential work on API endpoints (Week 1)

---

**Last Updated**: 2025-11-11
