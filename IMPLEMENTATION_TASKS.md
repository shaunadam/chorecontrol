# ChoreControl - Step 3 Implementation Tasks

> **Phase**: Business Logic Layer Implementation
> **Based on**: [BUSINESS_LOGIC_SPEC.md](BUSINESS_LOGIC_SPEC.md)
> **For**: AI Agent Execution
> **Created**: 2025-11-18

---

## Overview

This document breaks down Step 3 (Business Logic Layer) into discrete, implementable tasks for AI agents. Each task includes:
- **Scope**: What needs to be done
- **Files to modify/create**: Specific file paths
- **Dependencies**: Prerequisites that must be completed first
- **Acceptance criteria**: How to verify completion
- **Estimated complexity**: Low/Medium/High

---

## Task Organization

### Phases:
1. **Database Schema Changes** (Tasks 1-3)
2. **Core Business Logic** (Tasks 4-9)
3. **Background Jobs** (Tasks 10-14)
4. **API Endpoints** (Tasks 15-21)
5. **Webhook Integration** (Tasks 22-23)
6. **Testing** (Tasks 24-29)
7. **Documentation & Deployment** (Tasks 30-31)

---

## Phase 1: Database Schema Changes

### Task 1: Create Database Migration for Model Changes
**Complexity**: Medium

**Scope**:
- Create Alembic migration to add new fields to existing models
- Update constraints and indexes

**Files to create/modify**:
- Create new migration file in `addon/migrations/versions/`
- Modify: `addon/models.py`

**Changes required**:

1. **ChoreInstance model** (`addon/models.py`):
   ```python
   assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
   claimed_late = db.Column(db.Boolean, default=False, nullable=False)

   # Update constraint
   CheckConstraint("status IN ('assigned', 'claimed', 'approved', 'rejected', 'missed')")

   # Add index
   Index('idx_chore_instances_assigned_to', 'assigned_to')
   ```

2. **Chore model** (`addon/models.py`):
   ```python
   allow_late_claims = db.Column(db.Boolean, default=False, nullable=False)
   late_points = db.Column(db.Integer, nullable=True)
   ```

3. **Reward model** (`addon/models.py`):
   ```python
   requires_approval = db.Column(db.Boolean, default=False, nullable=False)
   ```

4. **RewardClaim model** (`addon/models.py`):
   ```python
   expires_at = db.Column(db.DateTime, nullable=True)
   ```

5. **User model** (`addon/models.py`):
   ```python
   # Update constraint
   CheckConstraint("role IN ('parent', 'kid', 'system')")
   ```

**Migration commands**:
```bash
cd addon
flask db migrate -m "Add business logic fields (assigned_to, claimed_late, late_points, etc.)"
flask db upgrade
```

**Dependencies**: None

**Acceptance criteria**:
- Migration file created successfully
- Migration runs without errors
- All new fields exist in database schema
- Constraints updated correctly
- Existing data preserved

---

### Task 2: Update Model Methods for New Fields
**Complexity**: Medium

**Scope**:
- Update `ChoreInstance.can_claim()` to check `assigned_to` and due_date
- Update `ChoreInstance.award_points()` to handle late points
- Update `Reward.can_claim()` to check `requires_approval`

**Files to modify**:
- `addon/models.py`

**Changes required**:

1. **Update `ChoreInstance.can_claim()`**:
   ```python
   def can_claim(self, user_id: int) -> bool:
       """Check if a user can claim this chore instance."""

       # Must be in 'assigned' status
       if self.status != 'assigned':
           return False

       # Check if claimable based on due_date (Option B: Strict)
       if self.due_date is not None:
           today = date.today()

           # Cannot claim future chores
           if self.due_date > today:
               return False

           # If past due and late claims not allowed, should be 'missed'
           if self.due_date < today and not self.chore.allow_late_claims:
               return False

       # Check assignment
       # For individual chores
       if self.assigned_to is not None:
           return self.assigned_to == user_id

       # For shared chores
       assignment = ChoreAssignment.query.filter_by(
           chore_id=self.chore_id,
           user_id=user_id
       ).first()

       return assignment is not None
   ```

2. **Update `ChoreInstance.award_points()`**:
   ```python
   def award_points(self, approver_id: int, points: Optional[int] = None) -> None:
       """Award points to the user who claimed this chore."""

       if self.status != 'claimed':
           raise ValueError("Cannot award points for non-claimed chore")

       if self.claimed_by is None:
           raise ValueError("Cannot award points without a claimer")

       # Determine points to award
       if points is not None:
           # Parent override
           points_to_award = points
       elif self.claimed_late and self.chore.late_points is not None:
           # Late completion with late_points set
           points_to_award = self.chore.late_points
       else:
           # Normal or late completion without late_points override
           points_to_award = self.chore.points

       self.points_awarded = points_to_award

       # Update status
       self.status = 'approved'
       self.approved_by = approver_id
       self.approved_at = datetime.utcnow()

       # Award points to user
       claimer = User.query.get(self.claimed_by)
       if claimer:
           claimer.adjust_points(
               delta=points_to_award,
               reason=f"Completed chore: {self.chore.name}",
               created_by_id=approver_id,
               chore_instance_id=self.id
           )
   ```

**Dependencies**: Task 1

**Acceptance criteria**:
- `can_claim()` validates due_date correctly
- `can_claim()` validates assigned_to for individual chores
- `can_claim()` checks ChoreAssignment for shared chores
- `award_points()` uses late_points when appropriate
- `award_points()` respects parent point override
- All edge cases handled (null due_date, null late_points, etc.)

---

### Task 3: Update Seed Data Script for New Fields
**Complexity**: Medium

**Scope**:
- Create system user for auto-approvals
- Update chore seeding to include new fields (allow_late_claims, late_points)
- Update reward seeding to include requires_approval field
- Create varied examples demonstrating all new features
- Optionally create sample pre-claimed instances for testing

**Files to modify**:
- `addon/seed.py`

**Changes required**:

1. **Create system user**:
```python
def create_system_user(db):
    """Create the system user for auto-approvals and system actions."""
    system_user = User.query.filter_by(ha_user_id='system').first()

    if not system_user:
        system_user = User(
            ha_user_id='system',
            username='System',
            role='system',
            points=0
        )
        db.session.add(system_user)
        db.session.commit()
        logger.info("Created system user")
    else:
        logger.info("System user already exists")

    return system_user
```

2. **Update chore seed data** with new fields:
```python
def seed_chores(db, users):
    """Seed sample chores with new fields."""

    parent = [u for u in users if u.role == 'parent'][0]
    kids = [u for u in users if u.role == 'kid']

    chores_data = [
        {
            'name': 'Make Bed',
            'points': 5,
            'recurrence_type': 'daily',
            'recurrence_pattern': {'type': 'daily'},
            'assignment_type': 'individual',
            'requires_approval': True,
            'allow_late_claims': True,      # NEW - allow late with penalty
            'late_points': 3,                # NEW - reduced points if late
            'assigned_users': [kids[0].id, kids[1].id]
        },
        {
            'name': 'Take out trash',
            'points': 10,
            'recurrence_type': 'weekly',
            'recurrence_pattern': {'type': 'weekly', 'days_of_week': [1, 4]},
            'assignment_type': 'shared',
            'requires_approval': True,
            'auto_approve_after_hours': 24,
            'allow_late_claims': False,      # NEW - no late claims (becomes missed)
            'assigned_users': [kids[0].id, kids[1].id]
        },
        {
            'name': 'Clean room',
            'points': 15,
            'recurrence_type': 'weekly',
            'recurrence_pattern': {'type': 'weekly', 'days_of_week': [6]},
            'assignment_type': 'individual',
            'requires_approval': True,
            'allow_late_claims': True,       # NEW - allow late claims
            'late_points': 10,                # NEW - partial points
            'assigned_users': [kids[0].id, kids[1].id]
        },
        {
            'name': 'Water plants',
            'points': 5,
            'recurrence_type': 'monthly',
            'recurrence_pattern': {'type': 'monthly', 'days_of_month': [1, 15]},
            'assignment_type': 'shared',
            'requires_approval': True,
            'allow_late_claims': False,      # NEW - strict deadline
            'assigned_users': [kids[0].id, kids[1].id]
        },
        {
            'name': 'Organize toys',
            'points': 8,
            'recurrence_type': 'none',
            'recurrence_pattern': {'type': 'none'},
            'assignment_type': 'individual',
            'requires_approval': False,
            'allow_late_claims': True,       # NEW - anytime chore
            'assigned_users': [kids[0].id]
        }
    ]

    # ... create chores from data ...
```

