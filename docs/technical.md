# ChoreControl Technical Reference

Developer and AI agent reference for ChoreControl architecture, API, and development.

## Table of Contents

- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Integration Development](#integration-development)
- [Development Setup](#development-setup)

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Home Assistant Instance                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ChoreControl Integration (Custom Component)          │   │
│  │  - Entities (sensors, buttons, calendar)              │   │
│  │  - Services for automations                           │   │
│  │  - REST API client                                    │   │
│  └────────────────────┬─────────────────────────────────┘   │
│                       │ REST API                             │
│  ┌────────────────────▼─────────────────────────────────┐   │
│  │  ChoreControl Add-on (Docker Container)               │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  Flask Web Application (port 8099)             │  │   │
│  │  │  - REST API endpoints                          │  │   │
│  │  │  - Web UI (parent administration)              │  │   │
│  │  │  - Business logic                              │  │   │
│  │  └────────────────────┬───────────────────────────┘  │   │
│  │  ┌────────────────────▼───────────────────────────┐  │   │
│  │  │  SQLite Database (/data/chorecontrol.db)       │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  HA Ingress (Sidebar Access + Authentication)         │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Add-on (Backend)**
- Python 3.11+
- Flask with SQLAlchemy ORM
- SQLite database
- APScheduler for background jobs
- Alembic (Flask-Migrate) for migrations
- Jinja2 + vanilla JS (web UI)

**Integration (Custom Component)**
- Python 3.11+ (HA compatible)
- aiohttp for async HTTP
- DataUpdateCoordinator pattern

### Key Files

**Add-on:**
- `chorecontrol/app.py` - Flask application setup
- `chorecontrol/models.py` - SQLAlchemy database models
- `chorecontrol/routes/` - API endpoint handlers
- `chorecontrol/utils/` - Business logic (recurrence, webhooks)
- `chorecontrol/jobs/` - Background job implementations

**Integration:**
- `custom_components/chorecontrol/__init__.py` - Entry point, services, webhooks
- `custom_components/chorecontrol/coordinator.py` - Data update coordinator
- `custom_components/chorecontrol/sensor.py` - Sensor entities
- `custom_components/chorecontrol/button.py` - Claim button entities
- `custom_components/chorecontrol/calendar.py` - Calendar entity
- `custom_components/chorecontrol/api_client.py` - REST API client

---

## API Reference

### Base URL

- Local development: `http://localhost:8099/api`
- HA Add-on: `http://chorecontrol/api`

### Authentication

Uses Home Assistant ingress headers:
- `X-Ingress-User`: HA user ID
- `Authorization: Bearer <token>` (for integration)

### Response Format

**Success:**
```json
{
  "data": { ... },
  "message": "Operation description"
}
```

**Error:**
```json
{
  "error": "ErrorType",
  "message": "Error description"
}
```

### Endpoints

#### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with DB status |

#### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List users (filter: `role`) |
| POST | `/api/users` | Create user |
| GET | `/api/users/{id}` | Get user details |
| PUT | `/api/users/{id}` | Update user |
| DELETE | `/api/users/{id}` | Delete user |
| GET | `/api/users/{id}/points` | Get points balance/history |

#### Chores
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chores` | List chores (filter: `active`, `assigned_to`) |
| POST | `/api/chores` | Create chore |
| GET | `/api/chores/{id}` | Get chore details |
| PUT | `/api/chores/{id}` | Update chore |
| DELETE | `/api/chores/{id}` | Soft delete chore |
| GET | `/api/chores/{id}/instances` | Get instances for chore |

#### Chore Instances
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/instances` | List instances (filter: `status`, `user_id`, `due_date`) |
| GET | `/api/instances/{id}` | Get instance details |
| GET | `/api/instances/due-today` | Get today's instances |
| POST | `/api/instances/{id}/claim` | Claim chore |
| POST | `/api/instances/{id}/approve` | Approve chore |
| POST | `/api/instances/{id}/reject` | Reject chore |
| POST | `/api/instances/{id}/unclaim` | Unclaim chore |
| POST | `/api/instances/{id}/reassign` | Reassign chore |

#### Rewards
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rewards` | List rewards |
| POST | `/api/rewards` | Create reward |
| GET | `/api/rewards/{id}` | Get reward details |
| PUT | `/api/rewards/{id}` | Update reward |
| DELETE | `/api/rewards/{id}` | Soft delete reward |
| POST | `/api/rewards/{id}/claim` | Claim reward |
| GET | `/api/rewards/claims` | List reward claims (filter: `status`, `user_id`) |
| GET | `/api/rewards/claims/history` | Get approved/rejected claims |
| POST | `/api/rewards/claims/{id}/unclaim` | Unclaim pending reward |
| POST | `/api/rewards/claims/{id}/approve` | Approve claim |
| POST | `/api/rewards/claims/{id}/reject` | Reject claim |

#### Points
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/points/adjust` | Manual point adjustment |
| GET | `/api/points/history/{user_id}` | Get points history |

### Webhook Events

Events fired to HA event bus:

| Event | When Fired |
|-------|------------|
| `chore_instance_created` | New instance created |
| `chore_instance_claimed` | Kid claims chore |
| `chore_instance_approved` | Chore approved |
| `chore_instance_rejected` | Chore rejected |
| `points_awarded` | Points change |
| `reward_claimed` | Kid claims reward |
| `reward_approved` | Reward approved |
| `reward_rejected` | Reward rejected |

---

## Database Schema

### Core Tables

**users**
```
id, ha_user_id (unique), username, role, points, password_hash, created_at, updated_at
```
Roles: `parent`, `kid`, `system`, `unmapped`, `claim_only`

**chores**
```
id, name, description, points, recurrence_type, recurrence_pattern (JSON),
start_date, end_date, assignment_type, requires_approval,
auto_approve_after_hours, allow_late_claims, late_points,
created_by (FK), is_active, created_at, updated_at
```

**chore_assignments**
```
id, chore_id (FK), user_id (FK), due_date
Unique: (chore_id, user_id, due_date)
```

**chore_instances**
```
id, chore_id (FK), due_date, assigned_to (FK),
status (assigned/claimed/approved/rejected/missed),
claimed_by (FK), claimed_at, claimed_late,
approved_by (FK), approved_at,
rejected_by (FK), rejected_at, rejection_reason,
points_awarded, created_at, updated_at
```

**rewards**
```
id, name, description, points_cost, cooldown_days,
max_claims_total, max_claims_per_kid, requires_approval,
is_active, created_at, updated_at
```

**reward_claims**
```
id, reward_id (FK), user_id (FK), points_spent,
claimed_at, expires_at, status (pending/approved/rejected),
approved_by (FK), approved_at
```

**points_history**
```
id, user_id (FK), points_delta, reason,
chore_instance_id (FK), reward_claim_id (FK),
created_by (FK), created_at
```

### Chore Instance Lifecycle

```
assigned → claimed → approved (points awarded)
                  → rejected (no points, can reclaim)
         → missed (if late claims disabled)
```

### Recurrence Patterns (JSON)

**Daily:** `{"type": "daily"}`

**Weekly:** `{"type": "weekly", "days_of_week": [0, 2, 4]}` (0=Sunday)

**Monthly:** `{"type": "monthly", "days_of_month": [1, 15]}`

**One-off:** `{"type": "none"}`

---

## Integration Development

### Entity Reference

**Global Sensors:**
- `sensor.chorecontrol_pending_approvals`
- `sensor.chorecontrol_pending_reward_approvals`
- `sensor.chorecontrol_total_kids`
- `sensor.chorecontrol_active_chores`

**Per-Kid Sensors (7 per kid):**
- `sensor.chorecontrol_{username}_points`
- `sensor.chorecontrol_{username}_pending_chores`
- `sensor.chorecontrol_{username}_claimed_chores`
- `sensor.chorecontrol_{username}_completed_today`
- `sensor.chorecontrol_{username}_completed_this_week`
- `sensor.chorecontrol_{username}_chores_due_today`
- `sensor.chorecontrol_{username}_pending_reward_claims`

**Buttons:** `button.chorecontrol_claim_{chore}_{username}`

**Calendar:** `calendar.chorecontrol_chores`

**Binary Sensor:** `binary_sensor.chorecontrol_api_connected`

### Services

| Service | Parameters |
|---------|------------|
| `claim_chore` | `chore_instance_id`, `user_id` |
| `approve_chore` | `chore_instance_id`, `approver_user_id`, `points` (optional) |
| `reject_chore` | `chore_instance_id`, `approver_user_id`, `reason` |
| `claim_reward` | `reward_id`, `user_id` |
| `approve_reward` | `claim_id`, `approver_user_id` |
| `reject_reward` | `claim_id`, `approver_user_id`, `reason` |
| `adjust_points` | `user_id`, `points_delta`, `reason` |
| `refresh_data` | (none) |

### Event Data Structure

**chore_instance_claimed:**
```yaml
instance_id: 123
chore_id: 45
chore_name: "Take out trash"
claimed_by: 2  # user_id
claimed_by_name: "Emma"
```

**reward_claimed:**
```yaml
claim_id: 78
reward_id: 12
reward_name: "Ice cream"
user_id: 2
user_name: "Emma"
points_spent: 25
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js (optional, for frontend tooling)
- Home Assistant dev environment (for integration testing)

### Running the Add-on Locally

```bash
cd chorecontrol

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
export FLASK_APP=app.py
flask db upgrade

# Run development server
python app.py
```

Access at `http://localhost:8099`

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
PYTHONPATH=. python -m pytest

# Run with coverage
PYTHONPATH=. python -m pytest --cov=chorecontrol --cov-report=html
```

### Database Migrations

```bash
# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

### Database Seeding (Development)

```bash
python seed_data.py
```

Creates test users, chores, rewards, and instances.

### Code Style

- Python: Follow PEP 8, use type hints
- Use `black` for formatting
- Use `ruff` for linting

### Background Jobs (APScheduler)

| Job | Schedule | Purpose |
|-----|----------|---------|
| Instance Generator | Daily 00:00 | Generate upcoming chore instances |
| Auto-Approval | Every 5 min | Auto-approve old claims |
| Missed Instance Marker | Hourly :30 | Mark overdue as missed |
| Reward Expiration | Daily 00:01 | Expire pending claims |
| Points Audit | Daily 02:00 | Verify point balances |

---

## Project Structure

```
chorecontrol/
├── chorecontrol/          # Add-on source
│   ├── app.py             # Flask app setup
│   ├── models.py          # Database models
│   ├── routes/            # API endpoints
│   ├── utils/             # Business logic
│   ├── jobs/              # Background tasks
│   ├── templates/         # Jinja2 templates
│   └── static/            # CSS, JS
├── custom_components/
│   └── chorecontrol/      # HA Integration
│       ├── __init__.py    # Setup, services
│       ├── coordinator.py # Data coordinator
│       ├── sensor.py      # Sensors
│       ├── button.py      # Buttons
│       ├── calendar.py    # Calendar
│       └── api_client.py  # API client
├── docs/                  # Documentation
├── tests/                 # Test suite
├── BACKLOG.md             # Feature backlog
├── CHANGELOG.md           # Version history
└── README.md              # Project overview
```

---

## Support

- **Issues**: [GitHub Issues](https://github.com/shaunadam/chorecontrol/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shaunadam/chorecontrol/discussions)
