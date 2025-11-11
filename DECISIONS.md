# Technology Decisions

This document tracks key technology decisions for the ChoreControl project.

## Decision Log

### Format
```
## [DECISION-ID] Decision Title
**Status**: Proposed | Accepted | Rejected | Superseded
**Date**: YYYY-MM-DD
**Decider**: Name
**Context**: Why we need to make this decision
**Options**:
- Option A: Description, pros, cons
- Option B: Description, pros, cons
**Decision**: What we chose and why
**Consequences**: What this means for the project
```

---

## [DEC-001] Web Framework for Add-on Backend

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: Need to choose a Python web framework for the add-on's REST API and web UI

**Options**:
- **FastAPI**:
  - Pros: Modern, async, automatic OpenAPI docs, type hints, fast
  - Cons: Slightly steeper learning curve, newer (less mature)
- **Flask**:
  - Pros: Simple, mature, lots of examples, extensive ecosystem
  - Cons: Sync by default, no auto-docs, more boilerplate

**Recommendation**: FastAPI
- Async will help with concurrent requests from multiple users
- Auto-generated API docs useful for integration development
- Type hints improve code quality and IDE support
- Performance benefits for real-time updates

**Decision**: **Flask** - Prioritizing simplicity and familiarity
- Developer already knows Flask
- Simpler learning curve for MVP
- Extensive ecosystem and examples
- Mature and stable for production use
- Can add async extensions if needed later (Flask 2.0+ supports async)

**Consequences**:
- Use Flask + Flask-RESTful or Flask-RESTX for API
- Sync by default, but adequate for expected load
- Will need to manually document API (can use flask-swagger or similar)
- SQLAlchemy will work seamlessly with Flask-SQLAlchemy extension

---

## [DEC-002] Frontend Framework for Add-on Web UI

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: Need to choose how to build the admin web UI for the add-on

**Options**:
- **Jinja2 + HTMX**:
  - Pros: No build step, simple deployment, lightweight, progressive enhancement
  - Cons: Less interactive, older patterns
- **React/Vue SPA**:
  - Pros: Rich interactivity, modern UX, reusable components
  - Cons: Build step required, more complex deployment, larger bundle
- **Alpine.js + Tailwind**:
  - Pros: Lightweight, no build, modern utility CSS
  - Cons: Less structure for large apps

**Recommendation**: Jinja2 + HTMX + Tailwind CSS
- No build step = easier for contributors
- HTMX provides enough interactivity for admin UI
- Can always migrate to SPA later if needed
- Mobile-first with Tailwind utilities

