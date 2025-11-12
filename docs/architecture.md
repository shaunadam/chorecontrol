# ChoreControl Architecture

This document provides an overview of the ChoreControl system architecture.

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

## Component Details

### Add-on (Backend Service)

**Technology Stack**:

- **Language**: Python 3.11+
- **Framework**: Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Migrations**: Alembic (via Flask-Migrate)
- **Task Scheduling**: APScheduler
- **Frontend**: Jinja2 templates + HTMX
- **Deployment**: Docker container

**Responsibilities**:

- Provide REST API for all CRUD operations
- Implement business logic (scheduling, points, notifications)
- Serve web UI for administration
- Generate ICS calendar feeds
- Manage database schema and migrations
- Run background tasks (chore generation, auto-approval)

**Key Modules**:

- `app.py`: Main Flask application setup
- `models.py`: SQLAlchemy database models
- `routes/`: API endpoint handlers
- `services/`: Business logic (scheduler, points manager, etc.)
- `templates/`: Jinja2 HTML templates
- `static/`: CSS, JavaScript, images

### Integration (Custom Component)

**Technology Stack**:

- **Language**: Python 3.11+ (HA compatible)
- **Framework**: Home Assistant custom component structure
- **HTTP Client**: aiohttp (async)

**Responsibilities**:

- Communicate with add-on REST API
- Expose HA entities (sensors, buttons)
- Provide HA services for automations
- Map HA users to parent/kid roles
- Handle HA notifications via event bus
- Poll add-on for entity state updates

**Key Modules**:

- `__init__.py`: Integration setup and entry point
- `config_flow.py`: UI configuration flow
- `coordinator.py`: Data update coordinator
- `sensor.py`: Sensor entity platform
- `button.py`: Button entity platform
- `api_client.py`: REST API client class

### Database Schema

For detailed database schema, see [PROJECT_PLAN.md - Data Model](../PROJECT_PLAN.md#data-model).

**Core Tables**:

- `users`: Parent and kid accounts
- `chores`: Chore definitions with recurrence patterns
- `chore_assignments`: Which chores are assigned to which users
- `chore_instances`: Individual chore occurrences with status
- `rewards`: Available rewards with point costs
- `reward_claims`: History of claimed rewards
- `points_history`: Complete audit trail of point changes

**Key Relationships**:

- Users have many chore instances (assigned, claimed)
- Chores have many chore instances (generated from recurrence)
- Users have many reward claims
- Points history references chore instances and reward claims

## Data Flow Examples

### Example 1: Kid Claims Chore

```
1. Kid clicks "Claim" button on HA dashboard
   ↓
2. HA integration calls service chorecontrol.claim_chore
   ↓
3. Integration makes POST request to /api/instances/{id}/claim
   ↓
4. Add-on updates database (status = 'claimed')
   ↓
5. Add-on fires event to HA event bus (chorecontrol_chore_claimed)
   ↓
6. Integration receives event, triggers HA notification
   ↓
7. Parent receives mobile notification
   ↓
8. Integration polls API, updates sensor entities
   ↓
9. Dashboard shows updated status ("Pending Approval")
```

### Example 2: Recurring Chore Generation

```
1. APScheduler triggers daily at midnight
   ↓
2. Chore scheduler service runs
   ↓
3. Query all active recurring chores
   ↓
4. For each chore, calculate next instances based on recurrence pattern
   ↓
5. Create new chore_instance records for upcoming dates
   ↓
6. Create chore_assignment records linking instances to users
   ↓
7. HA integration polls and updates entities
   ↓
8. New chores appear in kid dashboards
```

## Authentication and Authorization

**Add-on Authentication**:

- Uses Home Assistant ingress headers (`X-Ingress-User`)
- No separate authentication required
- Trusts HA to authenticate users

**Role-Based Access Control**:

- Users are mapped to roles: `parent` or `kid`
- Parents can: create/edit chores, approve chores, manage rewards, adjust points
- Kids can: view assigned chores, claim chores, claim rewards

**Implementation**:

```python
def require_role(role):
    """Decorator to enforce role-based access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_current_user_id()  # From ingress header
            user = User.query.get(user_id)
            if user.role != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/api/chores', methods=['POST'])
@require_role('parent')
def create_chore():
    # Only parents can create chores
    pass
```

## Scheduling and Background Tasks

**APScheduler Jobs**:

1. **Daily Chore Generation** (runs at midnight):
   - Generate chore instances for recurring chores
   - Create instances for next 7-30 days

2. **Auto-Approval Check** (runs every hour):
   - Find chores with auto_approve_after_hours set
   - Auto-approve if timeout has passed
   - Award points and send notifications

3. **Cleanup Old Data** (runs weekly):
   - Archive old chore instances (optional)
   - Clean up expired sessions

**Configuration**:

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    func=generate_chore_instances,
    trigger='cron',
    hour=0,
    minute=0
)
scheduler.start()
```

## Notification System

**Event-Based Notifications**:

- Add-on fires events to HA event bus via Supervisor API
- Integration listens for `chorecontrol_*` events
- Integration triggers HA notify service

**Event Types**:

- `chorecontrol_chore_claimed`: Kid claims chore
- `chorecontrol_chore_approved`: Parent approves chore
- `chorecontrol_chore_rejected`: Parent rejects chore
- `chorecontrol_reward_claimed`: Kid claims reward
- `chorecontrol_points_adjusted`: Manual point adjustment

**Implementation**:

```python
# Add-on fires event
requests.post(
    'http://supervisor/core/api/events/chorecontrol_chore_claimed',
    json={
        'chore_id': 1,
        'user_id': 1,
        'chore_name': 'Take out trash'
    }
)