3. **Update reward seed data**:
```python
def seed_rewards(db):
    """Seed sample rewards with new fields."""

    rewards_data = [
        {
            'name': '30 minutes screen time',
            'points_cost': 20,
            'requires_approval': False,      # NEW - auto-approve
            'is_active': True
        },
        {
            'name': 'Pick dinner menu',
            'points_cost': 50,
            'requires_approval': True,       # NEW - needs parent approval
            'is_active': True
        },
        {
            'name': 'Stay up 30 min late',
            'points_cost': 30,
            'requires_approval': True,       # NEW - needs approval
            'cooldown_days': 7,
            'is_active': True
        },
        {
            'name': 'Choose movie night film',
            'points_cost': 40,
            'requires_approval': False,      # NEW - auto-approve
            'max_claims_per_kid': 2,
            'is_active': True
        }
    ]

    # ... create rewards from data ...
```

4. **Optionally create sample instances** (for testing):
```python
def seed_sample_instances(db, chores, users):
    """Create sample instances for testing (optional)."""

    from datetime import date, timedelta, datetime
    from addon.models import ChoreInstance

    kids = [u for u in users if u.role == 'kid']

    # Claimed instance (not late)
    instance1 = ChoreInstance(
        chore_id=chores[0].id,
        due_date=date.today(),
        status='claimed',
        assigned_to=kids[0].id,
        claimed_by=kids[0].id,
        claimed_at=datetime.utcnow(),
        claimed_late=False
    )

    # Late-claimed instance
    instance2 = ChoreInstance(
        chore_id=chores[0].id,
        due_date=date.today() - timedelta(days=1),
        status='claimed',
        assigned_to=kids[1].id,
        claimed_by=kids[1].id,
        claimed_at=datetime.utcnow(),
        claimed_late=True
    )

    # Missed instance
    instance3 = ChoreInstance(
        chore_id=chores[1].id,
        due_date=date.today() - timedelta(days=2),
        status='missed',
        assigned_to=None  # Shared chore
    )

    db.session.add_all([instance1, instance2, instance3])
    db.session.commit()
```

5. **Update main seed function**:
```python
def seed_database():
    # ... existing code ...

    # Create system user first
    system_user = create_system_user(db)

    # Create users, chores, rewards with new fields
    users = seed_users(db)
    chores = seed_chores(db, users)
    rewards = seed_rewards(db)

    # Optional: create sample instances for testing
    seed_sample_instances(db, chores, users)

    # ... rest of seed data ...
```

**Dependencies**: Task 1

**Acceptance criteria**:
- System user created with `ha_user_id='system'` and `role='system'`
- Chores include varied examples of allow_late_claims and late_points
- Rewards include both auto-approve and pending-approval types
- Sample instances demonstrate different statuses (claimed, late, missed)
- Seed script runs without errors
- All new fields populated with realistic test data
- Script is idempotent (can be run multiple times safely)

---

## Phase 2: Core Business Logic

### Task 4: Implement Recurrence Pattern Parser
**Complexity**: High

**Scope**:
- Create utility module for parsing recurrence patterns
- Implement date calculation for daily/weekly/monthly patterns
- Handle edge cases (Feb 29, month-end, etc.)

**Files to create**:
- `addon/utils/recurrence.py`

**Implementation**:

```python
"""
Recurrence pattern utilities for chore instance generation.
"""

from datetime import date, timedelta
from typing import Optional, List
from dateutil.relativedelta import relativedelta
import calendar


def calculate_next_due_date(pattern: dict, after_date: date) -> Optional[date]:
    """
    Calculate the next due date based on recurrence pattern.

    Args:
        pattern: Recurrence pattern dict from Chore.recurrence_pattern
        after_date: Calculate next occurrence after this date

    Returns:
        Next due date, or None if no more occurrences
    """
    if not pattern:
        return None

    pattern_type = pattern.get('type')

    if pattern_type == 'daily':
        return after_date + timedelta(days=1)

    elif pattern_type == 'weekly':
        days_of_week = pattern.get('days_of_week', [])
        if not days_of_week:
            raise ValueError("Weekly pattern must have days_of_week")

        # Find next occurrence
        current = after_date + timedelta(days=1)
        for _ in range(7):  # Check next 7 days
            if current.weekday() in [d % 7 for d in days_of_week]:
                # Convert Sunday=0 to Monday=0 format
                # Pattern uses Sunday=0, Python uses Monday=0
                weekday_adjusted = [(d - 1) % 7 for d in days_of_week]
                if current.weekday() in weekday_adjusted:
                    return current
            current += timedelta(days=1)

        return None

    elif pattern_type == 'monthly':
        days_of_month = pattern.get('days_of_month', [])
        if not days_of_month:
            raise ValueError("Monthly pattern must have days_of_month")

        # Find next occurrence
        current = after_date + timedelta(days=1)

        # Check current month first
        for day in sorted(days_of_month):
            target_day = min(day, calendar.monthrange(current.year, current.month)[1])
            target_date = date(current.year, current.month, target_day)

            if target_date >= current:
                return target_date

        # Move to next month
        next_month = current + relativedelta(months=1)
        first_day = sorted(days_of_month)[0]
        target_day = min(first_day, calendar.monthrange(next_month.year, next_month.month)[1])

        return date(next_month.year, next_month.month, target_day)

    elif pattern_type == 'none':
        return None

    else:
        raise ValueError(f"Unknown recurrence pattern type: {pattern_type}")


def generate_due_dates(pattern: dict, start_date: date, end_date: date) -> List[date]:
    """
    Generate all due dates between start and end based on pattern.

    Args:
        pattern: Recurrence pattern dict
        start_date: Start of range (inclusive)
        end_date: End of range (inclusive)

    Returns:
        List of due dates
    """
    if not pattern:
        return []

    pattern_type = pattern.get('type')

    if pattern_type == 'none':
        # One-off chore
        if start_date <= end_date:
            return [start_date]
        return []

    dates = []
    current = start_date

    while current <= end_date:
        # Add current date if it matches pattern
        if matches_pattern(pattern, current):
            dates.append(current)

        # Calculate next date
        next_date = calculate_next_due_date(pattern, current)
        if next_date is None or next_date > end_date:
            break
        current = next_date

    return dates


def matches_pattern(pattern: dict, check_date: date) -> bool:
    """
    Check if a given date matches the recurrence pattern.

    Args:
        pattern: Recurrence pattern dict
        check_date: Date to check

    Returns:
        True if date matches pattern
    """
    pattern_type = pattern.get('type')

    if pattern_type == 'daily':
        return True

    elif pattern_type == 'weekly':
        days_of_week = pattern.get('days_of_week', [])
        # Convert Sunday=0 to Monday=0 format
        weekday_adjusted = [(d - 1) % 7 for d in days_of_week]
        return check_date.weekday() in weekday_adjusted

    elif pattern_type == 'monthly':
        days_of_month = pattern.get('days_of_month', [])
        # Handle month-end edge cases
        for day in days_of_month:
            target_day = min(day, calendar.monthrange(check_date.year, check_date.month)[1])
            if check_date.day == target_day:
                return True
        return False

    elif pattern_type == 'none':
        return False

    else:
        return False


def validate_recurrence_pattern(pattern: dict) -> tuple[bool, Optional[str]]:
    """
    Validate a recurrence pattern.

    Args:
        pattern: Recurrence pattern dict to validate

    Returns:
        (is_valid, error_message)
    """
    if not pattern:
        return False, "Pattern cannot be empty"

    pattern_type = pattern.get('type')

    if pattern_type not in ['daily', 'weekly', 'monthly', 'none']:
        return False, f"Invalid pattern type: {pattern_type}"

    if pattern_type == 'weekly':
        days_of_week = pattern.get('days_of_week')
        if not days_of_week or not isinstance(days_of_week, list) or len(days_of_week) == 0:
            return False, "Weekly pattern must have non-empty days_of_week array"

        if not all(isinstance(d, int) and 0 <= d <= 6 for d in days_of_week):
            return False, "days_of_week must contain integers 0-6"

    elif pattern_type == 'monthly':
        days_of_month = pattern.get('days_of_month')
        if not days_of_month or not isinstance(days_of_month, list) or len(days_of_month) == 0:
            return False, "Monthly pattern must have non-empty days_of_month array"

        if not all(isinstance(d, int) and 1 <= d <= 31 for d in days_of_month):
            return False, "days_of_month must contain integers 1-31"

    return True, None
```

**Dependencies**: Task 1

**Acceptance criteria**:
- Daily patterns generate correctly
- Weekly patterns handle days_of_week correctly (Sunday=0 convention)
- Monthly patterns handle month-end edge cases (Feb 30 → Feb 28/29)
- Validation rejects empty arrays
- All edge cases covered with unit tests

---

### Task 5: Implement Instance Generator
**Complexity**: High

