# ChoreControl Add-on - Database Layer

This directory contains the SQLAlchemy models and database layer for ChoreControl.

## Structure

```
addon/
├── __init__.py          # Package initialization
├── app.py              # Flask application factory
├── models.py           # SQLAlchemy models (7 models)
├── schemas.py          # JSON validation and recurrence patterns
└── requirements.txt    # Python dependencies
```

## Models

The database layer includes 7 SQLAlchemy models:

### 1. **User** (`users` table)
- Represents both parents and kids
- Fields: `ha_user_id`, `username`, `role`, `points`
- Role: 'parent' or 'kid'
- Methods:
  - `calculate_current_points()` - Calculate points from history
  - `verify_points_balance()` - Verify denormalized points match history
  - `adjust_points()` - Adjust points and create history entry

### 2. **Chore** (`chores` table)
- Chore template (recurring or one-off)
- Fields: `name`, `description`, `points`, `recurrence_type`, `recurrence_pattern` (JSON), `assignment_type`, `requires_approval`
- Recurrence types: 'none', 'simple', 'complex'
- Assignment types: 'individual', 'shared'
- Methods:
  - `is_due()` - Check if chore is due on a date
  - `generate_next_instance()` - Generate next chore instance

### 3. **ChoreAssignment** (`chore_assignments` table)
- Links chores to users
- Fields: `chore_id`, `user_id`, `due_date`
- Unique constraint on (chore_id, user_id, due_date)

### 4. **ChoreInstance** (`chore_instances` table)
- Tracks individual chore completions
- Fields: `chore_id`, `due_date`, `status`, `claimed_by`, `approved_by`, `points_awarded`
- Status workflow: 'assigned' → 'claimed' → 'approved'/'rejected'
- Methods:
  - `can_claim()` - Check if user can claim
  - `can_approve()` - Check if user can approve
  - `award_points()` - Approve and award points

### 5. **Reward** (`rewards` table)
- Rewards that can be claimed with points
- Fields: `name`, `description`, `points_cost`, `cooldown_days`, `max_claims_total`, `max_claims_per_kid`
- Methods:
  - `can_claim()` - Check if user can claim (returns tuple: bool, reason)
  - `is_on_cooldown()` - Check cooldown status for user

### 6. **RewardClaim** (`reward_claims` table)
- Records of reward claims
- Fields: `reward_id`, `user_id`, `points_spent`, `status`, `approved_by`
- Status: 'pending', 'approved', 'rejected'

### 7. **PointsHistory** (`points_history` table)
- Audit log of all point changes
- Fields: `user_id`, `points_delta`, `reason`, `chore_instance_id`, `reward_claim_id`, `created_by`
- Used to verify denormalized points balance

## Relationships

All models have proper relationships defined:
- Users → ChoreAssignments, ChoreInstances (claimed/approved/rejected), RewardClaims, PointsHistory
- Chores → ChoreAssignments, ChoreInstances
- Rewards → RewardClaims
- All relationships use proper `foreign_keys` parameter to avoid ambiguity

## JSON Schema (schemas.py)

### Recurrence Patterns

**Simple Patterns:**
```json
{
  "type": "simple",
  "interval": "daily|weekly|monthly",
  "every_n": 1,
  "time": "18:00"
}
```

**Complex Patterns:**
```json
{
  "type": "complex",
  "days_of_week": [0, 2, 4],  // Mon, Wed, Fri (0=Monday)
  "weeks_of_month": [1, 3],   // 1st and 3rd week
  "days_of_month": [1, 15],   // 1st and 15th
  "time": "18:00"
}
```

### Validation Functions
- `validate_recurrence_pattern()` - Validate pattern against JSON schema
- `calculate_next_due_date()` - Calculate next occurrence
- `generate_instances_for_date_range()` - Generate all instances in range
- `format_recurrence_pattern()` - Human-readable description

### Example Patterns
See `EXAMPLE_PATTERNS` dict in `schemas.py` for ready-to-use patterns:
- `daily`, `every_other_day`, `weekly`, `bi_weekly`, `monthly`
- `weekdays` (Mon-Fri), `monday_wednesday_friday`
- `first_and_fifteenth`, `first_monday`

## Database Migrations

### Setup
```bash
# Install dependencies
pip install -r addon/requirements.txt

# Initialize Flask-Migrate (already done)
FLASK_APP=manage.py flask db init

# Create migration
FLASK_APP=manage.py flask db migrate -m "Description"

# Apply migration
FLASK_APP=manage.py flask db upgrade

# Rollback migration
FLASK_APP=manage.py flask db downgrade
```

### Migration Files
- Migrations stored in `/migrations/versions/`
- Initial migration: `fe05e7ce7c54_initial_migration_with_all_7_models.py`

## Testing

Run the test script to verify all models work:

```bash
python test_models.py
```

This will:
1. Create sample users (parent and kids)
2. Create chores with recurrence patterns
3. Assign chores to kids
4. Test claim/approve workflow
5. Test points calculation and history
6. Test reward claims with validation
7. Verify all relationships work

## Success Criteria

✅ All 7 models defined with proper types
✅ Relationships work (can navigate user.chores, etc.)
✅ Initial migration created and tested
✅ Can create and query all models in Python shell
✅ JSON schema validates recurrence patterns
✅ Migration up/down works correctly
✅ All model methods tested and working

## Next Steps

This database layer is ready for integration with:
1. Flask REST API (Stream 3)
2. Flask Web UI (Stream 4)
3. Background scheduler for chore generation (Stream 5)

## Notes

- Database file location: `instance/chorecontrol.db` (Flask default)
- SQLite is used for simplicity and portability
- All models use soft delete pattern (`is_active` flag) where appropriate
- Points are stored denormalized in `User.points` but verified against `PointsHistory`
- Foreign keys properly defined with cascade deletes
- Indexes added for common query patterns
