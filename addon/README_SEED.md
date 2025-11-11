# Seed Data Scripts

This directory contains scripts for generating realistic seed data for ChoreControl development and testing.

## Files

### `seed.py`
Main script for generating seed data. Creates a complete, realistic dataset including:
- Parent and kid users
- Chores with various recurrence patterns (daily, weekly, complex)
- Chore assignments linking chores to age-appropriate kids
- Chore instances in all states (assigned, claimed, approved, rejected)
- Rewards with different costs and limits
- Reward claims (some redeemed, some pending)
- Points history matching all transactions

### `seed_helpers.py`
Helper functions for seed generation:
- Date generation utilities
- Recurrence pattern creation (DEC-010 format)
- Realistic data lookups (chore names, reward ideas)
- Age-based chore assignment
- Random data generators

## Usage

### Prerequisites

When the models are implemented, install dependencies:

```bash
pip install flask flask-sqlalchemy
```

### Basic Usage

**Generate default dataset:**
```bash
python addon/seed.py --reset --verbose
```

This creates:
- 2 parents
- 3 kids (Alex, Bailey, Charlie)
- 12 chores
- 25 chore instances
- 7 rewards
- 5 reward claims

### Command-Line Options

```bash
python addon/seed.py [OPTIONS]
```

**Options:**
- `--reset` - Clear all existing data before seeding (requires confirmation)
- `--preserve` - Add to existing data without clearing
- `--kids N` - Create N kid users (default: 3)
- `--chores N` - Create N chores (default: 12)
- `--instances N` - Create N chore instances (default: 25)
- `--rewards N` - Create N rewards (default: 7)
- `--claims N` - Create N reward claims (default: 5)
- `--verbose` / `-v` - Print detailed output

### Examples

**Create larger dataset:**
```bash
python addon/seed.py --reset --kids 5 --chores 20 --instances 50 --verbose
```

**Add more data to existing database:**
```bash
python addon/seed.py --preserve --instances 10
```

**Quick test with minimal data:**
```bash
python addon/seed.py --reset --kids 2 --chores 5 --instances 10
```

## Implementation Status

⚠️ **Current Status**: The seed scripts are ready but require the following to be implemented first:

1. **Stream 2: Database Models** (`addon/models.py`)
   - SQLAlchemy models for all tables
   - Database relationships and constraints

2. **Flask Application** (`addon/app.py`)
   - Application factory (`create_app()`)
   - Database initialization
   - Flask-SQLAlchemy setup

### To Enable Database Operations

Once models are implemented, uncomment the `TODO` sections in `seed.py`:

1. Import statements at the top:
   ```python
   from models import db, User, Chore, ChoreAssignment, ChoreInstance
   from models import Reward, RewardClaim, PointsHistory
   from app import create_app
   ```

2. Database operations in each method (marked with `# TODO: When models are available`)

3. Main function Flask context:
   ```python
   app = create_app()
   with app.app_context():
       generator.generate_all(...)
   ```

## Data Created

### Users
- **Parents**: 2 users with role="parent"
  - ParentOne, ParentTwo
  - Each has a unique HA user ID

- **Kids**: 3 users with role="kid" (configurable)
  - Alex (age 12)
  - Bailey (age 9)
  - Charlie (age 15)
  - Each starts with 0-50 points based on their history

### Chores
- Mix of recurrence types:
  - 20% one-off (no recurrence)
  - 50% simple recurring (daily/weekly/monthly)
  - 30% complex recurring (specific days of week)
- Realistic names and descriptions
- Age-appropriate assignments
- Some with auto-approval enabled

### Chore Instances
- Various states:
  - 60% approved (completed)
  - 20% assigned (not started)
  - 15% claimed (pending approval)
  - 5% rejected (with reasons)
- Dates spread across last 7 days
- Points awarded match chore points

### Rewards
- Various point costs (15-50 points)
- Some with cooldown periods
- Some with claim limits
- Realistic reward names

### Edge Cases Covered

The seed data includes these edge cases for testing:

1. **Chore with auto-approval enabled** - Tests auto-approval workflow
2. **Chore claimed but overdue** - Tests overdue detection
3. **Kid with negative/low points** - Tests insufficient points handling
4. **Reward on cooldown** - Tests cooldown validation
5. **Reward at claim limit** - Tests claim limit enforcement
6. **Chore assigned to multiple kids** - Tests shared chores
7. **Rejected chore with reason** - Tests rejection workflow
8. **Manual points adjustment** - Tests points history without chore/reward

## Points Balance Integrity

The seed script ensures points balance integrity:

1. Creates points history entries for:
   - Every approved chore instance (+points)
   - Every redeemed reward (-points)
   - Some manual adjustments

2. Updates user.points to match sum of points_history

3. Validates balance is non-negative

## Recurrence Pattern Format

Follows DEC-010 decision format:

**Simple patterns:**
```json
{
  "type": "simple",
  "interval": "daily|weekly|monthly",
  "every_n": 1
}
```

**Complex patterns:**
```json
{
  "type": "complex",
  "days_of_week": [1, 3, 5],
  "weeks_of_month": [1, 3],
  "days_of_month": [1, 15]
}
```

## Integration with Tests

See `tests/fixtures/` for pytest fixtures that use this data:

```python
def test_user_points(sample_users):
    kids = [u for u in sample_users if u['role'] == 'kid']
    assert all(u['points'] >= 0 for u in kids)
```

## Production Use

This seed script can be used in production for:

1. **Demo instances** - Populate demo sites with realistic data
2. **Development** - Quick database setup for development
3. **Testing** - Create consistent test data
4. **Training** - Show users how the system works

⚠️ **Warning**: Always use `--reset` carefully in production. It will delete all data!

## Extending the Seed Data

To add new types of data:

1. Add data to `seed_helpers.py` constants (e.g., `CHORE_DATA`)
2. Add a new method to `SeedDataGenerator` class
3. Call the method from `generate_all()`
4. Add command-line argument if configurable
5. Update the summary output

## Troubleshooting

**Script says models not implemented:**
- This is expected until Stream 2 is complete
- The script structure is ready, just needs models

**Foreign key errors:**
- Ensure data is created in dependency order
- Check that IDs are set correctly

**Points don't match:**
- Run with `--verbose` to see point calculations
- Verify points_history entries sum correctly

## See Also

- `PROJECT_PLAN.md` - Data model documentation
- `DECISIONS.md` - DEC-010 for recurrence patterns
- `tests/fixtures/sample_data.json` - Minimal test dataset
