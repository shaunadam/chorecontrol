# ChoreControl Architecture

This document provides a comprehensive overview of the ChoreControl system architecture, technology decisions, and business logic.

## Overview

ChoreControl is a Home Assistant integrated chore management system designed to help families track chores, manage points, and reward kids for their work. The system consists of two main components:

1. **Add-on (Backend Service)**: Flask-based REST API and web UI
2. **Integration (Custom Component)**: Home Assistant integration that bridges HA and the add-on

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│           Home Assistant Instance                   │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │  ChoreControl Integration (Custom Component)│    │
│  │  - Entities (sensors, buttons)             │    │
│  │  - Services for automations                │    │
│  │  - REST API client                         │    │
│  │  - User role mapping                       │    │
│  └──────────────┬─────────────────────────────┘    │
│                 │                                    │
│                 │ REST API                           │
│                 │                                    │
│  ┌──────────────▼─────────────────────────────┐    │
│  │  ChoreControl Add-on (Docker Container)    │    │
│  │  ┌──────────────────────────────────────┐  │    │
│  │  │  Flask Web Application               │  │    │
│  │  │  - REST API endpoints                │  │    │
│  │  │  - Web UI (admin interface)          │  │    │
│  │  │  - ICS calendar generation           │  │    │
│  │  │  - Business logic                    │  │    │
│  │  └────────────┬─────────────────────────┘  │    │
│  │               │                             │    │
│  │  ┌────────────▼─────────────────────────┐  │    │
│  │  │  SQLite Database                     │  │    │
│  │  │  - Persistent storage                │  │    │
│  │  │  - Proper relational structure       │  │    │
│  │  └──────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │  HA Ingress (Sidebar Access)                │   │
│  │  - Secure remote access                     │   │
│  │  - HA authentication                        │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Technology Decisions

### Web Framework: Flask

**Decision**: Flask over FastAPI

**Rationale**:
- Developer familiarity and simpler learning curve
- Extensive ecosystem and examples
- Mature and stable for production use
- Flask 2.0+ supports async if needed later

**Consequences**:
- Sync by default (adequate for expected load)
- Manual API documentation (can use flask-swagger)
- SQLAlchemy works seamlessly with Flask-SQLAlchemy

### Frontend: Jinja2 + Vanilla JS

**Decision**: Server-rendered templates with vanilla JavaScript

**Rationale**:
- No build step = easier for contributors
- Simpler Docker image and deployment
- Progressive enhancement

**Consequences**:
- Templates in `templates/` directory
- Static files in `static/` directory
- Mobile-first CSS with responsive design

### ORM: SQLAlchemy

**Decision**: SQLAlchemy ORM over raw SQL

**Rationale**:
- Better for schema evolution (migrations with Alembic)
- Type hints and IDE support for models
- Relationship handling (foreign keys, joins) is easier
- Worth the investment for maintainability

**Consequences**:
- Models defined as Python classes in `models.py`
- Query syntax: `User.query.filter_by(role='parent').all()`
- Enables Flask-Migrate for database migrations

### Authentication: Trust HA Ingress

**Decision**: Trust Home Assistant ingress headers for Phase 1

**Rationale**:
- Simplest path to MVP
- HA ingress provides auth via user session
- Extract HA user ID from `X-Ingress-User` header

**Consequences**:
- Add-on only accessible via HA (perfect for MVP)
- No external API access initially
- Simple middleware to extract user from headers

### Background Jobs: APScheduler

**Decision**: APScheduler with SQLite jobstore

**Rationale**:
- Lightweight, no extra services needed
- Persistent across restarts
- Good enough for low-frequency tasks

**Consequences**:
- Jobs persist across container restarts
- Thread-safe database sessions required
- Jobs defined in `scheduler.py` module

### Notifications: Webhook to HA Event Bus

**Decision**: Push events to HA event bus via webhooks

**Rationale**:
- Real-time notifications, no polling delay
- Reduces unnecessary API polling
- Integration listens to custom event types

**Consequences**:
- Add-on needs HA Supervisor API access
- Post events to HA event bus
- Event types: `chorecontrol_chore_claimed`, etc.

### Recurrence Patterns: JSON in TEXT column

**Decision**: Store patterns as JSON in TEXT column