**Scope**:
- Create utility for generating chore instances based on templates
- Handle individual vs shared assignment types
- Implement duplicate checking
- Calculate look-ahead window (end of month + 2 months)

**Files to create**:
- `addon/utils/instance_generator.py`

**Implementation**:

```python
"""
Chore instance generation utilities.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List
import calendar

from addon.models import db, Chore, ChoreInstance, ChoreAssignment
from addon.utils.recurrence import generate_due_dates
import logging

logger = logging.getLogger(__name__)


def calculate_lookahead_end_date() -> date:
    """
    Calculate the end date for instance generation.

    Rule: End of the month that is 2 months ahead.
    Examples:
    - Jan 1 → Mar 31
    - Jan 31 → Mar 31
    - Feb 1 → Apr 30
    """
    today = date.today()
    target_month = today + relativedelta(months=2)
    last_day = calendar.monthrange(target_month.year, target_month.month)[1]

    return date(target_month.year, target_month.month, last_day)


def check_duplicate_instance(chore_id: int, due_date: date, assigned_to: int = None) -> bool:
    """
    Check if an instance already exists.

    Args:
        chore_id: Chore template ID
        due_date: Due date for instance
        assigned_to: User ID (for individual chores) or None (for shared)

    Returns:
        True if duplicate exists, False otherwise
    """
    existing = ChoreInstance.query.filter_by(
        chore_id=chore_id,
        due_date=due_date,
        assigned_to=assigned_to
    ).first()

    return existing is not None


def generate_instances_for_chore(chore: Chore, start_date: date = None, end_date: date = None) -> List[ChoreInstance]:
    """
    Generate instances for a chore based on its recurrence pattern.

    Args:
        chore: Chore template
        start_date: Start of generation range (default: today)
        end_date: End of generation range (default: lookahead window)

    Returns:
        List of newly created instances
    """
    if not chore.is_active:
        logger.info(f"Chore {chore.id} is inactive, skipping generation")
        return []

    if start_date is None:
        start_date = date.today()

    if end_date is None:
        end_date = calculate_lookahead_end_date()

    # Respect chore's start_date and end_date
    if chore.start_date and start_date < chore.start_date:
        start_date = chore.start_date

    if chore.end_date and end_date > chore.end_date:
        end_date = chore.end_date

    # Handle one-off chores
    if chore.recurrence_type == 'none':
        if chore.start_date:
            due_dates = [chore.start_date] if chore.start_date >= start_date and chore.start_date <= end_date else []
        else:
            # No due date (anytime chore)
            due_dates = [None]
    else:
        # Recurring chore
        due_dates = generate_due_dates(chore.recurrence_pattern, start_date, end_date)

    instances = []

    for due_date in due_dates:
        if chore.assignment_type == 'individual':
            # Create one instance per assigned kid
            for assignment in chore.assignments:
                if not check_duplicate_instance(chore.id, due_date, assignment.user_id):
                    instance = ChoreInstance(
                        chore_id=chore.id,
                        due_date=due_date,
                        assigned_to=assignment.user_id,
                        status='assigned'
                    )
                    db.session.add(instance)
                    instances.append(instance)
                    logger.debug(f"Created individual instance: chore={chore.id}, due={due_date}, user={assignment.user_id}")

        else:  # shared
            # Create one instance total
            if not check_duplicate_instance(chore.id, due_date, None):
                instance = ChoreInstance(
                    chore_id=chore.id,
                    due_date=due_date,
                    assigned_to=None,
                    status='assigned'
                )
                db.session.add(instance)
                instances.append(instance)
                logger.debug(f"Created shared instance: chore={chore.id}, due={due_date}")

    db.session.commit()
    logger.info(f"Generated {len(instances)} instances for chore {chore.id}")

    return instances


def delete_future_instances(chore: Chore) -> int:
    """
    Delete future assigned instances for a chore (used when schedule changes).

    Only deletes instances with status='assigned' and due_date >= today.
    Preserves claimed/approved/rejected instances for history.

    Args:
        chore: Chore template

    Returns:
        Number of instances deleted
    """
    today = date.today()

    deleted = ChoreInstance.query.filter(
        ChoreInstance.chore_id == chore.id,
        ChoreInstance.status == 'assigned',
        ChoreInstance.due_date >= today
    ).delete()

    db.session.commit()
    logger.info(f"Deleted {deleted} future instances for chore {chore.id}")

    return deleted


def regenerate_instances_for_chore(chore: Chore) -> List[ChoreInstance]:
    """
    Delete and regenerate instances (used when chore schedule is modified).

    Args:
        chore: Chore template

    Returns:
        List of newly created instances
    """
    deleted_count = delete_future_instances(chore)
    logger.info(f"Regenerating instances for chore {chore.id} (deleted {deleted_count})")

    instances = generate_instances_for_chore(chore)

    return instances
```

**Dependencies**: Task 4

**Acceptance criteria**:
- Generates instances for individual chores (one per kid)
- Generates instances for shared chores (one total)
- Correctly calculates look-ahead window
- Prevents duplicates
- Respects chore start_date and end_date
- Handles one-off chores (with and without due_date)
- `delete_future_instances()` only deletes assigned instances
- `regenerate_instances_for_chore()` works correctly

---

### Task 6: Update Chore Claim Logic
**Complexity**: Medium

**Scope**:
- Update claim endpoint to set `claimed_late` flag
- Validate claiming rules (due date check)

**Files to modify**:
- `addon/routes/instances.py`

**Changes required**:

Update the claim endpoint:

```python
@instances_bp.route('/<int:instance_id>/claim', methods=['POST'])
@ha_auth_required
def claim_instance(instance_id, current_user):
    """Claim a chore instance."""

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    instance = ChoreInstance.query.get_or_404(instance_id)

    # Validate user can claim
    if not instance.can_claim(user_id):
        return jsonify({'error': 'Cannot claim this chore instance'}), 403

    # Update instance
    instance.status = 'claimed'
    instance.claimed_by = user_id
    instance.claimed_at = datetime.utcnow()

    # Check if late
    if instance.due_date and datetime.utcnow().date() > instance.due_date:
        instance.claimed_late = True

    db.session.commit()

    # Fire webhook
    from addon.utils.webhooks import fire_webhook
    fire_webhook('chore_instance_claimed', instance)

    return jsonify(instance.to_dict()), 200
```

**Dependencies**: Task 2

**Acceptance criteria**:
- Claims set `claimed_late=True` when claimed after due_date
- Claims fail if instance is not claimable (status, due_date, assignment)
- Webhook fires on successful claim
- Existing tests updated

---

### Task 7: Update Approval Logic
**Complexity**: Medium

**Scope**:
- Update approval endpoint to accept points override
- Fire webhooks for approval and points awarded

**Files to modify**:
- `addon/routes/instances.py`

**Changes required**:

```python
@instances_bp.route('/<int:instance_id>/approve', methods=['POST'])
@ha_auth_required
def approve_instance(instance_id, current_user):
    """Approve a claimed chore instance and award points."""

    data = request.get_json()
    approver_id = data.get('approver_id')
    points_override = data.get('points')  # Optional parent override

    if not approver_id:
        return jsonify({'error': 'approver_id is required'}), 400

    instance = ChoreInstance.query.get_or_404(instance_id)

    # Validate
    if not instance.can_approve(approver_id):
        return jsonify({'error': 'Cannot approve this chore instance'}), 403

    # Award points (handles late_points logic internally)
    instance.award_points(approver_id, points=points_override)

    db.session.commit()

    # Fire webhooks
    from addon.utils.webhooks import fire_webhook
    fire_webhook('chore_instance_approved', instance)
    fire_webhook('points_awarded', instance)

    return jsonify(instance.to_dict()), 200
```

**Dependencies**: Task 2

**Acceptance criteria**:
- Accepts optional `points` parameter
- Uses late_points when claimed_late=True and late_points is set
- Respects points override from parent
- Fires both approval and points_awarded webhooks
- Points transaction recorded in PointsHistory

---

### Task 8: Implement Reward Approval Workflow
**Complexity**: Medium

**Scope**:
- Update reward claim endpoint to handle approval workflow
- Set expires_at for pending claims
- Implement unclaim endpoint

**Files to modify**:
- `addon/routes/rewards.py`

**Changes required**:

1. **Update claim endpoint**:
```python
@rewards_bp.route('/<int:reward_id>/claim', methods=['POST'])
@ha_auth_required
def claim_reward(reward_id, current_user):
    """Claim a reward."""

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    reward = Reward.query.get_or_404(reward_id)
    user = User.query.get_or_404(user_id)

    # Validate
    can_claim, reason = reward.can_claim(user_id)
    if not can_claim:
        return jsonify({'error': reason}), 400

    # Create claim
    claim = RewardClaim(
        reward_id=reward.id,
        user_id=user_id,
        points_spent=reward.points_cost,
        status='pending' if reward.requires_approval else 'approved',
        claimed_at=datetime.utcnow()
    )

    # Set expiration for pending claims
    if reward.requires_approval:
        claim.expires_at = datetime.utcnow() + timedelta(days=7)

    db.session.add(claim)

    # Deduct points immediately (optimistic)
    user.adjust_points(
        delta=-reward.points_cost,
        reason=f"Claimed reward: {reward.name}",
        reward_claim_id=claim.id
    )

    db.session.commit()

    # Fire webhook
    from addon.utils.webhooks import fire_webhook
    fire_webhook('reward_claimed', claim)

    return jsonify(claim.to_dict()), 201
```

2. **Add unclaim endpoint**:
```python
@rewards_bp.route('/claims/<int:claim_id>/unclaim', methods=['POST'])
@ha_auth_required
def unclaim_reward(claim_id, current_user):
    """Unclaim a pending reward."""

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    claim = RewardClaim.query.get_or_404(claim_id)

    # Validate
    if claim.user_id != user_id:
        return jsonify({'error': 'Not your claim'}), 403

    if claim.status != 'pending':
        return jsonify({'error': 'Can only unclaim pending rewards'}), 400

    # Refund points
    user = User.query.get(user_id)
    user.adjust_points(
        delta=claim.points_spent,
        reason=f"Unclaimed reward: {claim.reward.name}",
        reward_claim_id=claim.id
    )

    # Delete claim
    db.session.delete(claim)
    db.session.commit()

    return jsonify({'message': 'Reward unclaimed, points refunded'}), 200
```

3. **Update approve/reject endpoints**:
```python
@rewards_bp.route('/claims/<int:claim_id>/approve', methods=['POST'])
@ha_auth_required
def approve_reward_claim(claim_id, current_user):
    """Approve a pending reward claim."""

    data = request.get_json()
    approver_id = data.get('approver_id')

    claim = RewardClaim.query.get_or_404(claim_id)

    # Validate
    approver = User.query.get(approver_id)
    if not approver or approver.role != 'parent':
        return jsonify({'error': 'Only parents can approve rewards'}), 403

    if claim.status != 'pending':
        return jsonify({'error': 'Claim is not pending'}), 400

    # Approve
    claim.status = 'approved'
    claim.approved_by = approver_id
    claim.approved_at = datetime.utcnow()
    claim.expires_at = None

    db.session.commit()

    # Fire webhook
    from addon.utils.webhooks import fire_webhook
    fire_webhook('reward_approved', claim)

    return jsonify(claim.to_dict()), 200


@rewards_bp.route('/claims/<int:claim_id>/reject', methods=['POST'])
@ha_auth_required
def reject_reward_claim(claim_id, current_user):
    """Reject a pending reward claim and refund points."""

    data = request.get_json()
    approver_id = data.get('approver_id')

    claim = RewardClaim.query.get_or_404(claim_id)

    # Validate
    approver = User.query.get(approver_id)
    if not approver or approver.role != 'parent':
        return jsonify({'error': 'Only parents can reject rewards'}), 403

    if claim.status != 'pending':
        return jsonify({'error': 'Claim is not pending'}), 400

    # Reject and refund
    claim.status = 'rejected'
    claim.approved_by = approver_id
    claim.approved_at = datetime.utcnow()
    claim.expires_at = None

    user = User.query.get(claim.user_id)
    user.adjust_points(
        delta=claim.points_spent,
        reason=f"Reward claim rejected: {claim.reward.name}",
        created_by_id=approver_id,
        reward_claim_id=claim.id
    )

    db.session.commit()

    # Fire webhook
    from addon.utils.webhooks import fire_webhook
    fire_webhook('reward_rejected', claim, reason='manual')

    return jsonify(claim.to_dict()), 200
```

**Dependencies**: Task 1, Task 2

**Acceptance criteria**:
- Claims set `expires_at` for pending rewards
- Points deducted immediately on claim
- Unclaim refunds points and deletes claim
- Approve keeps points deducted
- Reject refunds points
- Webhooks fire correctly

---

### Task 9: Add Instance Unclaim and Reassign Endpoints
**Complexity**: Low

**Scope**:
- Add endpoint for kids to unclaim instances
- Add endpoint for parents to reassign instances

**Files to modify**:
- `addon/routes/instances.py`

**Implementation**:

```python
@instances_bp.route('/<int:instance_id>/unclaim', methods=['POST'])
@ha_auth_required
def unclaim_instance(instance_id, current_user):
    """Unclaim a chore instance (before approval)."""

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    instance = ChoreInstance.query.get_or_404(instance_id)

    # Validate
    if instance.claimed_by != user_id:
        return jsonify({'error': 'Not your claim'}), 403

    if instance.status != 'claimed':
        return jsonify({'error': 'Can only unclaim pending instances'}), 400

    # Unclaim
    instance.status = 'assigned'
    instance.claimed_by = None
    instance.claimed_at = None
    instance.claimed_late = False

    db.session.commit()

    return jsonify(instance.to_dict()), 200


@instances_bp.route('/<int:instance_id>/reassign', methods=['POST'])
@ha_auth_required
def reassign_instance(instance_id, current_user):
    """Reassign a chore instance to a different kid (parents only)."""

    data = request.get_json()
    new_user_id = data.get('new_user_id')
    reassigned_by = data.get('reassigned_by')

    if not new_user_id or not reassigned_by:
        return jsonify({'error': 'new_user_id and reassigned_by are required'}), 400

    instance = ChoreInstance.query.get_or_404(instance_id)

    # Validate
    reassigner = User.query.get(reassigned_by)
    if not reassigner or reassigner.role != 'parent':
        return jsonify({'error': 'Only parents can reassign chores'}), 403

    if instance.status != 'assigned':
        return jsonify({'error': 'Can only reassign unclaimed instances'}), 400

    if instance.chore.assignment_type != 'individual':
        return jsonify({'error': 'Can only reassign individual chores'}), 400

    new_user = User.query.get(new_user_id)
    if not new_user or new_user.role != 'kid':
        return jsonify({'error': 'New assignee must be a kid'}), 400

    # Reassign
    instance.assigned_to = new_user_id

    # Ensure ChoreAssignment exists
    assignment = ChoreAssignment.query.filter_by(
        chore_id=instance.chore_id,
        user_id=new_user_id
    ).first()

    if not assignment:
        assignment = ChoreAssignment(
            chore_id=instance.chore_id,
            user_id=new_user_id
        )
        db.session.add(assignment)

    db.session.commit()

    return jsonify(instance.to_dict()), 200
```

**Dependencies**: Task 2

**Acceptance criteria**:
- Kids can unclaim their own claimed instances
- Parents can reassign assigned instances
- Reassignment only works for individual chores
- Reassignment creates ChoreAssignment if needed

---

## Phase 3: Background Jobs

### Task 10: Set Up APScheduler
**Complexity**: Low

**Scope**:
- Install APScheduler
- Configure scheduler in Flask app
- Create scheduler initialization module

**Files to create/modify**:
- `addon/requirements.txt` (add APScheduler)
- `addon/scheduler.py` (new file)
- `addon/app.py` (integrate scheduler)

**Implementation**:

1. **Add to requirements.txt**:
```
APScheduler==3.10.4
```

2. **Create `addon/scheduler.py`**:
```python
"""
Background job scheduler using APScheduler.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def init_scheduler(app):
    """Initialize and start the background scheduler."""

    if app.config.get('SCHEDULER_ENABLED', True):
        # Import job functions
        from addon.jobs.instance_generator import generate_daily_instances
        from addon.jobs.auto_approval import check_auto_approvals
        from addon.jobs.missed_instances import mark_missed_instances
        from addon.jobs.reward_expiration import expire_pending_rewards
        from addon.jobs.points_audit import audit_points_balances

        # Schedule jobs
        scheduler.add_job(
            generate_daily_instances,
            trigger=CronTrigger(hour=0, minute=0),
            id='daily_instance_generation',
            name='Generate daily chore instances',
            replace_existing=True
        )

        scheduler.add_job(
            check_auto_approvals,
            trigger=IntervalTrigger(minutes=5),
            id='auto_approval_check',
            name='Check for auto-approvals',
            replace_existing=True
        )

        scheduler.add_job(
            mark_missed_instances,
            trigger=CronTrigger(minute=30),  # Every hour at :30
            id='mark_missed_instances',
            name='Mark missed chore instances',
            replace_existing=True
        )

        scheduler.add_job(
            expire_pending_rewards,
            trigger=CronTrigger(hour=0, minute=1),
            id='expire_pending_rewards',
            name='Expire pending reward claims',
            replace_existing=True
        )

        scheduler.add_job(
            audit_points_balances,
            trigger=CronTrigger(hour=2, minute=0),
            id='audit_points_balances',
            name='Audit user points balances',
            replace_existing=True
        )

        scheduler.start()
        logger.info("Background scheduler started")
    else:
        logger.info("Background scheduler disabled")


def shutdown_scheduler():
    """Shutdown the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
```

