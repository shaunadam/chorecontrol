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

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
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

**Decision**: TBD

**Consequences**:
- If FastAPI: Need to learn async patterns, use async DB drivers
- If Flask: Simpler initial dev, may need to migrate for performance later

---

## [DEC-002] Frontend Framework for Add-on Web UI

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
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

**Decision**: TBD

**Consequences**:
- If server-rendered: Simpler deployment, slightly less responsive UI
- If SPA: Need build pipeline in Docker, more complex but richer UX

---

## [DEC-003] ORM vs Raw SQL

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
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

**Decision**: TBD

**Consequences**:
- If ORM: Need Alembic for migrations, learn ORM patterns
- If raw SQL: Manual migration scripts, more boilerplate for CRUD

---

## [DEC-004] Authentication Strategy

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
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

**Decision**: TBD

**Consequences**:
- If ingress-only: Cannot call API from outside HA network initially
- If API key: More secure but requires key management UI

---

## [DEC-005] Database Migration Strategy

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
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

**Decision**: TBD (depends on DEC-003)

**Consequences**:
- Need to include Alembic in Docker container
- Migration scripts run on add-on startup

---

## [DEC-006] Task Scheduling (Background Jobs)

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
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

**Decision**: TBD

**Consequences**:
- APScheduler runs in-process with web app
- Need to ensure thread safety with DB access

---

## [DEC-007] Notification System

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
**Context**: How should the add-on trigger notifications in HA?

**Options**:
- **Webhook to Integration**:
  - Pros: Push notifications, real-time
  - Cons: Integration must expose webhook, more complex
- **Integration Polls for Events**:
  - Pros: Simple, no webhook needed
  - Cons: Delayed notifications (poll interval)
- **HA Event Bus (via WebSocket)**:
  - Pros: Real-time, HA-native
  - Cons: Add-on needs HA API access

**Recommendation**: Polling for Phase 1, webhook for Phase 2
- Integration already polls for entity updates
- Include "pending_notifications" in poll response
- Integration fires HA notify service when new notifications found
- Simple and works with existing architecture

**Decision**: TBD

**Consequences**:
- Notifications delayed by poll interval (30 seconds)
- Good enough for MVP, optimize later

---

## [DEC-008] Calendar ICS Generation

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
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

**Decision**: TBD

**Consequences**:
- Add `ics` to requirements.txt
- Generate ICS on-demand for each request (or cache with TTL)

---

## [DEC-009] Home Assistant Integration Update Interval

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
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

**Decision**: TBD

**Consequences**:
- More frequent polling = higher CPU/network usage
- Less frequent = delayed dashboard updates

---

## [DEC-010] Chore Recurrence Pattern Storage

**Status**: Proposed
**Date**: 2025-11-11
**Decider**: TBD
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

**Decision**: TBD

**Consequences**:
- Need JSON schema for validation
- UI must parse JSON to show user-friendly format

---

## Pending Decisions

These need to be made before starting implementation:
- [ ] DEC-001: Web Framework (FastAPI vs Flask)
- [ ] DEC-002: Frontend Framework (Jinja+HTMX vs React)
- [ ] DEC-003: ORM vs Raw SQL
- [ ] DEC-004: Authentication Strategy

These can be decided during implementation:
- [ ] DEC-005: Database Migrations (depends on DEC-003)
- [ ] DEC-006: Task Scheduling
- [ ] DEC-007: Notification System
- [ ] DEC-008: Calendar ICS Generation
- [ ] DEC-009: Integration Update Interval
- [ ] DEC-010: Recurrence Pattern Storage

---

**Last Updated**: 2025-11-11
