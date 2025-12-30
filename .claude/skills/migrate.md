# Migrate Skill

## What is a Skill?
A skill is a modular instruction file that Claude Code loads when relevant to the current task. Skills keep context focused and avoid bloating every conversation with unnecessary instructions.

## When This Activates
This skill auto-loads when you mention: "migrate", "migration", "database schema", "flask db"

---

## Database Migrations

This project uses Flask-Migrate (Alembic) for database schema changes.

### Create a New Migration

After modifying `models.py`:

```bash
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db migrate -m "description of change"
```

Example:
```bash
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db migrate -m "add reset_count to chore_instances"
```

### Apply Migrations

```bash
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db upgrade
```

### Rollback Last Migration

```bash
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db downgrade
```

### View Migration History

```bash
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db history
```

---

## Migration Files

Migrations are stored in `chorecontrol/migrations/versions/`.

Each migration has:
- `upgrade()` - Apply the change
- `downgrade()` - Revert the change

---

## Best Practices

### 1. Review Auto-Generated Migrations
Alembic auto-detect isn't perfect. Always review the generated migration:
```python
def upgrade():
    # Check this is what you expect
    op.add_column('chore_instances',
        sa.Column('reset_count', sa.Integer(), nullable=True))
```

### 2. Make Migrations Reversible
Always implement `downgrade()`:
```python
def downgrade():
    op.drop_column('chore_instances', 'reset_count')
```

### 3. Handle Data Migrations
For data changes (not just schema):
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

def upgrade():
    # Schema change
    op.add_column('users', sa.Column('role', sa.String(20)))

    # Data migration
    users = table('users', column('role', sa.String))
    op.execute(users.update().values(role='kid'))
```

### 4. Test Migrations
```bash
# Apply
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db upgrade

# Run tests to verify
PYTHONPATH=chorecontrol python3 -m pytest chorecontrol/tests/ -v

# Rollback and reapply to test both directions
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db downgrade
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db upgrade
```

---

## Common Issues

### "Target database is not up to date"
Run upgrade first:
```bash
PYTHONPATH=chorecontrol FLASK_APP=app.py flask db upgrade
```

### "Can't locate revision"
The migration chain is broken. Check `migrations/versions/` for missing files.

### "No changes detected"
- Did you save `models.py`?
- Is the model imported in `app.py`?
- Check `models.py` for syntax errors