3. **Update `addon/app.py`**:
```python
from addon.scheduler import init_scheduler, shutdown_scheduler
import atexit

# ... existing code ...

# Initialize scheduler
init_scheduler(app)

# Shutdown scheduler on app exit
atexit.register(shutdown_scheduler)
```

**Dependencies**: None

**Acceptance criteria**:
- APScheduler installed
- Scheduler starts with Flask app
- Scheduler shuts down gracefully
- Can be disabled via config for testing

---

### Task 11: Implement Daily Instance Generator Job
**Complexity**: Medium

**Scope**:
- Create background job to generate instances daily
- Fire webhooks for instances due today

**Files to create**:
- `addon/jobs/instance_generator.py`

**Implementation**:

```python
"""
Daily instance generation job.
"""

from datetime import date
from addon.models import db, Chore
from addon.utils.instance_generator import generate_instances_for_chore, calculate_lookahead_end_date
from addon.utils.webhooks import fire_webhook
import logging

logger = logging.getLogger(__name__)


def generate_daily_instances():
    """
    Generate chore instances for all active chores.

    Runs daily at midnight. Generates instances through the look-ahead window
    (end of month + 2 months). Fires webhooks only for instances due today.
    """
    logger.info("Starting daily instance generation")

    with db.app.app_context():
        active_chores = Chore.query.filter_by(is_active=True).all()

        today = date.today()
        end_date = calculate_lookahead_end_date()

        total_instances = 0
        webhooks_fired = 0

        for chore in active_chores:
            try:
                instances = generate_instances_for_chore(chore, start_date=today, end_date=end_date)
                total_instances += len(instances)

                # Fire webhooks only for instances due today or NULL due date
                for instance in instances:
                    if instance.due_date == today or instance.due_date is None:
                        fire_webhook('chore_instance_created', instance)
                        webhooks_fired += 1

            except Exception as e:
                logger.error(f"Error generating instances for chore {chore.id}: {e}")
                db.session.rollback()

        logger.info(f"Daily instance generation complete: {total_instances} instances created, {webhooks_fired} webhooks fired")
```

**Dependencies**: Task 5, Task 10

**Acceptance criteria**:
- Runs daily at midnight
- Generates instances for all active chores
- Only fires webhooks for instances due today or NULL due date
- Handles errors gracefully (continues on error)

---

### Task 12: Implement Auto-Approval Checker Job
**Complexity**: Medium

**Scope**:
- Create job to check for auto-approval eligibility
- Award points via system user

**Files to create**:
- `addon/jobs/auto_approval.py`

**Implementation**:

```python
"""
Auto-approval checker job.
"""

from datetime import datetime
from addon.models import db, ChoreInstance, Chore, User
from addon.utils.webhooks import fire_webhook
import logging

logger = logging.getLogger(__name__)


def check_auto_approvals():
    """
    Check for chore instances eligible for auto-approval.

    Runs every 5 minutes. Auto-approves claimed instances that have exceeded
    the auto-approval window.
    """
    logger.debug("Checking for auto-approvals")

    with db.app.app_context():
        # Find eligible instances
        eligible = ChoreInstance.query.filter(
            ChoreInstance.status == 'claimed'
        ).join(Chore).filter(
            Chore.auto_approve_after_hours.isnot(None)
        ).all()

        system_user = User.query.filter_by(ha_user_id='system').first()

        if not system_user:
            logger.error("System user not found, cannot auto-approve")
            return

        approved_count = 0

        for instance in eligible:
            try:
                hours_since_claim = (datetime.utcnow() - instance.claimed_at).total_seconds() / 3600

                if hours_since_claim >= instance.chore.auto_approve_after_hours:
                    # Auto-approve
                    instance.award_points(approver_id=system_user.id)
                    db.session.commit()

                    logger.info(f"Auto-approved instance {instance.id} after {hours_since_claim:.1f} hours")

                    # Fire webhooks
                    fire_webhook('chore_instance_approved', instance, auto_approved=True)
                    fire_webhook('points_awarded', instance)

                    approved_count += 1

            except Exception as e:
                logger.error(f"Error auto-approving instance {instance.id}: {e}")
                db.session.rollback()

        if approved_count > 0:
            logger.info(f"Auto-approved {approved_count} instances")
```

**Dependencies**: Task 3, Task 10

**Acceptance criteria**:
- Runs every 5 minutes
- Auto-approves eligible instances
- Uses system user as approver
- Fires webhooks correctly
- Handles errors gracefully

---

### Task 13: Implement Missed Instance Marker Job
**Complexity**: Low

**Scope**:
- Create job to mark overdue instances as missed

**Files to create**:
- `addon/jobs/missed_instances.py`

**Implementation**:

```python
"""
Missed instance marker job.
"""

from datetime import date
from addon.models import db, ChoreInstance, Chore
import logging

logger = logging.getLogger(__name__)


def mark_missed_instances():
    """
    Mark overdue assigned instances as missed.

    Runs hourly. Transitions instances to 'missed' status if:
    - status = 'assigned'
    - due_date < today
    - chore.allow_late_claims = False
    """
    logger.debug("Checking for missed instances")

    with db.app.app_context():
        today = date.today()

        # Find overdue assigned instances
        overdue = ChoreInstance.query.filter(
            ChoreInstance.status == 'assigned',
            ChoreInstance.due_date < today,
            ChoreInstance.due_date.isnot(None)
        ).join(Chore).filter(
            Chore.allow_late_claims == False
        ).all()

        for instance in overdue:
            instance.status = 'missed'

        db.session.commit()

        if len(overdue) > 0:
            logger.info(f"Marked {len(overdue)} instances as missed")
```

**Dependencies**: Task 10

**Acceptance criteria**:
- Runs hourly
- Only marks instances where late claims not allowed
- Preserves instances with NULL due_date
- Only affects assigned status

---

### Task 14: Implement Reward Expiration and Points Audit Jobs
**Complexity**: Medium

**Scope**:
- Create job to expire pending reward claims
- Create job to audit points balances

**Files to create**:
- `addon/jobs/reward_expiration.py`
- `addon/jobs/points_audit.py`

**Implementation**:

1. **`addon/jobs/reward_expiration.py`**:
```python
"""
Pending reward expiration job.
"""

from datetime import datetime
from addon.models import db, RewardClaim, User
from addon.utils.webhooks import fire_webhook
import logging

logger = logging.getLogger(__name__)


def expire_pending_rewards():
    """
    Expire pending reward claims after 7 days.

    Runs daily at 00:01. Auto-rejects pending claims that have exceeded
    their expiration date and refunds points.
    """
    logger.info("Checking for expired reward claims")

    with db.app.app_context():
        expired = RewardClaim.query.filter(
            RewardClaim.status == 'pending',
            RewardClaim.expires_at <= datetime.utcnow()
        ).all()

        for claim in expired:
            try:
                claim.status = 'rejected'

                # Refund points
                user = User.query.get(claim.user_id)
                user.adjust_points(
                    delta=claim.points_spent,
                    reason=f"Reward claim expired: {claim.reward.name}",
                    reward_claim_id=claim.id
                )

                logger.info(f"Expired reward claim {claim.id}, refunded {claim.points_spent} points to user {user.id}")

                # Fire webhook
                fire_webhook('reward_rejected', claim, reason='expired')

            except Exception as e:
                logger.error(f"Error expiring claim {claim.id}: {e}")
                db.session.rollback()

        db.session.commit()

        if len(expired) > 0:
            logger.info(f"Expired {len(expired)} pending reward claims")
```

2. **`addon/jobs/points_audit.py`**:
```python
"""
Points balance audit job.
"""

from addon.models import db, User
import logging

logger = logging.getLogger(__name__)


def audit_points_balances():
    """
    Audit all users' points balances against history.

    Runs nightly at 02:00. Verifies that denormalized points field
    matches calculated total from PointsHistory.
    """
    logger.info("Starting points balance audit")

    with db.app.app_context():
        users = User.query.filter_by(role='kid').all()
        discrepancies = []

        for user in users:
            if not user.verify_points_balance():
                calculated = user.calculate_current_points()
                discrepancies.append({
                    'user_id': user.id,
                    'username': user.username,
                    'stored': user.points,
                    'calculated': calculated,
                    'diff': user.points - calculated
                })

        if discrepancies:
            logger.error(f"Points discrepancies found: {discrepancies}")
            # Future: send alert to admin, auto-heal, etc.
        else:
            logger.info("Points audit complete: all balances verified")
```