**Rationale**:
- SQLite handles JSON queries well
- Easy to add new pattern types
- Validate in application layer

**Consequences**:
- Validate with jsonschema library
- Parse in Python for scheduling logic
- Form UI converts to/from JSON

---

## Component Details

### Add-on (Backend Service)

**Technology Stack**:

- **Language**: Python 3.11+
- **Framework**: Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Migrations**: Alembic (via Flask-Migrate)
- **Task Scheduling**: APScheduler
- **Frontend**: Jinja2 templates + vanilla JS
- **Deployment**: Docker container

**Key Modules**:

- `app.py`: Main Flask application setup
- `models.py`: SQLAlchemy database models
- `routes/`: API endpoint handlers
- `utils/`: Business logic (recurrence, instance generator, webhooks)
- `jobs/`: Background job implementations
- `templates/`: Jinja2 HTML templates
- `static/`: CSS, JavaScript

### Integration (Custom Component)

**Technology Stack**:

- **Language**: Python 3.11+ (HA compatible)
- **Framework**: Home Assistant custom component structure
- **HTTP Client**: aiohttp (async)

**Key Modules**:

- `__init__.py`: Integration setup and entry point
- `config_flow.py`: UI configuration flow
- `coordinator.py`: Data update coordinator
- `sensor.py`: Sensor entity platform
- `button.py`: Button entity platform
- `api_client.py`: REST API client class

---

## Database Schema

**Core Tables**:

- `users`: Parent, kid, and system accounts
- `chores`: Chore definitions with recurrence patterns
- `chore_assignments`: Which chores are assigned to which users
- `chore_instances`: Individual chore occurrences with status
- `rewards`: Available rewards with point costs
- `reward_claims`: History of claimed rewards
- `points_history`: Complete audit trail of point changes

**Key Fields Added for Business Logic**:

```python
# ChoreInstance
assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
claimed_late = db.Column(db.Boolean, default=False)

# Chore
allow_late_claims = db.Column(db.Boolean, default=False)
late_points = db.Column(db.Integer, nullable=True)

# Reward
requires_approval = db.Column(db.Boolean, default=False)

# RewardClaim
expires_at = db.Column(db.DateTime, nullable=True)
```

---

## Business Logic

### Chore Instance Lifecycle

**Status Values**:
- `assigned` - Waiting to be claimed by kid
- `claimed` - Kid has claimed, awaiting parent approval
- `approved` - Parent approved, points awarded
- `rejected` - Parent rejected, no points awarded
- `missed` - Past due_date and cannot be claimed

**State Machine**:

```
                    ┌─────────┐
                    │assigned │
                    └────┬────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    (kid claims)    (late claims     (late claims
                       allowed)        disabled)
         │               │               │
         v               v               v
    ┌────────┐      ┌─────────┐     ┌────────┐
    │claimed │      │assigned │     │missed  │
    └───┬────┘      └────┬────┘     └────────┘
        │                │
        │          (kid claims,
        │           marked late)
        │                │
        └───────┬────────┘
                │
         ┌──────▼──────┐
         │             │
         v             v
    ┌─────────┐  ┌──────────┐
    │approved │  │rejected  │
    └─────────┘  └─────────┘
```

### Recurrence Patterns

**Daily**:
```json
{"type": "daily"}
```

**Weekly**:
```json
{"type": "weekly", "days_of_week": [0, 2, 4]}
```
- 0=Sunday through 6=Saturday

**Monthly**:
```json
{"type": "monthly", "days_of_month": [1, 15]}
```
- Edge case: Feb 30 → uses Feb 28/29

**One-Off**:
```json
{"type": "none"}
```
- If `start_date` set: due on that date
- If `start_date` NULL: claimable anytime

### Instance Generation

**Look-Ahead Window**: Generate instances through end of (current month + 2 months)

**For Individual Chores**: One instance per assigned kid per due date
**For Shared Chores**: One instance total per due date (first come, first served)

### Points Calculation

**On-time completion**: Award `chore.points`
**Late completion**: Award `chore.late_points` if set, otherwise `chore.points`
**Parent override**: Optional `points` parameter at approval time

### Reward Workflow

**Auto-approve rewards** (`requires_approval=False`):
- Points deducted immediately
- Status = 'approved'

