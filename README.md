# ChoreControl

> A comprehensive chore management system for Home Assistant

## Overview

ChoreControl is a Home Assistant integration that helps families manage chores, track points, and reward kids for completing tasks. Unlike existing solutions that rely on entity-based storage, ChoreControl uses a proper database structure for reliability and scalability.

### Key Features

#### Implemented ✅
- **Chore Management**: Create recurring (daily/weekly/monthly) or one-off chores with flexible scheduling
- **Multi-User Support**: Parent, kid, and system roles with appropriate permissions
- **Points & Rewards**: Kids earn points for completing chores, redeem for rewards with approval workflow
- **Approval Workflow**: Claim → Approve → Award points with late claim detection
- **Background Automation**: Auto-approval after timeout, missed chore detection, reward expiration
- **Late Claim Support**: Optional late completion with reduced points
- **Reward Approval**: Optional parent approval for reward claims with 7-day expiration
- **Points Auditing**: Nightly verification of points balances against transaction history
- **Webhook Integration**: Real-time event notifications to Home Assistant
- **REST API**: 28 endpoints for full programmatic control

#### Planned
- **Calendar Integration**: ICS feed showing upcoming chores
- **Mobile-First Admin UI**: Manage everything from your phone via HA sidebar
- **Dashboard Integration**: Native HA dashboards for kids and parents

## Architecture

ChoreControl consists of two main components:

1. **Add-on** (Backend Service)
   - Flask/FastAPI web application
   - SQLite database for proper data storage
   - REST API for all operations
   - Web UI for parent administration
   - Accessible via HA sidebar (ingress)

2. **Integration** (Custom Component)
   - Python custom component for Home Assistant
   - Exposes entities (sensors, buttons) to HA
   - Provides services for automations
   - Polls add-on API for updates

## Project Status

**Current Phase**: Web UI Complete ✅ → HA Integration

**Completed:**
- ✅ Flask app structure, config management (dev/prod/test environments)
- ✅ Database models (7 tables with full relationships and validation)
- ✅ Database migrations (2 migrations including business logic fields)
- ✅ **REST API (28 endpoints across 5 route modules)**
- ✅ **Business logic layer (recurrence, instances, points, rewards)**
- ✅ **Background jobs (5 scheduled jobs via APScheduler)**
- ✅ **Webhook integration (8 event types to Home Assistant)**
- ✅ **Comprehensive test suite (245 tests, 5,325+ lines of test code)**
- ✅ **Web UI (13 templates, mobile-first responsive design)**
- ✅ HA integration framework (manifest, config flow structure)
- ✅ Development tooling (pytest, ruff, black, mypy, pre-commit)
- ✅ Seed data generator with system user support

**Next Steps:**
1. Complete HA integration (sensors, services, entities)
2. Docker containerization for HA add-on

See [NEXT_STEPS.md](NEXT_STEPS.md) for detailed implementation guide.

- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** - Comprehensive project plan with architecture, data model, and roadmap
- **[BACKLOG.md](BACKLOG.md)** - Task backlog organized by phase
- **[docs/architecture.md](docs/architecture.md)** - Architecture, technology decisions, and business logic

## Documentation

### For Users
- Installation Guide (Coming soon)
- User Manual (Coming soon)
- FAQ (Coming soon)

### For Developers
- [Project Plan](PROJECT_PLAN.md) - Complete architectural overview
- [Task Backlog](BACKLOG.md) - Implementation tasks
- [Architecture & Decisions](docs/architecture.md) - Technology choices and business logic
- [API Reference](docs/api-reference.md) - API endpoint documentation
- Contributing Guide (Coming soon)

## Technology Stack

**Backend (Add-on)** - Implemented ✅
- Python 3.11+
- Flask 3.0+ with SQLAlchemy ORM
- SQLite database with Alembic migrations
- APScheduler for background jobs
- Requests for webhook delivery
- Comprehensive pytest test suite (245 tests)

**Planned**
- Jinja2 + HTMX/Alpine.js (web UI)
- Docker containerization

**Frontend (Integration)** - Framework Ready
- Python 3.11+ (HA custom component)
- Manifest and config flow structure in place
- Ready for sensor/service implementation

**Development** - Fully Configured ✅
- pytest with fixtures and mocking (245 tests, 100% critical path coverage)
- ruff for linting
- black for formatting
- mypy for type checking
- pre-commit hooks
- Git version control