**Dependencies**: Task 10

**Acceptance criteria**:
- Reward expiration runs daily at 00:01
- Expired claims are rejected and refunded
- Points audit runs nightly at 02:00
- Discrepancies are logged
- Both jobs handle errors gracefully

---

## Phase 4: API Endpoints

### Task 15: Update Chore Create Endpoint
**Complexity**: Medium

**Scope**:
- Add validation for recurrence patterns
- Generate instances on creation
- Fire webhooks for instances due today

**Files to modify**:
- `addon/routes/chores.py`

**Changes**:

```python
from addon.utils.recurrence import validate_recurrence_pattern
from addon.utils.instance_generator import generate_instances_for_chore
from addon.utils.webhooks import fire_webhook

@chores_bp.route('', methods=['POST'])
@ha_auth_required
def create_chore(current_user):
    """Create a new chore."""

    data = request.get_json()

    # Validate recurrence pattern
    if 'recurrence_pattern' in data:
        valid, error = validate_recurrence_pattern(data['recurrence_pattern'])
        if not valid:
            return jsonify({'error': error}), 400

    # Validate new fields
    if data.get('late_points') is not None and data.get('late_points') < 0:
        return jsonify({'error': 'late_points must be non-negative'}), 400

    # Create chore
    chore = Chore(
        name=data['name'],
        description=data.get('description'),
        points=data.get('points', 0),
        recurrence_type=data.get('recurrence_type'),
        recurrence_pattern=data.get('recurrence_pattern'),
        assignment_type=data.get('assignment_type'),
        requires_approval=data.get('requires_approval', True),
        auto_approve_after_hours=data.get('auto_approve_after_hours'),
        allow_late_claims=data.get('allow_late_claims', False),
        late_points=data.get('late_points'),
        created_by=current_user.id
    )

    db.session.add(chore)
    db.session.commit()

    # Create assignments
    if 'assigned_users' in data:
        for user_id in data['assigned_users']:
            assignment = ChoreAssignment(chore_id=chore.id, user_id=user_id)
            db.session.add(assignment)

    db.session.commit()

    # Generate instances
    today = date.today()
    instances = generate_instances_for_chore(chore)

    # Fire webhooks for instances due today
    for instance in instances:
        if instance.due_date == today or instance.due_date is None:
            fire_webhook('chore_instance_created', instance)

    return jsonify(chore.to_dict()), 201
```

**Dependencies**: Task 4, Task 5

**Acceptance criteria**:
- Validates recurrence patterns
- Validates new fields (allow_late_claims, late_points)
- Generates instances on creation
- Fires webhooks for instances due today
- Existing tests updated

---

### Task 16: Update Chore Update Endpoint
**Complexity**: High

**Scope**:
- Detect recurrence pattern changes
- Delete and regenerate instances when pattern changes
- Handle other field updates

**Files to modify**:
- `addon/routes/chores.py`

**Changes**:

```python
from addon.utils.instance_generator import regenerate_instances_for_chore

@chores_bp.route('/<int:chore_id>', methods=['PUT'])
@ha_auth_required
def update_chore(chore_id, current_user):
    """Update a chore."""

    chore = Chore.query.get_or_404(chore_id)
    data = request.get_json()

    # Validate recurrence pattern if changed
    if 'recurrence_pattern' in data:
        valid, error = validate_recurrence_pattern(data['recurrence_pattern'])
        if not valid:
            return jsonify({'error': error}), 400

    # Check if recurrence pattern changed
    pattern_changed = False
    if 'recurrence_type' in data and data['recurrence_type'] != chore.recurrence_type:
        pattern_changed = True
    if 'recurrence_pattern' in data and data['recurrence_pattern'] != chore.recurrence_pattern:
        pattern_changed = True

    # Update fields
    for field in ['name', 'description', 'points', 'recurrence_type', 'recurrence_pattern',
                  'assignment_type', 'requires_approval', 'auto_approve_after_hours',
                  'allow_late_claims', 'late_points', 'is_active']:
        if field in data:
            setattr(chore, field, data[field])

    db.session.commit()

    # Regenerate instances if pattern changed
    if pattern_changed:
        today = date.today()
        instances = regenerate_instances_for_chore(chore)

        # Fire webhooks for new instances due today
        for instance in instances:
            if instance.due_date == today or instance.due_date is None:
                fire_webhook('chore_instance_created', instance)

    return jsonify(chore.to_dict()), 200
```

**Dependencies**: Task 5

**Acceptance criteria**:
- Detects recurrence pattern changes
- Deletes future assigned instances
- Regenerates instances based on new pattern
- Preserves claimed/approved instances
- Fires webhooks for new instances due today

---

### Task 17: Add Get Instances Due Today Endpoint
**Complexity**: Low

**Scope**:
- Create new endpoint for HA sensors to poll

**Files to modify**:
- `addon/routes/instances.py`

**Implementation**:

```python
@instances_bp.route('/due-today', methods=['GET'])
@ha_auth_required
def get_instances_due_today(current_user):
    """
    Get all chore instances due today or with no due date.

    Query params:
    - user_id: Filter by assigned user (optional)
    - status: Filter by status (optional)
    """

    today = date.today()

    query = ChoreInstance.query.filter(
        db.or_(
            ChoreInstance.due_date == today,
            ChoreInstance.due_date.is_(None)
        )
    )

    # Optional filters
    user_id = request.args.get('user_id', type=int)
    if user_id:
        query = query.filter(
            db.or_(
                ChoreInstance.assigned_to == user_id,
                ChoreInstance.assigned_to.is_(None)  # Include shared chores
            )
        )

    status = request.args.get('status')
    if status:
        query = query.filter(ChoreInstance.status == status)

    instances = query.all()

    return jsonify({
        'date': today.isoformat(),
        'count': len(instances),
        'instances': [instance.to_dict() for instance in instances]
    }), 200
```

**Dependencies**: None

**Acceptance criteria**:
- Returns instances due today
- Returns instances with NULL due_date
- Supports filtering by user_id and status
- Returns proper JSON format

---

### Task 18: Update Reward Create/Update Endpoints
**Complexity**: Low

**Scope**:
- Add support for `requires_approval` field

**Files to modify**:
- `addon/routes/rewards.py`

**Changes**:

```python
@rewards_bp.route('', methods=['POST'])
@ha_auth_required
def create_reward(current_user):
    """Create a new reward."""

    data = request.get_json()

    reward = Reward(
        name=data['name'],
        description=data.get('description'),
        points_cost=data['points_cost'],
        cooldown_days=data.get('cooldown_days'),
        max_claims_total=data.get('max_claims_total'),
        max_claims_per_kid=data.get('max_claims_per_kid'),
        requires_approval=data.get('requires_approval', False)  # NEW
    )

    db.session.add(reward)
    db.session.commit()

    return jsonify(reward.to_dict()), 201


@rewards_bp.route('/<int:reward_id>', methods=['PUT'])
@ha_auth_required
def update_reward(reward_id, current_user):
    """Update a reward."""

    reward = Reward.query.get_or_404(reward_id)
    data = request.get_json()

    for field in ['name', 'description', 'points_cost', 'cooldown_days',
                  'max_claims_total', 'max_claims_per_kid', 'requires_approval', 'is_active']:
        if field in data:
            setattr(reward, field, data[field])

    db.session.commit()

    return jsonify(reward.to_dict()), 200
```

**Dependencies**: Task 1

**Acceptance criteria**:
- Create endpoint accepts `requires_approval`
- Update endpoint accepts `requires_approval`
- Field defaults to False

---

### Task 19: Update Points Adjustment Endpoint
**Complexity**: Low

**Scope**:
- Fire webhook when points are manually adjusted

**Files to modify**:
- `addon/routes/points.py`

**Changes**:

```python
from addon.utils.webhooks import fire_webhook

@points_bp.route('/adjust', methods=['POST'])
@ha_auth_required
def adjust_points(current_user):
    """Manually adjust a user's points (parent only)."""

    data = request.get_json()

    # ... existing validation ...

    user.adjust_points(
        delta=delta,
        reason=reason,
        created_by_id=created_by
    )

    db.session.commit()

    # Fire webhook
    fire_webhook('points_awarded', user, delta=delta, reason=reason)

    return jsonify(user.to_dict()), 200
```

**Dependencies**: Task 22

**Acceptance criteria**:
- Fires webhook on manual adjustment
- Supports negative deltas
- Webhook includes reason

---

### Task 20: Add to_dict() Methods for Webhook Serialization
**Complexity**: Low

**Scope**:
- Ensure all models have `to_dict()` methods for JSON serialization

**Files to modify**:
- `addon/models.py`

**Add to each model**:

```python
# ChoreInstance
def to_dict(self):
    return {
        'id': self.id,
        'chore_id': self.chore_id,
        'chore_name': self.chore.name if self.chore else None,
        'due_date': self.due_date.isoformat() if self.due_date else None,
        'status': self.status,
        'assigned_to': self.assigned_to,
        'assigned_to_name': User.query.get(self.assigned_to).username if self.assigned_to else None,
        'claimed_by': self.claimed_by,
        'claimed_by_name': User.query.get(self.claimed_by).username if self.claimed_by else None,
        'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
        'claimed_late': self.claimed_late,
        'approved_by': self.approved_by,
        'approved_at': self.approved_at.isoformat() if self.approved_at else None,
        'points_awarded': self.points_awarded,
        # ... etc
    }

# Similar for Reward, RewardClaim, User, etc.
```

**Dependencies**: None

**Acceptance criteria**:
- All models have `to_dict()` methods
- Methods handle None values
- Methods include related object names (not just IDs)

---

### Task 21: Add Verification After Points Transactions
**Complexity**: Low

**Scope**:
- Run points verification after each transaction

**Files to modify**:
- `addon/models.py` (User.adjust_points method)

**Changes**:

```python
def adjust_points(self, delta: int, reason: str, created_by_id: Optional[int] = None,
                 chore_instance_id: Optional[int] = None, reward_claim_id: Optional[int] = None) -> None:
    """Adjust user's points and create history entry."""

    # Prevent negative balance
    if self.points + delta < 0:
        raise ValueError(f"Insufficient points: cannot adjust by {delta} (current balance: {self.points})")

    self.points += delta

    history = PointsHistory(
        user_id=self.id,
        points_delta=delta,
        reason=reason,
        created_by=created_by_id,
        chore_instance_id=chore_instance_id,
        reward_claim_id=reward_claim_id
    )
    db.session.add(history)

    # Verify balance after transaction
    if not self.verify_points_balance():
        calculated = self.calculate_current_points()
        logger.error(f"Points mismatch for user {self.id}: stored={self.points}, calculated={calculated}")
        # For now, just log. Future: auto-heal or alert
```

**Dependencies**: None

**Acceptance criteria**:
- Prevents negative balances
- Verifies balance after each adjustment
- Logs discrepancies

---

## Phase 5: Webhook Integration

### Task 22: Implement Webhook Utility
**Complexity**: Medium

**Scope**:
- Create webhook firing utility
- Handle payload serialization
- Handle delivery failures gracefully

**Files to create**:
- `addon/utils/webhooks.py`
- Update `addon/config.py` (add webhook URL setting)

**Implementation**:

```python
"""
Webhook utilities for Home Assistant integration.
"""

import requests
from datetime import datetime
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def get_webhook_url() -> Optional[str]:
    """Get the configured webhook URL."""
    from addon.config import Config
    return Config.HA_WEBHOOK_URL


def build_payload(event_name: str, obj: Any, **kwargs) -> dict:
    """
    Build webhook payload for an event.

    Args:
        event_name: Name of the event
        obj: Model instance (ChoreInstance, RewardClaim, User, etc.)
        **kwargs: Additional event-specific data

    Returns:
        Webhook payload dict
    """
    payload = {
        'event': event_name,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'data': {}
    }

    # Build data based on object type
    if hasattr(obj, 'to_dict'):
        payload['data'] = obj.to_dict()

    # Add any additional kwargs
    payload['data'].update(kwargs)

    return payload


def fire_webhook(event_name: str, obj: Any, **kwargs) -> bool:
    """
    Fire a webhook to Home Assistant.

    Args:
        event_name: Name of the event
        obj: Model instance
        **kwargs: Additional event-specific data

    Returns:
        True if successful, False otherwise
    """
    webhook_url = get_webhook_url()

    if not webhook_url:
        logger.warning("Webhook URL not configured, skipping webhook")
        return False

    payload = build_payload(event_name, obj, **kwargs)

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=5  # Don't block for too long
        )
        response.raise_for_status()

        logger.info(f"Webhook fired: {event_name} (status {response.status_code})")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Webhook delivery timeout for event: {event_name}")
        return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Webhook delivery failed for event {event_name}: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error firing webhook {event_name}: {e}")
        return False
```

**Update `addon/config.py`**:

```python
class Config:
    # ... existing config ...

    HA_WEBHOOK_URL = os.getenv('HA_WEBHOOK_URL')
    # Example: http://homeassistant.local:8123/api/webhook/chorecontrol-abc123
```

**Dependencies**: Task 20

**Acceptance criteria**:
- Fires HTTP POST to configured URL
- Includes proper event name and timestamp
- Serializes model objects correctly
- Handles timeouts gracefully
- Logs failures without crashing

---

### Task 23: Add Webhooks to All Event Points
**Complexity**: Low

**Scope**:
- Ensure all 8 webhook events are fired at correct times
- Review: Tasks 6, 7, 8, 11, 12, 14, 15, 16, 19 already include webhooks

**Verification checklist**:
- [x] `chore_instance_created` - Task 11, 15, 16
- [x] `chore_instance_claimed` - Task 6
- [x] `chore_instance_approved` - Task 7, 12
- [x] `chore_instance_rejected` - (Already in existing routes/instances.py)
- [x] `points_awarded` - Task 7, 19
- [x] `reward_claimed` - Task 8
- [x] `reward_approved` - Task 8
- [x] `reward_rejected` - Task 8, 14

**Dependencies**: Task 22

**Acceptance criteria**:
- All 8 webhook types fire correctly
- Payloads match specification
- Error handling in place

---

## Phase 6: Testing

### Task 24: Update Existing API Tests
**Complexity**: Medium

**Scope**:
- Update existing test files to account for new fields and logic
- Fix broken tests from model changes

**Files to modify**:
- `addon/tests/test_chores.py`
- `addon/tests/test_instances.py`
- `addon/tests/test_rewards.py`
- `addon/tests/test_users.py`
- `addon/tests/test_points.py`

**Changes needed**:
- Update test data to include new fields
- Update assertions for new behavior
- Mock webhook calls

**Dependencies**: All previous tasks

**Acceptance criteria**:
- All existing tests pass
- No deprecation warnings
- Tests cover new fields

---

### Task 25: Write Unit Tests for Recurrence Logic
**Complexity**: Medium

**Scope**:
- Test recurrence pattern calculation
- Test edge cases (Feb 29, month-end, etc.)

**Files to create**:
- `addon/tests/test_recurrence.py`

**Test cases**:
```python
def test_daily_pattern():
    """Test daily recurrence generation."""
    # ...

def test_weekly_pattern():
    """Test weekly recurrence with multiple days."""
    # ...

def test_monthly_pattern_normal():
    """Test monthly recurrence on normal days."""
    # ...

def test_monthly_pattern_edge_cases():
    """Test monthly on 29/30/31 (month-end handling)."""
    # Test Feb 30 → Feb 28/29
    # Test Apr 31 → Apr 30
    # ...

def test_pattern_validation():
    """Test recurrence pattern validation."""
    # Empty arrays should fail
    # Invalid types should fail
    # ...
```

**Dependencies**: Task 4

**Acceptance criteria**:
- All recurrence types tested
- Edge cases covered
- Validation tests included

---

### Task 26: Write Unit Tests for Instance Generator
**Complexity**: Medium

**Scope**:
- Test instance generation for individual/shared chores
- Test duplicate prevention
- Test look-ahead window calculation

**Files to create**:
- `addon/tests/test_instance_generator.py`

**Test cases**:
```python
def test_generate_individual_instances():
    """Test generation for individual chores."""
    # Create chore assigned to 2 kids
    # Generate instances
    # Verify 2 instances per due date
    # ...

def test_generate_shared_instances():
    """Test generation for shared chores."""
    # Create shared chore assigned to 3 kids
    # Generate instances
    # Verify 1 instance per due date
    # ...

def test_duplicate_prevention():
    """Test that duplicates are not created."""
    # ...

def test_lookahead_window():
    """Test look-ahead calculation."""
    # Jan 1 → Mar 31
    # Feb 1 → Apr 30
    # ...

def test_regenerate_instances():
    """Test deletion and regeneration."""
    # Create instances
    # Change pattern
    # Regenerate
    # Verify old assigned instances deleted
    # Verify claimed instances preserved
    # ...
```

**Dependencies**: Task 5

**Acceptance criteria**:
- Individual and shared logic tested
- Duplicate prevention verified
- Look-ahead window correct
- Regeneration preserves history

---

### Task 27: Write Integration Tests for Background Jobs
**Complexity**: Medium

**Scope**:
- Test each background job in isolation
- Mock scheduler to run jobs on-demand

**Files to create**:
- `addon/tests/test_background_jobs.py`

