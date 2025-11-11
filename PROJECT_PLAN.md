# ChoreControl - Home Assistant Chore Management System
## Project Plan & Requirements

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Data Model](#data-model)
5. [Component Breakdown](#component-breakdown)
6. [User Experience Flows](#user-experience-flows)
7. [Phase 1: MVP](#phase-1-mvp)
8. [Phase 2+: Future Features](#phase-2-future-features)
9. [Open Questions & Decisions](#open-questions--decisions)

---

## Project Overview

### Goals
- Create a full-featured chore management system integrated with Home Assistant
- Support multiple kids and parents with role-based access
- Provide scheduling, points, rewards, and approval workflows
- Mobile-first admin interface with HA dashboard integration
- Proper data structure and persistence (avoiding entity-based storage issues)

### Success Criteria
- Parents can manage chores, kids, and rewards through HA sidebar interface
- Kids can view assigned chores and claim completion via HA dashboard
- Approval workflow with notifications
- Calendar integration showing upcoming chores
- Points and rewards system working end-to-end

### Comparisons & Inspiration
- **kidschores-ha**: Reference for features, but avoid entity-based storage issues
- **Skylight Chore Chart**: UI/UX inspiration for chore management

---

## Architecture

### High-Level Architecture

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
│  │  │  Flask/FastAPI Web Application       │  │    │
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

### Component Responsibilities

#### Add-on (Backend Service)
- **Purpose**: Core application and data management
- **Tech**: Flask/FastAPI + SQLite
- **Responsibilities**:
  - REST API for all CRUD operations
  - Business logic (scheduling, points calculation, notifications)
  - Web UI for parent administration
  - ICS calendar feed generation
  - Database management
- **Access**: HA sidebar via ingress

#### Integration (Custom Component)
- **Purpose**: Bridge between HA and add-on
- **Tech**: Python (HA custom component)
- **Responsibilities**:
  - Communicate with add-on REST API
  - Expose HA entities (sensors, buttons, switches)
  - Provide HA services for automations
  - Map HA users to parent/kid roles
  - Handle HA notifications
- **Access**: Configured via HA UI

#### Dashboard/UI
- **Purpose**: User-facing displays
- **Tech**: HA Lovelace dashboards (standard cards initially)
- **Responsibilities**:
  - Kid view: See assigned chores, claim completion
  - Parent view: Quick approvals, points overview
  - Use integration entities for display
- **Future**: Custom Lovelace card if needed

---

## Technology Stack

### Add-on
- **Language**: Python 3.11+
- **Framework**: FastAPI (async, auto-docs, modern) OR Flask (simpler, proven)
- **Database**: SQLite3 with proper schema
- **ORM**: SQLAlchemy (optional but recommended)
- **Frontend**: Jinja2 templates + HTMX (lightweight, no build step) OR simple React/Vue
- **Container**: Docker (Alpine-based for size)

### Integration
- **Language**: Python 3.11+ (HA compatible)
- **Framework**: Home Assistant custom component structure
- **HTTP Client**: aiohttp (async)
- **Dependencies**: Minimal (requests/aiohttp only)

### Development Tools
- **Version Control**: Git
- **Testing**: pytest, pytest-homeassistant-custom-component
- **Linting**: ruff, black, mypy
- **Documentation**: Markdown, OpenAPI for API docs

---

## Data Model

### Core Entities

#### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ha_user_id TEXT UNIQUE NOT NULL,  -- Home Assistant user ID
    username TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('parent', 'kid')),
    points INTEGER DEFAULT 0,  -- Only used for kids
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Chores Table
```sql
CREATE TABLE chores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    points INTEGER NOT NULL DEFAULT 0,

    -- Scheduling
    recurrence_type TEXT CHECK(recurrence_type IN ('none', 'simple', 'complex')),
    recurrence_pattern TEXT,  -- JSON for complex patterns
    start_date DATE,
    end_date DATE,

    -- Assignment
    assignment_type TEXT CHECK(assignment_type IN ('individual', 'shared')),

    -- Workflow
    requires_approval BOOLEAN DEFAULT TRUE,
    auto_approve_after_hours INTEGER,  -- NULL means no auto-approve

    -- Metadata
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### Chore Assignments Table
```sql
CREATE TABLE chore_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chore_id INTEGER NOT NULL REFERENCES chores(id),
    user_id INTEGER NOT NULL REFERENCES users(id),

    -- For recurring chores, which instance
    due_date DATE,

    UNIQUE(chore_id, user_id, due_date)
);
```

#### Chore Instances Table
```sql
-- Tracks individual completions/claims
CREATE TABLE chore_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chore_id INTEGER NOT NULL REFERENCES chores(id),
    due_date DATE NOT NULL,

    -- Status tracking
    status TEXT CHECK(status IN ('assigned', 'claimed', 'approved', 'rejected')) DEFAULT 'assigned',

    -- Who did what when
    claimed_by INTEGER REFERENCES users(id),
    claimed_at TIMESTAMP,
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    rejected_by INTEGER REFERENCES users(id),
    rejected_at TIMESTAMP,
    rejection_reason TEXT,

    -- Points awarded (may differ from chore.points for bonuses/penalties)
    points_awarded INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Rewards Table
```sql
CREATE TABLE rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    points_cost INTEGER NOT NULL,

    -- Limits
    cooldown_days INTEGER,  -- NULL means no cooldown
    max_claims_total INTEGER,  -- NULL means unlimited
    max_claims_per_kid INTEGER,  -- NULL means unlimited

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Reward Claims Table
```sql
CREATE TABLE reward_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reward_id INTEGER NOT NULL REFERENCES rewards(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    points_spent INTEGER NOT NULL,
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Approval workflow (optional for rewards)
    status TEXT CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'approved',
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP
);
```

#### Points History Table
```sql
CREATE TABLE points_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    points_delta INTEGER NOT NULL,  -- Can be negative
    reason TEXT NOT NULL,

    -- Reference to what caused this change
    chore_instance_id INTEGER REFERENCES chore_instances(id),
    reward_claim_id INTEGER REFERENCES reward_claims(id),

    created_by INTEGER REFERENCES users(id),  -- Who made the change
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Recurrence Patterns
```json
// Simple patterns stored as JSON in chores.recurrence_pattern
{
  "type": "simple",
  "interval": "daily|weekly|monthly",
  "every_n": 1  // Every N days/weeks/months
}

// Complex patterns
{
  "type": "complex",
  "schedule": "cron-like-expression",
  "days_of_week": [1, 3, 5],  // Monday, Wednesday, Friday
  "weeks_of_month": [1, 3],   // First and third week
  "days_of_month": [1, 15]    // 1st and 15th of month
}
```

---

## Component Breakdown

### 1. Add-on: Backend Service

#### 1.1 REST API Endpoints

**Authentication**
- Uses HA ingress auth (user already authenticated by HA)
- Extract HA user ID from headers

**Users**
- `GET /api/users` - List all users
- `POST /api/users` - Create new user (map HA user)
- `GET /api/users/{id}` - Get user details
- `PUT /api/users/{id}` - Update user
- `GET /api/users/{id}/points` - Get points balance and history

**Chores**
- `GET /api/chores` - List all chores (filterable by active, assigned_to)
- `POST /api/chores` - Create new chore
- `GET /api/chores/{id}` - Get chore details
- `PUT /api/chores/{id}` - Update chore
- `DELETE /api/chores/{id}` - Soft delete chore
- `GET /api/chores/{id}/instances` - Get instances for a chore

**Chore Instances**
- `GET /api/instances` - List instances (filterable by status, user, date range)
- `GET /api/instances/{id}` - Get instance details
- `POST /api/instances/{id}/claim` - Kid claims completion
- `POST /api/instances/{id}/approve` - Parent approves
- `POST /api/instances/{id}/reject` - Parent rejects with reason

**Rewards**
- `GET /api/rewards` - List all rewards
- `POST /api/rewards` - Create reward
- `GET /api/rewards/{id}` - Get reward details
- `PUT /api/rewards/{id}` - Update reward
- `DELETE /api/rewards/{id}` - Soft delete reward
- `POST /api/rewards/{id}/claim` - User claims reward

**Points**
- `POST /api/points/adjust` - Manual point adjustment (parent only)
- `GET /api/points/history/{user_id}` - Point history for user

**Calendar**
- `GET /api/calendar/{user_id}.ics` - ICS feed for user's chores

**Dashboard Data**
- `GET /api/dashboard/kid/{user_id}` - Kid's dashboard data
- `GET /api/dashboard/parent` - Parent overview (pending approvals, etc.)

#### 1.2 Web UI Pages

**Setup/Admin (Parent Only)**
- `/` - Dashboard (pending approvals, recent activity)
- `/chores` - Chore management (list, create, edit)
- `/chores/new` - Create chore form
- `/chores/{id}/edit` - Edit chore form
- `/kids` - Kid management
- `/rewards` - Reward management
- `/rewards/new` - Create reward form
- `/points` - Manual points adjustment
- `/settings` - System settings

**Shared Views**
- `/calendar` - Calendar view of all chores
- `/history` - Completion history

**Technical**
- `/health` - Health check endpoint
- `/docs` - API documentation (auto-generated)

#### 1.3 Business Logic

**Chore Scheduler**
- Generate chore instances based on recurrence patterns
- Run daily (or on-demand) to create upcoming instances
- Handle one-off vs recurring chores

**Points Manager**
- Calculate points for completed chores
- Handle bonuses/penalties
- Deduct points for rewards
- Maintain points_history

**Notification Manager**
- Trigger HA notifications via integration callback
- Events: chore_assigned, chore_claimed, chore_approved, chore_rejected, reward_claimed

**Auto-Approval**
- Background task to auto-approve chores after configured hours

### 2. Integration: Custom Component

#### 2.1 Directory Structure
```
custom_components/chorecontrol/
├── __init__.py           # Component setup
├── manifest.json         # Component metadata
├── config_flow.py        # UI configuration
├── const.py              # Constants
├── coordinator.py        # Data update coordinator
├── sensor.py             # Sensor entities
├── button.py             # Button entities
├── services.yaml         # Service definitions
└── api_client.py         # REST API client
```

#### 2.2 Entities to Expose

**Sensor Entities (per kid)**
- `sensor.{kid_name}_points` - Current points balance
- `sensor.{kid_name}_pending_chores` - Count of assigned chores
- `sensor.{kid_name}_claimed_chores` - Count of claimed (pending approval)
- `sensor.{kid_name}_completed_today` - Count completed today
- `sensor.{kid_name}_completed_this_week` - Count completed this week

**Sensor Entities (global)**
- `sensor.chorecontrol_pending_approvals` - Count of chores needing approval
- `sensor.chorecontrol_total_kids` - Number of kids
- `sensor.chorecontrol_active_chores` - Number of active chores

**Button Entities (per kid/chore combination)**
- `button.claim_chore_{chore_id}_{kid_id}` - Quick claim button

**Binary Sensor**
- `binary_sensor.chorecontrol_api_connected` - API health status

#### 2.3 Services

**chorecontrol.claim_chore**
- Parameters: `chore_instance_id`, `user_id`
- Claims a chore as completed

**chorecontrol.approve_chore**
- Parameters: `chore_instance_id`, `approver_user_id`
- Approves a claimed chore

**chorecontrol.reject_chore**
- Parameters: `chore_instance_id`, `approver_user_id`, `reason`
- Rejects a claimed chore

**chorecontrol.adjust_points**
- Parameters: `user_id`, `points_delta`, `reason`
- Manual points adjustment

**chorecontrol.claim_reward**
- Parameters: `reward_id`, `user_id`
- Claims a reward

**chorecontrol.refresh_data**
- Force refresh all entities

#### 2.4 Configuration

**Config Flow (UI)**
- Add-on URL (auto-detect if possible)
- API key (if we implement one)
- Update interval (default: 30 seconds)
- Parent user mapping (which HA users are parents)

#### 2.5 Data Coordinator

- Polls add-on API every 30 seconds (configurable)
- Updates all sensor entities
- Handles API errors gracefully
- Caches data to minimize API calls

### 3. Dashboards

#### 3.1 Kid Dashboard (Non-Parent View)

**Sections**
- **My Points**: Large display of current points
- **My Chores Today**: List of assigned chores for today
  - Status indicator (assigned, claimed, approved)
  - Claim button
  - Points value
- **Upcoming Chores**: Next 7 days
- **Available Rewards**: Grid of rewards with points cost
  - Claim button (disabled if insufficient points)
- **Recent Activity**: Last 5 completed chores

**Technical**
- Uses standard HA cards (entities, button, markdown)
- Optionally use mushroom cards for better UI
- Filter entities by current user

#### 3.2 Parent Dashboard

**Sections**
- **Pending Approvals**: List requiring approval
  - Kid name
  - Chore name
  - Claimed time
  - Approve/Reject buttons
- **Kids Overview**: Grid of kid cards
  - Name
  - Points balance
  - Chores today (completed/total)
  - Quick points adjust
- **Recent Activity**: System-wide activity feed
- **Quick Actions**
  - Link to add-on admin UI
  - Manual points adjustment
  - Create one-off chore

**Technical**
- Custom view with visibility restrictions
- Use conditional cards based on user role
- Service call buttons for approvals

---

## User Experience Flows

### Flow 1: Parent Creates Recurring Chore

1. Parent opens HA sidebar → ChoreControl
2. Clicks "Chores" → "New Chore"
3. Fills form:
   - Name: "Take out trash"
   - Description: "Roll bins to curb"
   - Points: 5
   - Recurrence: Weekly, every Monday
   - Assigned to: [Kid1, Kid2] (individual chores for each)
   - Requires approval: Yes
4. Saves
5. System generates chore instances for next 4 weeks
6. Integration polls and creates sensor entities
7. Kids see "Take out trash" on their dashboard for next Monday

### Flow 2: Kid Completes Chore

1. Kid logs into HA dashboard (kid view)
2. Sees "Take out trash" in "My Chores Today"
3. Completes chore in real life
4. Clicks "Claim" button on dashboard
5. Service `chorecontrol.claim_chore` called
6. Add-on updates instance status to "claimed"
7. Notification sent to parent(s) via HA notify service
8. Kid's dashboard shows chore as "Pending Approval"

### Flow 3: Parent Approves Chore

1. Parent gets mobile notification: "Kid1 claimed 'Take out trash'"
2. Opens HA app → Parent dashboard
3. Sees chore in "Pending Approvals"
4. Clicks "Approve" button
5. Service `chorecontrol.approve_chore` called
6. Add-on:
   - Updates instance status to "approved"
   - Awards 5 points to Kid1
   - Creates points_history entry
   - Updates user points balance
7. Notification sent to Kid1: "Chore approved! +5 points"
8. Kid's dashboard updates to show new points balance

### Flow 4: Kid Claims Reward

1. Kid opens dashboard
2. Sees "Ice cream trip" reward (costs 20 points, has 25 points)
3. Clicks "Claim Reward"
4. Service `chorecontrol.claim_reward` called
5. Add-on:
   - Checks sufficient points: ✓
   - Checks cooldown: ✓
   - Checks claim limits: ✓
   - Creates reward_claim entry
   - Deducts 20 points
   - Creates points_history entry
6. Notification sent to parent(s): "Kid1 claimed 'Ice cream trip'"
7. Kid sees updated points balance (now 5)

### Flow 5: Calendar Integration

1. HA configured with calendar integration
2. Add-on generates ICS feed at `/api/calendar/{kid_id}.ics`
3. HA calendar subscribes to feed
4. Calendar shows all assigned chores with due dates
5. Kid can view calendar on dashboard
6. Calendar events show chore name, points, description

---

## Phase 1: MVP

### Goal
Basic working system: Create chores, assign to kids, claim/approve workflow, points and simple rewards.

### Tasks

#### Project Setup
- [ ] **SETUP-1**: Initialize Git repository structure
- [ ] **SETUP-2**: Create add-on directory structure and Dockerfile
- [ ] **SETUP-3**: Create integration directory structure
- [ ] **SETUP-4**: Set up Python virtual environment and dependencies
- [ ] **SETUP-5**: Configure linting tools (ruff, black, mypy)
- [ ] **SETUP-6**: Create README.md with project overview

#### Add-on: Database Layer
- [ ] **DB-1**: Design and create SQLite schema (all tables from data model)
- [ ] **DB-2**: Write database initialization script
- [ ] **DB-3**: Create SQLAlchemy models (or raw SQL helpers)
- [ ] **DB-4**: Write database migration strategy (for future updates)
- [ ] **DB-5**: Create seed data script for testing

#### Add-on: REST API - Core
- [ ] **API-1**: Set up FastAPI/Flask application structure
- [ ] **API-2**: Implement health check endpoint
- [ ] **API-3**: Implement user endpoints (CRUD)
- [ ] **API-4**: Implement chore endpoints (CRUD)
- [ ] **API-5**: Implement chore instance endpoints (list, get, claim, approve, reject)
- [ ] **API-6**: Implement basic reward endpoints (CRUD, claim)
- [ ] **API-7**: Implement points adjustment endpoint
- [ ] **API-8**: Implement points history endpoint
- [ ] **API-9**: Add API authentication/authorization (check HA user role)
- [ ] **API-10**: Generate OpenAPI documentation

#### Add-on: Business Logic
- [ ] **LOGIC-1**: Implement simple chore scheduler (daily/weekly recurrence)
- [ ] **LOGIC-2**: Implement points calculation and awarding
- [ ] **LOGIC-3**: Implement reward claim validation (points, cooldown, limits)
- [ ] **LOGIC-4**: Implement notification event system (hooks for integration)
- [ ] **LOGIC-5**: Create background task runner for scheduled jobs

#### Add-on: Web UI
- [ ] **UI-1**: Set up Jinja2 templates and static files
- [ ] **UI-2**: Create base layout and navigation
- [ ] **UI-3**: Build chores list page
- [ ] **UI-4**: Build create/edit chore form (simple recurrence only)
- [ ] **UI-5**: Build kids management page
- [ ] **UI-6**: Build rewards management page
- [ ] **UI-7**: Build parent dashboard (pending approvals, overview)
- [ ] **UI-8**: Build points adjustment interface
- [ ] **UI-9**: Make UI mobile-responsive
- [ ] **UI-10**: Add basic styling (CSS framework like Bootstrap/Tailwind)

#### Add-on: Deployment
- [ ] **DEPLOY-1**: Create Dockerfile for add-on
- [ ] **DEPLOY-2**: Create add-on config.json (HA add-on metadata)
- [ ] **DEPLOY-3**: Configure ingress for sidebar access
- [ ] **DEPLOY-4**: Test add-on installation in HA
- [ ] **DEPLOY-5**: Document add-on installation and setup

#### Integration: Core
- [ ] **INT-1**: Create custom component scaffold
- [ ] **INT-2**: Implement manifest.json
- [ ] **INT-3**: Implement config_flow.py (UI setup)
- [ ] **INT-4**: Create REST API client class
- [ ] **INT-5**: Implement data update coordinator
- [ ] **INT-6**: Create sensor platform (points, counts)
- [ ] **INT-7**: Create button platform (claim buttons)
- [ ] **INT-8**: Implement services (claim, approve, reject, adjust_points)
- [ ] **INT-9**: Add error handling and logging
- [ ] **INT-10**: Test integration installation in HA

#### Integration: HA User Mapping
- [ ] **INT-11**: Implement parent/kid role detection
- [ ] **INT-12**: Create user mapping configuration
- [ ] **INT-13**: Filter entities based on current user context

#### Dashboards
- [ ] **DASH-1**: Create example kid dashboard YAML
- [ ] **DASH-2**: Create example parent dashboard YAML
- [ ] **DASH-3**: Document dashboard setup instructions
- [ ] **DASH-4**: Test dashboard with real data

#### Calendar Integration (Simple)
- [ ] **CAL-1**: Implement ICS feed generation for user's chores
- [ ] **CAL-2**: Test ICS feed with HA calendar integration
- [ ] **CAL-3**: Document calendar setup

#### Testing & Documentation
- [ ] **TEST-1**: Write unit tests for API endpoints
- [ ] **TEST-2**: Write unit tests for business logic
- [ ] **TEST-3**: Write integration tests (add-on + integration)
- [ ] **TEST-4**: Perform end-to-end testing (full workflow)
- [ ] **DOC-1**: Write user documentation (setup, usage)
- [ ] **DOC-2**: Write developer documentation (architecture, API)
- [ ] **DOC-3**: Create demo video/screenshots

#### Final MVP Release
- [ ] **RELEASE-1**: Version tagging and release notes
- [ ] **RELEASE-2**: Publish to GitHub
- [ ] **RELEASE-3**: Submit to HA community add-on repository (optional)

---

## Phase 2+: Future Features

### Backlog

#### Scheduling Enhancements
- [ ] **SCHED-1**: Complex recurrence patterns (cron-like)
- [ ] **SCHED-2**: Chore rotation (auto-assign to different kid each week)
- [ ] **SCHED-3**: Seasonal chores (only certain months)
- [ ] **SCHED-4**: Skip holidays or school breaks

#### Workflow Enhancements
- [ ] **WORK-1**: Photo proof of completion (upload image)
- [ ] **WORK-2**: Auto-approval after X hours
- [ ] **WORK-3**: Partial completion (kid worked on it but didn't finish)
- [ ] **WORK-4**: Chore templates/presets (common chores library)

#### Points & Rewards
- [ ] **POINTS-1**: Bonus points for streaks (7 days in a row)
- [ ] **POINTS-2**: Allowance integration (weekly point grants)
- [ ] **POINTS-3**: Point expiration (use it or lose it)
- [ ] **POINTS-4**: Shared rewards (multiple kids pool points)
- [ ] **POINTS-5**: Penalty system (negative points for behavior)

#### Achievements & Gamification
- [ ] **ACHIEVE-1**: Milestone tracking (100 chores completed)
- [ ] **ACHIEVE-2**: Badges/trophies system
- [ ] **ACHIEVE-3**: Leaderboards (friendly competition)
- [ ] **ACHIEVE-4**: Weekly challenges (bonus points for specific goals)

#### Calendar & Scheduling UI
- [ ] **CAL-UI-1**: Custom Lovelace card with calendar view
- [ ] **CAL-UI-2**: Drag-and-drop chore scheduling
- [ ] **CAL-UI-3**: Color-coding by kid or chore type
- [ ] **CAL-UI-4**: Integration with Google Calendar, Apple Calendar

#### Mobile App
- [ ] **MOBILE-1**: Dedicated mobile app (React Native/Flutter)
- [ ] **MOBILE-2**: Push notifications outside HA
- [ ] **MOBILE-3**: Offline mode (sync when online)

#### Analytics & Reporting
- [ ] **ANALYTICS-1**: Completion rate graphs (per kid, per chore)
- [ ] **ANALYTICS-2**: Points earned over time charts
- [ ] **ANALYTICS-3**: Export data to CSV/Excel
- [ ] **ANALYTICS-4**: Weekly/monthly reports sent via email

#### Multi-Family Support
- [ ] **MULTI-1**: Support multiple households in one instance
- [ ] **MULTI-2**: Family-level isolation of data
- [ ] **MULTI-3**: Share chore templates across families

#### Advanced UI
- [ ] **ADV-UI-1**: Custom Lovelace card for chore management
- [ ] **ADV-UI-2**: Theme support (match HA themes)
- [ ] **ADV-UI-3**: Kid-friendly view with avatars and animations
- [ ] **ADV-UI-4**: Voice control integration (Alexa/Google Assistant)

#### Integrations
- [ ] **INTEG-1**: Google Assistant actions ("Hey Google, mark dishes as done")
- [ ] **INTEG-2**: Alexa skill
- [ ] **INTEG-3**: Apple Shortcuts support
- [ ] **INTEG-4**: Integration with allowance/banking apps
- [ ] **INTEG-5**: IFTTT/Zapier webhooks

#### Security & Privacy
- [ ] **SEC-1**: Encrypted database (optional)
- [ ] **SEC-2**: Audit log (who changed what)
- [ ] **SEC-3**: Parent PIN for sensitive actions
- [ ] **SEC-4**: Kid cannot view other kids' points (privacy setting)

---

## Open Questions & Decisions

### Technology Decisions Needed

#### 1. Web Framework
- **Option A**: FastAPI (modern, async, auto-docs)
- **Option B**: Flask (simpler, more resources/examples)
- **Recommendation**: FastAPI for async and built-in OpenAPI docs
- **Decision**: TBD

#### 2. Frontend Framework (Add-on UI)
- **Option A**: Jinja2 + HTMX (no build step, simple)
- **Option B**: React/Vue (modern, rich components, requires build)
- **Option C**: Alpine.js + Tailwind (lightweight, no build)
- **Recommendation**: Jinja2 + HTMX for Phase 1 (fast dev), migrate later if needed
- **Decision**: TBD

#### 3. ORM vs Raw SQL
- **Option A**: SQLAlchemy (ORM, easier models, migrations)
- **Option B**: Raw SQL (simpler, no abstraction)
- **Recommendation**: SQLAlchemy for maintainability
- **Decision**: TBD

#### 4. Authentication Strategy
- **Option A**: Trust HA ingress headers (simpler)
- **Option B**: API key + JWT (more secure)
- **Recommendation**: Option A for Phase 1, add API key for external access later
- **Decision**: TBD

### Feature Clarifications Needed

#### 1. Shared Chores - Multiple Kids Working Together
- How do we track who contributed?
- Should all kids claim individually, or one claim for the group?
- Equal point split or configurable?
- **Proposed**: Each kid claims individually, each gets full points (cooperation incentivized)

#### 2. One-Off Chores
- Should these be in a separate list or mixed with recurring?
- Do they expire if not completed?
- **Proposed**: Mixed list, optional expiration date

#### 3. Point Penalties
- Should penalties require approval (or just be instant)?
- Minimum point balance (can kids go negative)?
- **Proposed**: Instant deduction, can go negative (teachable moment)

#### 4. Notification Preferences
- Per-user notification settings (parent gets mobile, kid gets dashboard)?
- Different notification types (assigned, claimed, approved)?
- Quiet hours?
- **Proposed**: Global defaults in Phase 1, per-user settings in Phase 2

#### 5. Multiple Parents
- Should parent actions require consensus, or any parent can approve?
- Track which parent approved (for accountability)?
- **Proposed**: Any parent can approve, track approver in database

### Database Design Questions

#### 1. Soft Delete vs Hard Delete
- Should we soft delete (is_active flag) or hard delete records?
- **Proposed**: Soft delete for chores/rewards, hard delete for test data only

#### 2. Historical Data Retention
- Keep all chore instances forever, or archive after X months?
- **Proposed**: Keep forever (disk space is cheap), add archive feature in Phase 2

#### 3. Point Balance Calculation
- Store current balance in users.points (denormalized) or calculate from history?
- **Proposed**: Denormalized for performance, validated against history on load

---

## Success Metrics

### Phase 1 MVP Success
- [ ] Add-on installs successfully via HA add-on store
- [ ] Integration configures via UI without errors
- [ ] Parent can create 5 different chores with different recurrence patterns
- [ ] Kid can claim and parent can approve chore in < 30 seconds
- [ ] Points balance updates in real-time on dashboard
- [ ] Calendar integration shows upcoming chores
- [ ] System handles 3 kids, 10 chores, 100 instances without performance issues

### Long-Term Success
- Active users (households using the system)
- Chore completion rate (% of assigned chores completed)
- User retention (still using after 3 months)
- Community contributions (PRs, issues, feedback)

---

## Development Principles

1. **Mobile-First**: Admin UI must work well on phones
2. **HA-Native**: Feel like a first-class HA integration, not a bolt-on
3. **Data Integrity**: Proper database design, no entity abuse
4. **User-Friendly**: Non-technical parents can set up and use
5. **Kid-Appropriate**: UI elements kids can understand and use
6. **Performance**: Fast response times (< 500ms for API calls)
7. **Secure**: Protect family data, proper role-based access
8. **Maintainable**: Clean code, documented, testable

---

## Next Steps

1. **Review this plan** - Ensure alignment with vision
2. **Make technology decisions** - Choose frameworks and tools
3. **Set up project structure** - Create repos, directories, initial files
4. **Begin Phase 1 implementation** - Start with database and API
5. **Iterate with testing** - Test early and often with real family use

---

**Document Version**: 1.0
**Last Updated**: 2025-11-11
**Status**: Draft - Awaiting Approval
