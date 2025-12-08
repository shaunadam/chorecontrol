# Changelog

All notable changes to ChoreControl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] - 2025-12-08

### Added
- New sensors: `chores_due_today` (per-kid), `pending_reward_claims` (per-kid), `pending_reward_approvals` (global)
- Calendar entity showing chore schedules
- New API endpoint: `GET /api/rewards/claims` with status filtering
- Alias fields in webhook events (`instance_id`, `claim_id`) for easier automations

### Changed
- Consolidated documentation from 19 files to 5 files
- Updated user guide with actionable notification examples

## [0.3.1] - 2025-12-02

### Added
- Tailwind CSS implementation for addon UI
- Mobile-first responsive design
- Rewards claiming section on rewards page

### Fixed
- Mobile navigation improvements
- Bug fixes for non-due-date chores

## [0.3.0] - 2025-12-01

### Added
- Full Home Assistant integration with sensors, buttons, services
- Webhook events for real-time notifications
- `claim_only` user role for limited access
- Calendar view in addon UI

### Changed
- Improved API response format consistency
- Better error handling throughout

## [0.2.0] - 2025-11-30

### Added
- Home Assistant integration (custom component)
- Per-kid sensors (points, pending, claimed, completed)
- Global sensors (pending approvals, total kids, active chores)
- Dynamic claim buttons
- Services for automations (claim, approve, reject, adjust_points)
- Supervisor API access for HA user management

### Changed
- Addon configuration to enable HA API access

## [0.1.0] - 2025-11-29

### Added
- Initial addon release
- Flask web application with REST API
- SQLite database with SQLAlchemy ORM
- User management with HA user integration
- Chore management (CRUD, recurrence patterns)
- Chore instance lifecycle (assigned → claimed → approved/rejected)
- Reward system with cooldowns and limits
- Points system with full audit trail
- Approval workflow for chores and rewards
- Background jobs (instance generation, auto-approval, missed detection)
- Web UI for parent administration
- Database migrations with Alembic

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 0.3.2 | 2025-12-08 | New sensors, calendar entity, documentation consolidation |
| 0.3.1 | 2025-12-02 | Tailwind CSS, mobile improvements |
| 0.3.0 | 2025-12-01 | Full HA integration, webhooks |
| 0.2.0 | 2025-11-30 | Custom component, sensors, services |
| 0.1.0 | 2025-11-29 | Initial addon release |