## Getting Started

### Prerequisites
- Home Assistant instance (2024.1.0+)
- Basic understanding of HA add-ons and integrations
- (For development) Python 3.11+, Docker

### Installation

Not yet available as a Home Assistant add-on. See Development Setup below to run locally.

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/chorecontrol.git
   cd chorecontrol
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r addon/requirements.txt
   pip install -r addon/requirements-dev.txt
   ```

3. **Initialize the database:**
   ```bash
   cd addon
   export FLASK_APP=app.py
   export FLASK_ENV=development
   flask db upgrade
   ```

4. **Seed test data:**
   ```bash
   python seed_db.py
   # Creates: 2 parents, 2 kids, 5 chores, 4 rewards, sample instances
   ```

5. **Run the Flask app:**
   ```bash
   python app.py
   # Server starts on http://localhost:8099
   ```

6. **Run tests:**
   ```bash
   pytest -v
   # Runs 245 tests across 7 test modules
   ```

7. **Test API endpoints:**
   ```bash
   curl http://localhost:8099/health
   curl -H "X-Ingress-User: test-parent-1" http://localhost:8099/api/user
   ```

For more details, see [NEXT_STEPS.md](NEXT_STEPS.md).

## Roadmap

### Phase 1: Core Backend ✅ COMPLETE
- ✅ Database models and migrations
- ✅ REST API (28 endpoints)
- ✅ Business logic (recurrence, points, rewards)
- ✅ Background jobs (5 scheduled tasks)
- ✅ Webhook integration (8 event types)
- ✅ Comprehensive test suite (245 tests)

### Phase 2: Frontend & Integration (In Progress)
- **Web UI** (Current Focus)
  - Parent dashboard with approval queue
  - Chore/reward management forms
  - User management and points history
  - Mobile-responsive design
- **Home Assistant Integration**
  - Sensor entities (points, pending approvals)
  - Service calls (claim, approve, reject)
  - Button entities for chore instances
  - Event listeners for webhooks
- **Docker Add-on**
  - Dockerfile and build configuration
  - Add-on manifest and documentation
  - HA ingress configuration

### Phase 3: Enhancements
- Complex scheduling (cron-like patterns)
- Photo proof of completion
- Achievements and gamification
- Advanced analytics
- Custom Lovelace cards
- ICS calendar integration

### Phase 4: Advanced Features
- Multi-family support
- Mobile app
- Voice assistant integration
- External calendar sync (Google, Apple)

Full feature list in [PROJECT_PLAN.md](PROJECT_PLAN.md).

## Comparison to Existing Solutions

### vs kidschores-ha
ChoreControl improves on [kidschores-ha](https://github.com/ad-ha/kidschores-ha) by:
- Using proper database structure instead of entity-based storage
- Providing a dedicated admin UI via add-on
- Offering more robust scheduling and workflow options
- Better separation of concerns (add-on + integration architecture)

### vs Skylight Chore Chart
Inspired by [Skylight's chore features](https://myskylight.com/lp/chore-chart/), but:
- Fully integrated with Home Assistant ecosystem
- Self-hosted and private
- Extensible via HA automations
- Open source

## Contributing

Contributions welcome! This project is in early stages, so now is a great time to get involved.

### How to Contribute
1. Review [PROJECT_PLAN.md](PROJECT_PLAN.md) to understand the vision
2. Check [BACKLOG.md](BACKLOG.md) for available tasks
3. Comment on issues or create new ones for discussion
4. Submit PRs (once development begins)

### Development Principles
- Mobile-first design
- HA-native integration
- Proper data modeling
- User-friendly for non-technical parents
- Clean, documented, testable code

## License

MIT License (TBD - to be added once project structure is finalized)

## Support

- **Issues**: GitHub Issues (for bugs and feature requests)
- **Discussions**: GitHub Discussions (for questions and ideas)
- **Documentation**: See docs/ folder (coming soon)

## Acknowledgments

- Inspired by [kidschores-ha](https://github.com/ad-ha/kidschores-ha)
- UI/UX ideas from [Skylight Chore Chart](https://myskylight.com/lp/chore-chart/)
- Built for the Home Assistant community

## Contact

Project maintained by [Your Name] - [Your Email/GitHub]

---

**Status**: Backend Complete, Frontend In Progress
**Last Updated**: 2025-11-19
**Version**: 0.2.0-alpha (backend functional, UI pending)