# Integration listens for event
async def async_setup_entry(hass, entry):
    hass.bus.async_listen(
        'chorecontrol_chore_claimed',
        handle_chore_claimed
    )
```

## Calendar Integration

**ICS Feed Generation**:

- Add-on exposes `/api/calendar/{user_id}.ics` endpoint
- Generates standard ICS format with upcoming chores
- HA calendar integration subscribes to URL
- Chores appear in HA calendar alongside other events

**ICS Format**:

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ChoreControl//EN
BEGIN:VEVENT
UID:chore-instance-1@chorecontrol
DTSTART:20251111
SUMMARY:Take out trash (5 points)
DESCRIPTION:Roll both bins to curb
STATUS:TENTATIVE
END:VEVENT
END:VCALENDAR
```

## Deployment Architecture

**Docker Container**:

```dockerfile
FROM python:3.11-alpine

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Run migrations and start app
CMD ["sh", "run.sh"]
```

**Volume Mounts**:

- `/data`: Database and persistent storage
- `/config`: Configuration files (if needed)

**Environment Variables**:

- `DATABASE_URL`: SQLite database path
- `LOG_LEVEL`: Logging verbosity
- `SECRET_KEY`: Flask secret key

## Scalability Considerations

**Current Design (Phase 1)**:

- Single add-on instance per HA installation
- SQLite for simplicity
- Expected load: 1-10 users (family size)
- No external dependencies

**Future Scalability (Phase 2+)**:

- Support for PostgreSQL/MySQL for larger deployments
- Redis for caching and session management
- Horizontal scaling with load balancer
- Separate worker processes for background tasks

## Security Considerations

**Current Implementation**:

- Trust Home Assistant ingress authentication
- No sensitive data stored (it's chore data)
- SQL injection prevention via SQLAlchemy ORM
- Input validation on all API endpoints

**Future Enhancements**:

- Optional API key for external access
- Encrypted database (if storing sensitive rewards)
- Audit logging for all actions
- Rate limiting on API endpoints

## Monitoring and Logging

**Logging**:

- Flask logs to stdout (captured by Docker)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Structured logging for easier parsing

**Health Checks**:

- `/health` endpoint checks database connectivity
- HA integration reports API connectivity via binary sensor

**Metrics** (Future):

- Track API response times
- Monitor database query performance
- Count of chores completed per day/week
- User engagement metrics

## Complete Architecture Documentation

For complete architectural details including:

- Full data model schema
- API endpoint specifications
- User experience flows
- Phase 1 MVP implementation plan
- Development principles

See [PROJECT_PLAN.md](../PROJECT_PLAN.md)

## Technology Decisions

For detailed rationale on technology choices including:

- Why Flask over FastAPI
- Why SQLAlchemy ORM
- Why APScheduler for background jobs
- Why event-based notifications

See [DECISIONS.md](../DECISIONS.md)

## Implementation Roadmap

For current development priorities and parallel work streams:

See [NEXT_STEPS.md](../NEXT_STEPS.md)

---

**Questions about the architecture?** Open a [discussion](https://github.com/shaunadam/chorecontrol/discussions) or [issue](https://github.com/shaunadam/chorecontrol/issues)!
