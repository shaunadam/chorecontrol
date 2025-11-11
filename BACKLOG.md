# ChoreControl - Task Backlog

This is a simplified backlog extracted from PROJECT_PLAN.md for easier tracking.

## Legend
- [ ] Not started
- [x] Complete
- [~] In progress
- [?] Blocked/needs decision

---

## Phase 1: MVP Tasks

### 1. Project Setup (6 tasks)

- [ ] **SETUP-1**: Initialize Git repository structure
- [ ] **SETUP-2**: Create add-on directory structure and Dockerfile
- [ ] **SETUP-3**: Create integration directory structure
- [ ] **SETUP-4**: Set up Python virtual environment and dependencies
- [ ] **SETUP-5**: Configure linting tools (ruff, black, mypy)
- [ ] **SETUP-6**: Create README.md with project overview

### 2. Add-on: Database Layer (5 tasks)

- [ ] **DB-1**: Design and create SQLite schema (all tables from data model)
- [ ] **DB-2**: Write database initialization script
- [ ] **DB-3**: Create SQLAlchemy models (or raw SQL helpers)
- [ ] **DB-4**: Write database migration strategy (for future updates)
- [ ] **DB-5**: Create seed data script for testing

### 3. Add-on: REST API - Core (10 tasks)

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

### 4. Add-on: Business Logic (5 tasks)

- [ ] **LOGIC-1**: Implement simple chore scheduler (daily/weekly recurrence)
- [ ] **LOGIC-2**: Implement points calculation and awarding
- [ ] **LOGIC-3**: Implement reward claim validation (points, cooldown, limits)
- [ ] **LOGIC-4**: Implement notification event system (hooks for integration)
- [ ] **LOGIC-5**: Create background task runner for scheduled jobs

### 5. Add-on: Web UI (10 tasks)

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

### 6. Add-on: Deployment (5 tasks)

- [ ] **DEPLOY-1**: Create Dockerfile for add-on
- [ ] **DEPLOY-2**: Create add-on config.json (HA add-on metadata)
- [ ] **DEPLOY-3**: Configure ingress for sidebar access
- [ ] **DEPLOY-4**: Test add-on installation in HA
- [ ] **DEPLOY-5**: Document add-on installation and setup

### 7. Integration: Core (10 tasks)

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

### 8. Integration: HA User Mapping (3 tasks)

- [ ] **INT-11**: Implement parent/kid role detection
- [ ] **INT-12**: Create user mapping configuration
- [ ] **INT-13**: Filter entities based on current user context

### 9. Dashboards (4 tasks)

- [ ] **DASH-1**: Create example kid dashboard YAML
- [ ] **DASH-2**: Create example parent dashboard YAML
- [ ] **DASH-3**: Document dashboard setup instructions
- [ ] **DASH-4**: Test dashboard with real data

### 10. Calendar Integration (3 tasks)

- [ ] **CAL-1**: Implement ICS feed generation for user's chores
- [ ] **CAL-2**: Test ICS feed with HA calendar integration
- [ ] **CAL-3**: Document calendar setup

### 11. Testing & Documentation (7 tasks)

- [ ] **TEST-1**: Write unit tests for API endpoints
- [ ] **TEST-2**: Write unit tests for business logic
- [ ] **TEST-3**: Write integration tests (add-on + integration)
- [ ] **TEST-4**: Perform end-to-end testing (full workflow)
- [ ] **DOC-1**: Write user documentation (setup, usage)
- [ ] **DOC-2**: Write developer documentation (architecture, API)
- [ ] **DOC-3**: Create demo video/screenshots

### 12. Final MVP Release (3 tasks)

- [ ] **RELEASE-1**: Version tagging and release notes
- [ ] **RELEASE-2**: Publish to GitHub
- [ ] **RELEASE-3**: Submit to HA community add-on repository (optional)

**Total Phase 1 Tasks: 71**

---

## Phase 2: Priority Backlog

### Scheduling Enhancements
- [ ] **SCHED-1**: Complex recurrence patterns (cron-like)
- [ ] **SCHED-2**: Chore rotation (auto-assign to different kid each week)
- [ ] **SCHED-3**: Seasonal chores (only certain months)
- [ ] **SCHED-4**: Skip holidays or school breaks

### Workflow Enhancements
- [ ] **WORK-1**: Photo proof of completion (upload image)
- [ ] **WORK-2**: Auto-approval after X hours
- [ ] **WORK-3**: Partial completion (kid worked on it but didn't finish)
- [ ] **WORK-4**: Chore templates/presets (common chores library)

### Points & Rewards
- [ ] **POINTS-1**: Bonus points for streaks (7 days in a row)
- [ ] **POINTS-2**: Allowance integration (weekly point grants)
- [ ] **POINTS-3**: Point expiration (use it or lose it)
- [ ] **POINTS-4**: Shared rewards (multiple kids pool points)
- [ ] **POINTS-5**: Penalty system (negative points for behavior)

### Achievements & Gamification
- [ ] **ACHIEVE-1**: Milestone tracking (100 chores completed)
- [ ] **ACHIEVE-2**: Badges/trophies system
- [ ] **ACHIEVE-3**: Leaderboards (friendly competition)
- [ ] **ACHIEVE-4**: Weekly challenges (bonus points for specific goals)

---

## Phase 3: Advanced Features

### Calendar & UI
- [ ] **CAL-UI-1**: Custom Lovelace card with calendar view
- [ ] **CAL-UI-2**: Drag-and-drop chore scheduling
- [ ] **CAL-UI-3**: Color-coding by kid or chore type
- [ ] **CAL-UI-4**: Integration with Google Calendar, Apple Calendar

### Analytics
- [ ] **ANALYTICS-1**: Completion rate graphs (per kid, per chore)
- [ ] **ANALYTICS-2**: Points earned over time charts
- [ ] **ANALYTICS-3**: Export data to CSV/Excel
- [ ] **ANALYTICS-4**: Weekly/monthly reports sent via email

### Integrations
- [ ] **INTEG-1**: Google Assistant actions
- [ ] **INTEG-2**: Alexa skill
- [ ] **INTEG-3**: Apple Shortcuts support
- [ ] **INTEG-4**: Integration with allowance/banking apps
- [ ] **INTEG-5**: IFTTT/Zapier webhooks

---

## Quick Wins (Can be done anytime)

- [ ] Add dark mode toggle to web UI
- [ ] Export/import chore templates (JSON)
- [ ] Bulk chore operations (assign multiple chores at once)
- [ ] Chore categories/tags for filtering
- [ ] Custom point multipliers (double points weekends)
- [ ] Notification sound customization
- [ ] Parent notes on chores (private from kids)
- [ ] Undo last approval (oops button)

---

## Bugs / Issues

Track bugs here as they're discovered during development.

---

## Ideas / Future Consideration

- Integration with school calendar (sync from Google Classroom)
- Shared family calendar view (not just individual)
- Export to printable PDF (weekly chore chart)
- SMS notifications (via Twilio integration)
- Multi-language support
- Accessibility improvements (screen reader support)
- PWA (Progressive Web App) for mobile home screen
- Apple Watch complications
- Vacation mode (pause chore generation)
- Guest user accounts (grandparents can view/approve)

---

**Last Updated**: 2025-11-11
