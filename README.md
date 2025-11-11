# ChoreControl

> A comprehensive chore management system for Home Assistant

## Overview

ChoreControl is a Home Assistant integration that helps families manage chores, track points, and reward kids for completing tasks. Unlike existing solutions that rely on entity-based storage, ChoreControl uses a proper database structure for reliability and scalability.

### Key Features (Planned)

- **Chore Management**: Create recurring or one-off chores with flexible scheduling
- **Multi-User Support**: Parent and kid roles with appropriate permissions
- **Points & Rewards**: Kids earn points for completing chores, redeem for rewards
- **Approval Workflow**: Claim → Approve → Award points flow with notifications
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

**Current Phase**: Planning & Design

This project is in early planning stages. See the documentation below for detailed plans:

- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** - Comprehensive project plan with architecture, data model, and roadmap
- **[BACKLOG.md](BACKLOG.md)** - Task backlog organized by phase
- **[DECISIONS.md](DECISIONS.md)** - Technology decisions and trade-offs

## Documentation

### For Users
- Installation Guide (Coming soon)
- User Manual (Coming soon)
- FAQ (Coming soon)

### For Developers
- [Project Plan](PROJECT_PLAN.md) - Complete architectural overview
- [Task Backlog](BACKLOG.md) - Implementation tasks
- [Technology Decisions](DECISIONS.md) - Key technical choices
- API Documentation (Coming soon)
- Contributing Guide (Coming soon)

## Technology Stack (Proposed)

**Backend (Add-on)**
- Python 3.11+
- FastAPI (recommended) or Flask
- SQLAlchemy ORM
- SQLite database
- Jinja2 + HTMX (web UI)
- Docker

**Frontend (Integration)**
- Python 3.11+ (HA custom component)
- aiohttp for API client
- Home Assistant entity platform

**Development**
- Git for version control
- pytest for testing
- ruff, black, mypy for linting
- GitHub for hosting

## Getting Started

### Prerequisites
- Home Assistant instance (2024.1.0+)
- Basic understanding of HA add-ons and integrations
- (For development) Python 3.11+, Docker

### Installation

Not yet available. This project is in planning phase.

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/chorecontrol.git
   cd chorecontrol
   ```

2. Review planning documents:
   - Read [PROJECT_PLAN.md](PROJECT_PLAN.md) for full context
   - Check [DECISIONS.md](DECISIONS.md) for technology choices
   - See [BACKLOG.md](BACKLOG.md) for tasks

3. Development will begin soon!

## Roadmap

### Phase 1: MVP (Current Focus)
- Core chore CRUD operations
- Simple daily/weekly scheduling
- Points and basic rewards system
- Claim/approve workflow
- Kid and parent dashboards
- ICS calendar integration

See [BACKLOG.md](BACKLOG.md) for detailed task list (71 tasks).

### Phase 2: Enhancements
- Complex scheduling (cron-like patterns)
- Photo proof of completion
- Achievements and gamification
- Advanced analytics
- Custom Lovelace cards

### Phase 3: Advanced Features
- Multi-family support
- Mobile app
- Voice assistant integration
- External calendar sync (Google, Apple)

Full feature list in [PROJECT_PLAN.md](PROJECT_PLAN.md#phase-2-future-features).

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

**Status**: Planning Phase
**Last Updated**: 2025-11-11
**Version**: 0.1.0-alpha (pre-release)