**Decision**: **Jinja2 + HTMX** as recommended
- Server-rendered templates (Flask's built-in Jinja2)
- HTMX for dynamic interactions without JavaScript complexity
- Tailwind CSS via CDN for mobile-first styling
- No build step = simpler Docker image and deployment

**Consequences**:
- Templates live in `templates/` directory
- Static files (CSS, JS) in `static/` directory
- Use HTMX attributes for AJAX interactions (hx-get, hx-post, etc.)
- Can use Alpine.js for small client-side interactions if needed
- Simpler for contributors unfamiliar with modern JS frameworks

---

## [DEC-003] ORM vs Raw SQL

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: Need to decide how to interact with SQLite database

**Options**:
- **SQLAlchemy ORM**:
  - Pros: Type-safe models, easier migrations, relationship handling
  - Cons: Learning curve, abstraction overhead
- **Raw SQL with sqlite3**:
  - Pros: Simple, direct control, no dependencies
  - Cons: Manual query building, harder to maintain migrations
- **SQLAlchemy Core (no ORM)**:
  - Pros: Type safety without full ORM, SQL-like syntax
  - Cons: Still requires learning SQLAlchemy

**Recommendation**: SQLAlchemy ORM
- Better for schema evolution (migrations with Alembic)
- Type hints and IDE support for models
- Relationship handling (foreign keys, joins) is easier
- Worth the learning investment for maintainability

**Decision**: **SQLAlchemy ORM** as recommended
- Use Flask-SQLAlchemy extension for Flask integration
- Define models with proper relationships
- Type hints for better IDE support
- Foundation for Alembic migrations

**Consequences**:
- Install Flask-SQLAlchemy and SQLAlchemy
- Models defined as Python classes in `models.py`
- Automatic relationship loading (lazy/eager configurable)
- Query syntax: `User.query.filter_by(role='parent').all()`
- Enables DEC-005 (Alembic migrations)

---

## [DEC-004] Authentication Strategy

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: How should the add-on authenticate requests?

**Options**:
- **Trust HA Ingress Headers**:
  - Pros: Simple, no extra auth needed, HA handles it
  - Cons: Only works via ingress, no external API access
- **API Key + JWT**:
  - Pros: Secure, supports external access, standard pattern
  - Cons: More complex, key management needed
- **Hybrid (Ingress + Optional API Key)**:
  - Pros: Best of both, flexible
  - Cons: Most complex to implement

**Recommendation**: Trust HA Ingress for Phase 1, add API key in Phase 2
- Simplest path to MVP
- HA ingress provides auth via user session
- Can extract HA user ID from `X-Ingress-User` header
- Add API key later if external access needed

**Decision**: **Trust HA Ingress** as recommended for Phase 1
- Read `X-Ingress-User` header for HA user ID
- Map HA user to internal user/role via database lookup
- Web UI protected by HA authentication
- API endpoints protected by checking ingress headers

**Consequences**:
- Add-on only accessible via HA (perfect for MVP)
- No external API access initially (can add in Phase 2)
- Simple middleware to extract user from headers
- User mapping table required (ha_user_id → internal user_id)

---

## [DEC-005] Database Migration Strategy

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: How to handle database schema changes over time?

**Options**:
- **Alembic (with SQLAlchemy)**:
  - Pros: Industry standard, auto-generate migrations, rollback support
  - Cons: Requires SQLAlchemy, learning curve
- **Manual SQL Migration Scripts**:
  - Pros: Simple, direct control
  - Cons: Easy to mess up, no auto-generation
- **Schema Versioning + Rebuild**:
  - Pros: Simplest for small DB
  - Cons: Loses data on schema change (unacceptable)

**Recommendation**: Alembic
- Pairs with SQLAlchemy ORM decision
- Critical for long-term maintainability
- Users won't lose data on updates

**Decision**: **Alembic** as recommended (follows from DEC-003)
- Flask-Migrate extension (wrapper around Alembic for Flask)
- Auto-generate migrations from model changes
- Version control migrations in `migrations/` directory
- Run `flask db upgrade` on container startup

**Consequences**:
- Install Flask-Migrate
- Initialize migrations: `flask db init`
- Generate migration: `flask db migrate -m "description"`
- Apply migration: `flask db upgrade`
- Migrations stored in git for version history
- Startup script checks and applies pending migrations

---

## [DEC-006] Task Scheduling (Background Jobs)

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: How to run scheduled tasks (chore generation, auto-approval)?

**Options**:
- **APScheduler**:
  - Pros: Pure Python, simple, supports interval/cron
  - Cons: In-memory (lost on restart unless persistent jobstore)
- **Celery + Redis**:
  - Pros: Robust, distributed, many features
  - Cons: Requires Redis, overkill for single add-on
- **Simple Thread + asyncio**:
  - Pros: No dependencies, lightweight
  - Cons: Manual implementation, less features

**Recommendation**: APScheduler with SQLite jobstore
- Lightweight, no extra services needed
- Persistent across restarts
- Good enough for low-frequency tasks (daily chore generation)

**Decision**: **APScheduler** as recommended
- Use APScheduler with SQLAlchemy jobstore (shares same DB)
- Schedule daily chore generation (midnight)
- Schedule auto-approval checks (every hour)
- Initialize scheduler on Flask app startup

**Consequences**:
- Install APScheduler
- Configure jobstore to use same SQLite database
- Jobs persist across container restarts
- Thread-safe database sessions required
- Jobs defined in `scheduler.py` module

---

## [DEC-007] Notification System

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: How should the add-on trigger notifications in HA?

**Options**:
- **Webhook to Integration**:
  - Pros: Push notifications, real-time
  - Cons: Integration must expose webhook, more complex
- **HA Event Bus (via WebSocket)**:
  - Pros: Real-time, HA-native
  - Cons: Add-on needs HA API access
- **Integration Polls for Events**:
  - Pros: Simple, no webhook needed
  - Cons: Delayed notifications (poll interval)

**Recommendation**: Polling for Phase 1, webhook for Phase 2
- Integration already polls for entity updates
- Include "pending_notifications" in poll response
- Integration fires HA notify service when new notifications found
- Simple and works with existing architecture

**Decision**: **Webhook/HA Event Bus** - Future-proof architecture
- Add-on pushes events to HA event bus via HA API
- Real-time notifications, no polling delay
- Reduces unnecessary API polling (only poll for entity state)
- Integration listens to custom event types (chorecontrol_*)

**Consequences**:
- Add-on needs HA Supervisor API access (available to add-ons)
- Post events to `http://supervisor/core/api/events/chorecontrol_event`
- Integration subscribes to event types in setup
- Event types: `chorecontrol_chore_claimed`, `chorecontrol_chore_approved`, etc.
- More complex but better UX (instant notifications)
- Can still poll for entity states separately (or use events for that too)

---

## [DEC-008] Calendar ICS Generation

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: How to generate ICS calendar feeds?

**Options**:
- **ics Python library**:
  - Pros: Simple, pure Python, generates valid ICS
  - Cons: Another dependency
- **Manual ICS string building**:
  - Pros: No dependency
  - Cons: Easy to get wrong, RFC compliance tricky
- **vobject library**:
  - Pros: More features (VTODO support)
  - Cons: Heavier dependency

**Recommendation**: ics library
- Simple API, well-maintained
- Handles RFC compliance automatically
- Lightweight enough for our use case

**Decision**: **ics library** as recommended
- Generate ICS feed on-demand at `/api/calendar/{user_id}.ics`
- Cache generated ICS with 5-minute TTL
- Include upcoming chores (next 30 days)
- Each chore instance becomes a VEVENT

**Consequences**:
- Install `ics` library
- Create calendar view/route in Flask
- HA calendar integration subscribes to URL
- Can use VTODO instead of VEVENT if desired (to-do items vs events)

---

## [DEC-009] Home Assistant Integration Update Interval

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: How often should the integration poll the add-on API?

**Options**:
- **15 seconds**: Very responsive, higher load
- **30 seconds**: Balanced, standard for HA integrations
- **60 seconds**: Lower load, delayed updates
- **Configurable**: User chooses, more flexible

**Recommendation**: 30 seconds default, configurable in UI
- Most HA integrations use 30s
- Chore updates aren't millisecond-critical
- Let power users reduce to 15s if desired

**Decision**: **30 seconds default, configurable** as recommended
- Default SCAN_INTERVAL = 30 seconds
- Configurable in integration config flow
- Allow 10-300 second range
- Note: With event-based notifications (DEC-007), polling only for entity states

**Consequences**:
- DataUpdateCoordinator uses configured interval
- Entity states refresh every 30s by default
- Notifications are real-time (event-based)
- Users can tune based on their preference/load

---

## [DEC-010] Chore Recurrence Pattern Storage

**Status**: ✅ Accepted
**Date**: 2025-11-11
**Decider**: Project Owner
**Context**: How to store recurrence patterns in database?

**Options**:
- **JSON string in TEXT column**:
  - Pros: Flexible, easy to extend
  - Cons: No DB-level validation
- **Separate recurrence_rules table**:
  - Pros: Normalized, queryable
  - Cons: More complex schema
- **Cron expression string**:
  - Pros: Standard format, libraries available
  - Cons: Not user-friendly, harder to parse for UI

**Recommendation**: JSON in TEXT column
- SQLite handles JSON queries well
- Easy to add new pattern types
- Can validate in application layer
- Example: `{"type": "weekly", "days": [1, 3, 5], "time": "18:00"}`

**Decision**: **JSON in TEXT column** as recommended
- Store as TEXT in `chores.recurrence_pattern`
- Validate with JSON schema (jsonschema library)
- Parse in Python for scheduling logic
- Form UI converts to/from JSON

**Consequences**:
- Install `jsonschema` for validation
- Define schema for simple and complex patterns
- Helper functions to parse/generate recurrence patterns
- SQLite JSON functions available for queries if needed

---

## Decision Summary

All major technology decisions have been made:

- [x] **DEC-001**: Flask (simple, familiar)
- [x] **DEC-002**: Jinja2 + HTMX (no build step)
- [x] **DEC-003**: SQLAlchemy ORM (maintainable)
- [x] **DEC-004**: Trust HA Ingress (simple auth)
- [x] **DEC-005**: Alembic via Flask-Migrate (migrations)
- [x] **DEC-006**: APScheduler (background jobs)
- [x] **DEC-007**: HA Event Bus via Supervisor API (real-time)
- [x] **DEC-008**: ics library (calendar feeds)
- [x] **DEC-009**: 30s configurable polling (entity state)
- [x] **DEC-010**: JSON in TEXT (recurrence patterns)

**Ready to begin implementation!**

---

**Last Updated**: 2025-11-11