**Approval-required rewards** (`requires_approval=True`):
- Points deducted immediately (optimistic)
- Status = 'pending'
- Expires after 7 days (auto-reject, refund points)

---

## Background Tasks (APScheduler)

### 1. Daily Instance Generator
**Schedule**: Every day at 00:00

Generates missing chore instances through the look-ahead window.

### 2. Auto-Approval Checker
**Schedule**: Every 5 minutes

Auto-approves claimed instances that have exceeded `auto_approve_after_hours`.

### 3. Missed Instance Marker
**Schedule**: Every hour at :30

Transitions overdue assigned instances to 'missed' status (if `allow_late_claims=False`).

### 4. Pending Reward Expiration
**Schedule**: Every day at 00:01

Auto-rejects pending reward claims after 7 days, refunds points.

### 5. Points Balance Audit
**Schedule**: Every day at 02:00

Verifies all users' points match their transaction history.

---

## Webhook Events

All events follow this structure:
```json
{
  "event": "event_name",
  "timestamp": "2025-01-15T14:30:00Z",
  "data": { /* event-specific data */ }
}
```

### Event Types

1. **chore_instance_created** - New instance created (due today or NULL)
2. **chore_instance_claimed** - Kid claims a chore
3. **chore_instance_approved** - Parent approves (or auto-approval)
4. **chore_instance_rejected** - Parent rejects
5. **points_awarded** - Any point change
6. **reward_claimed** - Kid claims a reward
7. **reward_approved** - Parent approves reward claim
8. **reward_rejected** - Parent rejects or claim expires

---

## Authentication and Authorization

**Add-on Authentication**:
- Uses Home Assistant ingress headers (`X-Ingress-User`)
- Trusts HA to authenticate users

**Role-Based Access Control**:
- `parent`: Create/edit chores, approve, manage rewards, adjust points
- `kid`: View assigned chores, claim chores, claim rewards
- `system`: Background job operations

---

## Data Flow Examples

### Kid Claims Chore

```
1. Kid clicks "Claim" button on HA dashboard
2. HA integration calls service chorecontrol.claim_chore
3. Integration makes POST request to /api/instances/{id}/claim
4. Add-on updates database (status = 'claimed')
5. Add-on fires webhook (chore_instance_claimed)
6. Integration receives event, triggers HA notification
7. Parent receives mobile notification
8. Integration polls API, updates sensor entities
9. Dashboard shows "Pending Approval"
```

### Recurring Chore Generation

```
1. APScheduler triggers daily at midnight
2. Instance generator queries all active recurring chores
3. For each chore, calculate instances based on recurrence pattern
4. Create chore_instance records for upcoming dates
5. Fire webhooks for instances due today
6. HA integration polls and updates entities
7. New chores appear in kid dashboards
```

---

## Deployment Architecture

**Docker Container**:

```dockerfile
FROM python:3.11-alpine
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
CMD ["sh", "run.sh"]
```

**Volume Mounts**:
- `/data`: Database and persistent storage

**Environment Variables**:
- `DATABASE_URL`: SQLite database path
- `LOG_LEVEL`: Logging verbosity
- `SECRET_KEY`: Flask secret key
- `HA_WEBHOOK_URL`: Home Assistant webhook endpoint

---

## Security Considerations

**Current Implementation**:
- Trust Home Assistant ingress authentication
- SQL injection prevention via SQLAlchemy ORM
- Input validation on all API endpoints
- Role-based access control

**Future Enhancements**:
- Optional API key for external access
- Audit logging for all actions
- Rate limiting on API endpoints

---

## Scalability Considerations

**Current Design (Phase 1)**:
- Single add-on instance per HA installation
- SQLite for simplicity
- Expected load: 1-10 users (family size)

**Future Scalability (Phase 2+)**:
- Support for PostgreSQL/MySQL
- Redis for caching
- Separate worker processes for background tasks

---

## Related Documentation

- [PROJECT_PLAN.md](../PROJECT_PLAN.md) - Full data model schema, API endpoints, UX flows
- [NEXT_STEPS.md](../NEXT_STEPS.md) - Current implementation progress
- [api-reference.md](api-reference.md) - API endpoint documentation

---

**Last Updated**: 2025-11-21
