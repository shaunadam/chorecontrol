# ChoreControl

A chore management system for families, integrated with Home Assistant.

## Quick Reference

### Stack
- **Backend**: Flask 2.3+, SQLAlchemy ORM, SQLite
- **Frontend**: Jinja2 templates, Tailwind CSS, vanilla JS
- **Integration**: Home Assistant custom component
- **Background Jobs**: APScheduler

### Commands
```bash
# Run tests
PYTHONPATH=chorecontrol python3 -m pytest chorecontrol/tests/ -v

# Run specific test file
PYTHONPATH=chorecontrol python3 -m pytest chorecontrol/tests/test_instances.py -v

# Database migrations
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db migrate -m "description"
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db upgrade

# Run development server
PYTHONPATH=chorecontrol FLASK_APP=app.py flask run
```

### Pre-commit Hooks
This project uses ruff, black, mypy, and bandit. Run before committing:
```bash
pre-commit run --all-files
```

## Architecture

```
chorecontrol/
├── app.py              # Flask factory, middleware
├── models.py           # SQLAlchemy models (8 tables)
├── auth.py             # @ha_auth_required, @parent_required decorators
├── routes/
│   ├── ui.py           # Web UI routes
│   ├── instances.py    # Chore instance workflow API
│   ├── chores.py       # Chore CRUD API
│   ├── rewards.py      # Reward marketplace API
│   └── ...
├── services/           # Business logic layer (being introduced)
├── utils/
│   ├── instance_generator.py  # Generates ChoreInstances from Chores
│   ├── recurrence.py          # Recurrence pattern calculations
│   └── webhooks.py            # Event firing
├── jobs/               # APScheduler background tasks
└── templates/          # Jinja2 HTML templates
```

### Data Model (Key Tables)
- `User` - Parents, kids, claim_only users (role-based)
- `Chore` - Template with recurrence pattern, points value
- `ChoreInstance` - Individual occurrence with status workflow
- `Reward` - Redeemable items with points cost
- `RewardClaim` - Redemption record with approval workflow
- `PointsHistory` - Audit log of all point transactions

### Instance Status Flow
```
assigned → claimed → approved
              ↓
           rejected → assigned (re-claimable)
```

## Patterns & Conventions

### Route Organization
- API routes return JSON, prefix with `/api/`
- UI routes render templates, no prefix
- Use `@ha_auth_required` for auth, `@parent_required` for admin-only

### Webhooks
Fire events for external integrations:
```python
from utils.webhooks import fire_webhook
fire_webhook('chore_instance_claimed', instance)
```

### One-Time vs Recurring Chores
- `recurrence_type='none'` = one-time (single instance)
- `recurrence_type='simple'|'complex'` = recurring (multiple instances)
- `due_date=None` = "anytime" chores (no specific deadline)

## Skills
See `.claude/skills/` for workflow-specific guidance:
- `commit.md` - Committing with pre-commit hooks
- `test.md` - Running and writing tests
- `review.md` - PR review checklist
- `migrate.md` - Database migrations

## Testing
- Tests in `chorecontrol/tests/`
- Use fixtures from `conftest.py` (app, client, sample_user, etc.)
- Run full suite before pushing