**Test cases**:
```python
def test_daily_instance_generation():
    """Test daily generation job."""
    # Create active chores
    # Run job
    # Verify instances created
    # Verify webhooks fired
    # ...

def test_auto_approval_job():
    """Test auto-approval checker."""
    # Create claimed instance with auto_approve_after_hours
    # Mock time passage
    # Run job
    # Verify instance approved
    # ...

def test_missed_instance_job():
    """Test missed instance marker."""
    # Create overdue assigned instances
    # Run job
    # Verify status changed to 'missed'
    # ...

def test_reward_expiration_job():
    """Test pending reward expiration."""
    # Create expired pending claims
    # Run job
    # Verify claims rejected and refunded
    # ...

def test_points_audit_job():
    """Test points balance audit."""
    # Create discrepancy
    # Run job
    # Verify logging
    # ...
```

**Dependencies**: Tasks 11-14

**Acceptance criteria**:
- All jobs tested in isolation
- Jobs can be run on-demand for testing
- Error handling verified

---

### Task 28: Write API Integration Tests for New Endpoints
**Complexity**: Medium

**Scope**:
- Test new endpoints (due-today, unclaim, reassign)
- Test updated endpoints with new logic

**Files to modify/create**:
- `addon/tests/test_instances.py` (add new tests)
- `addon/tests/test_rewards.py` (add new tests)

**Test cases**:
```python
def test_get_instances_due_today():
    """Test due-today endpoint."""
    # ...

def test_unclaim_instance():
    """Test unclaim functionality."""
    # ...

def test_reassign_instance():
    """Test parent reassignment."""
    # ...

def test_reward_claim_with_approval():
    """Test reward claim requiring approval."""
    # ...

def test_reward_unclaim():
    """Test reward unclaim."""
    # ...

def test_claim_with_late_flag():
    """Test claiming past due_date sets claimed_late."""
    # ...

def test_approval_with_late_points():
    """Test late_points used when claimed_late."""
    # ...

def test_approval_with_points_override():
    """Test parent point override."""
    # ...
```

**Dependencies**: Tasks 6-9, 15-19

**Acceptance criteria**:
- All new endpoints tested
- All new logic paths covered
- Edge cases included

---

### Task 29: Write Webhook Integration Tests
**Complexity**: Low

**Scope**:
- Test webhook firing
- Mock HTTP requests
- Verify payloads

**Files to create**:
- `addon/tests/test_webhooks.py`

**Test cases**:
```python
def test_webhook_payload_format():
    """Test payload structure."""
    # ...

def test_webhook_delivery():
    """Test successful delivery."""
    # Mock requests.post
    # Fire webhook
    # Verify called with correct payload
    # ...

def test_webhook_failure_handling():
    """Test graceful failure handling."""
    # Mock timeout/error
    # Fire webhook
    # Verify logs error but doesn't crash
    # ...

def test_all_event_types():
    """Test all 8 webhook event types."""
    # ...
```

**Dependencies**: Task 22

**Acceptance criteria**:
- Webhook utility fully tested
- All event types verified
- Failure handling tested

---

## Phase 7: Documentation & Deployment

### Task 30: Update Documentation
**Complexity**: Low

**Scope**:
- Update NEXT_STEPS.md to mark Step 3 complete
- Update README.md if needed
- Add inline code comments

**Files to modify**:
- `NEXT_STEPS.md`
- `README.md`
- Various code files (add docstrings/comments)

**Changes**:

Update NEXT_STEPS.md:
```markdown
**Phase**: Step 3 Complete ✅ → Step 4: Complete HA Integration

**Completed:**
- ✅ Business logic layer (scheduler, points calculation, validation)
- ✅ Background tasks (APScheduler for instance generation)
- ✅ Webhook events to Home Assistant
```

**Dependencies**: All previous tasks

**Acceptance criteria**:
- Documentation reflects current state
- All new code has docstrings
- Complex logic has inline comments

---

### Task 31: Create Deployment Guide for Step 3
**Complexity**: Low

**Scope**:
- Document how to run migrations
- Document environment variables
- Document testing procedures

**Files to create**:
- `DEPLOYMENT_STEP3.md`

**Content**:
```markdown
# Deploying Step 3: Business Logic Layer

## Prerequisites
- Step 2 completed (API endpoints working)
- Python 3.11+
- SQLite database initialized

## Deployment Steps

### 1. Update Dependencies
```bash
pip install -r addon/requirements.txt
```

### 2. Set Environment Variables
```bash
export HA_WEBHOOK_URL="http://homeassistant.local:8123/api/webhook/chorecontrol-abc123"
export SCHEDULER_ENABLED=true
```

### 3. Run Database Migration
```bash
cd addon
flask db upgrade
```

### 4. Seed System User
```bash
python seed.py --create-system-user
```

### 5. Restart Flask App
```bash
python app.py
```

### 6. Verify Background Jobs
Check logs for:
- "Background scheduler started"
- Jobs running at scheduled times

### 7. Test Webhooks
- Create a test chore due today
- Check HA for incoming webhook event

## Troubleshooting
...
```

**Dependencies**: All previous tasks

**Acceptance criteria**:
- Deployment guide is complete
- All steps documented
- Troubleshooting section included

---

## Task Dependencies Summary

```
Phase 1: Database Schema
├── Task 1 (Migration) → [No deps]
├── Task 2 (Model methods) → Task 1
└── Task 3 (System user) → Task 1

Phase 2: Core Logic
├── Task 4 (Recurrence parser) → Task 1
├── Task 5 (Instance generator) → Task 4
├── Task 6 (Claim logic) → Task 2
├── Task 7 (Approval logic) → Task 2
├── Task 8 (Reward workflow) → Tasks 1, 2
└── Task 9 (Unclaim/reassign) → Task 2

Phase 3: Background Jobs
├── Task 10 (APScheduler setup) → [No deps]
├── Task 11 (Daily generator) → Tasks 5, 10
├── Task 12 (Auto-approval) → Tasks 3, 10
├── Task 13 (Missed marker) → Task 10
└── Task 14 (Expiration/audit) → Task 10

Phase 4: API Endpoints
├── Task 15 (Create chore) → Tasks 4, 5
├── Task 16 (Update chore) → Task 5
├── Task 17 (Due today) → [No deps]
├── Task 18 (Reward endpoints) → Task 1
├── Task 19 (Points adjustment) → Task 22
├── Task 20 (to_dict methods) → [No deps]
└── Task 21 (Points verification) → [No deps]

Phase 5: Webhooks
├── Task 22 (Webhook utility) → Task 20
└── Task 23 (Add webhooks) → Task 22

Phase 6: Testing
├── Task 24 (Update existing tests) → All previous
├── Task 25 (Recurrence tests) → Task 4
├── Task 26 (Generator tests) → Task 5
├── Task 27 (Job tests) → Tasks 11-14
├── Task 28 (API tests) → Tasks 6-9, 15-19
└── Task 29 (Webhook tests) → Task 22

Phase 7: Documentation
├── Task 30 (Update docs) → All previous
└── Task 31 (Deployment guide) → All previous
```

---

## Suggested Implementation Order

For AI agent execution, tasks should be completed in this order:

### Week 1: Foundation
1. Task 1 - Database migration
2. Task 2 - Model methods
3. Task 3 - System user
4. Task 20 - to_dict methods
5. Task 4 - Recurrence parser
6. Task 25 - Recurrence tests

### Week 2: Instance Generation
7. Task 5 - Instance generator
8. Task 26 - Generator tests
9. Task 15 - Create chore endpoint
10. Task 16 - Update chore endpoint
11. Task 17 - Due today endpoint

### Week 3: Claim/Approval Logic
12. Task 6 - Claim logic
13. Task 7 - Approval logic
14. Task 9 - Unclaim/reassign
15. Task 21 - Points verification
16. Task 28 - API integration tests

### Week 4: Rewards & Webhooks
17. Task 8 - Reward workflow
18. Task 18 - Reward endpoints
19. Task 19 - Points adjustment
20. Task 22 - Webhook utility
21. Task 23 - Add webhooks
22. Task 29 - Webhook tests

### Week 5: Background Jobs
23. Task 10 - APScheduler setup
24. Task 11 - Daily generator
25. Task 12 - Auto-approval
26. Task 13 - Missed marker
27. Task 14 - Expiration/audit
28. Task 27 - Job tests

### Week 6: Testing & Documentation
29. Task 24 - Update existing tests
30. Task 30 - Update documentation
31. Task 31 - Deployment guide

---

## Complexity Summary

- **Low complexity**: 11 tasks (can be completed quickly)
- **Medium complexity**: 16 tasks (moderate effort)
- **High complexity**: 4 tasks (significant effort)

**Total**: 31 tasks

---

**End of Implementation Tasks**
