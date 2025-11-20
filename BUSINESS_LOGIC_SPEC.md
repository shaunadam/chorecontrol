# ChoreControl - Business Logic Specification

> **Phase**: Step 3 - Business Logic Layer
> **Status**: Requirements Complete - Ready for Implementation
> **Last Updated**: 2025-11-18

---

## Table of Contents

1. [Overview](#overview)
2. [Data Model Changes](#data-model-changes)
3. [Chore Instance Scheduler](#chore-instance-scheduler)
4. [Recurrence Patterns](#recurrence-patterns)
5. [Assignment Logic](#assignment-logic)
6. [Instance Lifecycle & State Machine](#instance-lifecycle--state-machine)
7. [Points Calculation & Awarding](#points-calculation--awarding)
8. [Reward Validation & Approval](#reward-validation--approval)
9. [Background Tasks (APScheduler)](#background-tasks-apscheduler)
10. [Webhook Events](#webhook-events)
11. [API Endpoint Changes](#api-endpoint-changes)
12. [Validation Rules](#validation-rules)

---

## Overview

The business logic layer implements the core chore management workflows:
- Automatic generation of chore instances from recurring templates
- Late/missed status tracking with configurable penalties
- Points calculation with support for late completion bonuses/penalties
- Reward approval workflow with auto-expiration
- Background jobs for auto-approval and instance generation
- Webhook events for Home Assistant integration

---

## Data Model Changes

### 1. ChoreInstance Table

**Add fields:**
```python
assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
# For individual assignments: assigned_to = specific kid
# For shared assignments: assigned_to = NULL

claimed_late = db.Column(db.Boolean, default=False, nullable=False)
# Set to True if claimed_at > due_date
```

**Update constraints:**
```python
CheckConstraint(
    "status IN ('assigned', 'claimed', 'approved', 'rejected', 'missed')",
    name='check_instance_status'
)
```

**Update indexes:**
```python
Index('idx_chore_instances_assigned_to', 'assigned_to')
```

---

### 2. Chore Table

**Add fields:**
```python
allow_late_claims = db.Column(db.Boolean, default=False, nullable=False)
# If False, assigned instances past due_date transition to 'missed'
# If True, kids can still claim past due_date (marked as claimed_late)

late_points = db.Column(db.Integer, nullable=True)
# Points awarded for late completions (if allow_late_claims=True)
# If NULL, use regular chore.points value
```

**Update recurrence_pattern validation:**
- `type='daily'`: No additional fields required
- `type='weekly'`: Requires non-empty `days_of_week` array
- `type='monthly'`: Requires non-empty `days_of_month` array
- `type='none'`: One-off chore (supports `start_date` or NULL for "anytime")

---

### 3. Reward Table

**Add field:**
```python
requires_approval = db.Column(db.Boolean, default=False, nullable=False)
# If False, reward claim auto-approves and deducts points immediately
# If True, parent must approve; claim status starts as 'pending'
```

---

### 4. RewardClaim Table

**Add field:**
```python
expires_at = db.Column(db.DateTime, nullable=True)
# For pending claims: set to claimed_at + 7 days
# Background job auto-rejects expired pending claims
```

---

### 5. User Table

**Update constraints:**
```python
CheckConstraint(
    "role IN ('parent', 'kid', 'system')",
    name='check_user_role'
)
```

**Add system user during initialization:**
```python
system_user = User(
    ha_user_id='system',
    username='System',
    role='system',
    points=0
)
```

---

## Chore Instance Scheduler

### Generation Timing

Instances are generated:
1. **When chore is created** - Generate instances through end of (current month + 2 months)
2. **When chore is modified** - Delete future instances, regenerate based on new schedule
3. **Daily at midnight** - Generate any missing instances through the look-ahead window

### Look-Ahead Window

**Rule**: Generate instances through the **end of the month that is 2 months ahead**

Examples:
- January 1 → Generate through March 31
- January 31 → Generate through March 31
- February 1 → Generate through April 30
- December 15 → Generate through February 28/29 (next year)

### Duplicate Prevention

**For individual chores** (`assignment_type='individual'`):
```python
existing = ChoreInstance.query.filter_by(
    chore_id=chore.id,
    due_date=calculated_date,
    assigned_to=kid.id
).first()
```

**For shared chores** (`assignment_type='shared'`):
```python
existing = ChoreInstance.query.filter_by(
    chore_id=chore.id,
    due_date=calculated_date,
    assigned_to=None
).first()
```

### Schedule Modification Handling

When a chore's recurrence pattern changes:
1. Delete all future instances where `due_date >= today` AND `status='assigned'`
2. Regenerate instances based on new pattern through the look-ahead window
3. Do NOT delete instances that are `claimed`, `approved`, or `rejected` (preserve history)

---

## Recurrence Patterns

### Daily Pattern
```json
{
  "type": "daily"
}
```

**Generation logic:**
- Create one instance per day from `start_date` to `end_date`
- If `end_date` is NULL, generate through look-ahead window

---

### Weekly Pattern
```json
{
  "type": "weekly",
  "days_of_week": [0, 2, 4]
}
```

**Fields:**
- `days_of_week`: Array of integers (0=Sunday, 1=Monday, ..., 6=Saturday)
- **Validation**: Array must be non-empty

**Generation logic:**
- Create instances only on specified days of the week
- Example: `[0, 2, 4]` → Every Sunday, Tuesday, Thursday

---

### Monthly Pattern
```json
{
  "type": "monthly",
  "days_of_month": [2, 17]
}
```

**Fields:**
- `days_of_month`: Array of integers (1-31)
- **Validation**: Array must be non-empty

**Generation logic:**
- Create instances on specified days of each month
- **Edge case**: If day doesn't exist in month (e.g., Feb 30), use last day of month
- Example: `days_of_month: [15, 31]` in February → Feb 15, Feb 28/29

---

### One-Off (No Recurrence)
```json
{
  "type": "none"
}
```

**Generation logic:**
- If `start_date` is set: Create one instance with `due_date = start_date`
- If `start_date` is NULL: Create one instance with `due_date = NULL` (claimable anytime)

---

## Assignment Logic

### Individual Chores (`assignment_type='individual'`)

**Behavior:**
- Create **one instance per assigned kid** for each due date
- Each instance has `assigned_to = kid.id`
- Kid can only claim their own instance

**Example:**
- Chore: "Make Bed" assigned to Kid A (id=2) and Kid B (id=3)
- Due date: Jan 15
- Generates:
  - Instance 1: `chore_id=1, due_date='2025-01-15', assigned_to=2`
  - Instance 2: `chore_id=1, due_date='2025-01-15', assigned_to=3`

---

### Shared Chores (`assignment_type='shared'`)

**Behavior:**
- Create **one instance total** for each due date
- Instance has `assigned_to = NULL`
- Any kid in `ChoreAssignment` can claim it (first come, first served)

**Example:**
- Chore: "Take out trash" assigned to Kid A (id=2) and Kid B (id=3)
- Due date: Jan 15
- Generates:
  - Instance 1: `chore_id=2, due_date='2025-01-15', assigned_to=NULL`
- Either Kid A or Kid B can claim it

**Claiming validation:**
```python
def can_claim(self, user_id: int) -> bool:
    if self.status != 'assigned':
        return False

    # For individual chores, must match assigned_to
    if self.assigned_to is not None:
        return self.assigned_to == user_id

    # For shared chores, check ChoreAssignment table
    assignment = ChoreAssignment.query.filter_by(
        chore_id=self.chore_id,
        user_id=user_id
    ).first()

    return assignment is not None
```

---

## Instance Lifecycle & State Machine

### Status Values

- `'assigned'` - Waiting to be claimed by kid
- `'claimed'` - Kid has claimed, awaiting parent approval
- `'approved'` - Parent approved, points awarded
- `'rejected'` - Parent rejected, no points awarded
- `'missed'` - Past due_date and cannot be claimed (late claims not allowed)

### State Transitions

```
                    ┌─────────┐
                    │assigned │
                    └────┬────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    (kid claims)    (becomes         (becomes
                     overdue,         overdue,
                 late claims OK)  late claims disabled)
         │               │               │
         v               v               v
    ┌────────┐      ┌─────────┐     ┌────────┐
    │claimed │      │assigned │     │missed  │
    └───┬────┘      └────┬────┘     └────────┘
        │                │          (terminal)
        │          (kid claims,
        │           marked late)
        │                │
        │                v
        │           ┌────────┐
        │           │claimed │
        │           │(late)  │
        │           └───┬────┘
        │               │
        └───────┬───────┘
                │
         ┌──────▼──────┐
         │             │
         v             v
    ┌─────────┐  ┌──────────┐
    │approved │  │rejected  │
    └─────────┘  └─────┬────┘
                        │
                  (kid can
                   re-claim)
                        │
                        v
                   ┌────────┐
                   │claimed │
                   └────────┘
```

### Transition Rules

#### `assigned` → `claimed`
**Trigger**: Kid claims via `POST /api/instances/{id}/claim`

**Logic:**
```python
instance.status = 'claimed'
instance.claimed_by = user_id
instance.claimed_at = datetime.utcnow()

# Check if late
if instance.due_date and datetime.utcnow().date() > instance.due_date:
    instance.claimed_late = True
```

**Validations:**
- Instance must be in `'assigned'` status
- User must be assigned to this chore (via `ChoreAssignment` or `assigned_to`)
- If `due_date` passed and `allow_late_claims=False`, cannot claim (should be `'missed'`)

---

#### `assigned` → `missed`
**Trigger**: Background job (nightly or hourly)

**Logic:**
```python
# Find overdue assigned instances
overdue = ChoreInstance.query.filter(
    ChoreInstance.status == 'assigned',
    ChoreInstance.due_date < date.today(),
    ChoreInstance.due_date.isnot(None)
).join(Chore).filter(
    Chore.allow_late_claims == False
).all()

for instance in overdue:
    instance.status = 'missed'
```

**Validations:**
- Only if `chore.allow_late_claims = False`
- Instances with `due_date = NULL` never transition to missed

---

#### `claimed` → `approved`
**Trigger**: Parent approval via `POST /api/instances/{id}/approve` OR auto-approval (background job)

**Logic:**
```python
# Determine points to award
if instance.claimed_late and instance.chore.late_points is not None:
    points_to_award = instance.chore.late_points
else:
    points_to_award = instance.chore.points

# Allow parent override (optional parameter)
if points_override is not None:
    points_to_award = points_override

# Update instance
instance.status = 'approved'
instance.approved_by = approver_id  # or system user for auto-approval
instance.approved_at = datetime.utcnow()
instance.points_awarded = points_to_award

# Award points to kid
claimer = User.query.get(instance.claimed_by)
claimer.adjust_points(
    delta=points_to_award,
    reason=f"Completed chore: {instance.chore.name}",
    created_by_id=approver_id,
    chore_instance_id=instance.id
)
```

**Validations:**
- Instance must be in `'claimed'` status
- Approver must be a parent (or system user)
- Cannot approve your own claim

---

#### `claimed` → `rejected`
**Trigger**: Parent rejection via `POST /api/instances/{id}/reject`

**Logic:**
```python
instance.status = 'rejected'
instance.rejected_by = rejecter_id
instance.rejected_at = datetime.utcnow()
instance.rejection_reason = reason
instance.points_awarded = None
```

**Validations:**
- Instance must be in `'claimed'` status
- Rejecter must be a parent
- Cannot reject your own claim

---

#### `rejected` → `claimed` (Re-claim)
**Trigger**: Kid re-claims via `POST /api/instances/{id}/claim`

**Logic:**
```python
# Clear rejection fields
instance.status = 'claimed'
instance.claimed_by = user_id
instance.claimed_at = datetime.utcnow()
instance.rejected_by = None
instance.rejected_at = None
instance.rejection_reason = None

# Re-check if late
if instance.due_date and datetime.utcnow().date() > instance.due_date:
    instance.claimed_late = True
```

**Validations:**
- No time limit on re-claiming rejected instances
- Still must be assigned to this chore

---

#### `claimed` → `assigned` (Unclaim)
**Trigger**: Kid unclaims via `POST /api/instances/{id}/unclaim`

**Logic:**
```python
instance.status = 'assigned'
instance.claimed_by = None
instance.claimed_at = None
instance.claimed_late = False
```

**Validations:**
- Instance must be in `'claimed'` status (before approval/rejection)
- Only the kid who claimed can unclaim

---

### Parent Re-assignment

**Trigger**: `POST /api/instances/{id}/reassign`

**Logic:**
```python
# Only for individual chores
if instance.chore.assignment_type != 'individual':
    return error("Cannot reassign shared chores")

# Update assigned_to
instance.assigned_to = new_user_id

# Create ChoreAssignment if it doesn't exist
if not ChoreAssignment.query.filter_by(
    chore_id=instance.chore_id,
    user_id=new_user_id
).first():
    assignment = ChoreAssignment(
        chore_id=instance.chore_id,
        user_id=new_user_id
    )
    db.session.add(assignment)
```

**Validations:**
- Instance must be in `'assigned'` status (not claimed yet)
- Only individual chores can be reassigned
- Target user must be a kid

---

## Points Calculation & Awarding

### Default Points

**On-time completion:**
- Award `chore.points`

**Late completion** (if `claimed_late=True`):
- If `chore.late_points` is set: Award `chore.late_points`
- Otherwise: Award `chore.points` (no penalty/bonus)

### Parent Override

Parents can adjust points at approval time:
```python
POST /api/instances/{id}/approve
{
  "approver_id": 1,
  "points": 7  # Override: give 7 points instead of chore default
}
```

**Use cases:**
- Partial completion (reduce points)
- Extra effort (bonus points)
- Quality issues (reduce points)

### Points Transaction

All point changes create a `PointsHistory` entry:
```python
User.adjust_points(
    delta=points_to_award,
    reason=f"Completed chore: {chore.name}",
    created_by_id=approver_id,
    chore_instance_id=instance.id
)
```

### Points Balance Verification

**When to verify:**
1. After each points transaction (inline check)
2. Nightly background job (audit all users)

**Logic:**
```python
calculated = user.calculate_current_points()  # Sum of PointsHistory
if user.points != calculated:
    logger.error(f"Points mismatch for user {user.id}: "
                 f"stored={user.points}, calculated={calculated}")
    # Future: auto-heal or alert admin
```

---

## Reward Validation & Approval

### Two Reward Types

**Auto-approve rewards** (`requires_approval=False`):
- Points deducted immediately
- `RewardClaim.status = 'approved'`
- No parent action needed

**Approval-required rewards** (`requires_approval=True`):
- Points deducted immediately (optimistic)
- `RewardClaim.status = 'pending'`
- `RewardClaim.expires_at = claimed_at + 7 days`
- Parent must approve/reject within 7 days
- If expired, auto-reject and refund points

### Claim Workflow

#### Step 1: Claim Validation
```python
can_claim, reason = reward.can_claim(user_id)
if not can_claim:
    return error(reason)
```

**Checks:**
- Reward is active
- User is a kid
- User has sufficient points
- Max claims limits (total and per-kid)
- Cooldown period

---

#### Step 2: Create Claim
```python
claim = RewardClaim(
    reward_id=reward.id,
    user_id=user_id,
    points_spent=reward.points_cost,
    status='pending' if reward.requires_approval else 'approved'
)

if reward.requires_approval:
    claim.expires_at = datetime.utcnow() + timedelta(days=7)

# Deduct points immediately
user.adjust_points(
    delta=-reward.points_cost,
    reason=f"Claimed reward: {reward.name}",
    reward_claim_id=claim.id
)
```

---

#### Step 3: Parent Approval (if required)
```python
# Approve
claim.status = 'approved'
claim.approved_by = approver_id
claim.approved_at = datetime.utcnow()
claim.expires_at = None  # Clear expiration
# Points already deducted, no additional action

# Reject
claim.status = 'rejected'
claim.approved_by = approver_id
claim.approved_at = datetime.utcnow()
claim.expires_at = None

# Refund points
user.adjust_points(
    delta=claim.points_spent,  # Positive delta to refund
    reason=f"Reward claim rejected: {reward.name}",
    created_by_id=approver_id,
    reward_claim_id=claim.id
)
```

---

#### Step 4: Auto-Expiration (Background Job)
```python
expired_claims = RewardClaim.query.filter(
    RewardClaim.status == 'pending',
    RewardClaim.expires_at <= datetime.utcnow()
).all()

for claim in expired_claims:
    claim.status = 'rejected'

    # Refund points
    user = User.query.get(claim.user_id)
    user.adjust_points(
        delta=claim.points_spent,
        reason=f"Reward claim expired: {claim.reward.name}",
        reward_claim_id=claim.id
    )
```

---

### Unclaim Workflow

**Only for pending claims:**
```python
POST /api/rewards/claims/{id}/unclaim

if claim.status != 'pending':
    return error("Can only unclaim pending rewards")

# Refund points
user.adjust_points(
    delta=claim.points_spent,
    reason=f"Unclaimed reward: {claim.reward.name}",
    reward_claim_id=claim.id
)

# Delete claim record
db.session.delete(claim)
```

**Approved claims cannot be unclaimed** (reward was given, points are spent).

---

## Background Tasks (APScheduler)

### 1. Daily Instance Generator
**Schedule**: Every day at 00:00 (midnight)

**Purpose**: Generate missing chore instances through the look-ahead window

**Logic**:
```python
@scheduler.scheduled_job('cron', hour=0, minute=0)
def generate_daily_instances():
    logger.info("Starting daily instance generation")

    active_chores = Chore.query.filter_by(is_active=True).all()

    for chore in active_chores:
        # Calculate look-ahead end date
        today = date.today()
        target_month = today + relativedelta(months=2)
        end_date = date(target_month.year, target_month.month,
                       calendar.monthrange(target_month.year, target_month.month)[1])

        # Generate instances based on recurrence pattern
        instances = generate_instances_for_chore(chore, today, end_date)

        for instance in instances:
            db.session.add(instance)

            # Fire webhook only for instances due today or NULL due date
            if instance.due_date == today or instance.due_date is None:
                fire_webhook('chore_instance_created', instance)

    db.session.commit()
    logger.info("Daily instance generation complete")
```

---

### 2. Auto-Approval Checker
**Schedule**: Every 5 minutes

**Purpose**: Auto-approve claimed instances that have exceeded the auto-approval window

**Logic**:
```python
@scheduler.scheduled_job('interval', minutes=5)
def check_auto_approvals():
    # Find eligible instances
    eligible = ChoreInstance.query.filter(
        ChoreInstance.status == 'claimed'
    ).join(Chore).filter(
        Chore.auto_approve_after_hours.isnot(None)
    ).all()

    system_user = User.query.filter_by(ha_user_id='system').first()

    for instance in eligible:
        hours_since_claim = (datetime.utcnow() - instance.claimed_at).total_seconds() / 3600

        if hours_since_claim >= instance.chore.auto_approve_after_hours:
            # Auto-approve
            instance.award_points(approver_id=system_user.id)
            db.session.commit()

            logger.info(f"Auto-approved instance {instance.id}")
            fire_webhook('chore_instance_approved', instance, auto_approved=True)
```

---

### 3. Missed Instance Marker
**Schedule**: Every hour (or nightly at 00:30)

**Purpose**: Transition overdue assigned instances to 'missed' status

**Logic**:
```python
@scheduler.scheduled_job('cron', minute=30)  # Run at :30 past each hour
def mark_missed_instances():
    overdue = ChoreInstance.query.filter(
        ChoreInstance.status == 'assigned',
        ChoreInstance.due_date < date.today(),
        ChoreInstance.due_date.isnot(None)
    ).join(Chore).filter(
        Chore.allow_late_claims == False
    ).all()

    for instance in overdue:
        instance.status = 'missed'
        logger.info(f"Marked instance {instance.id} as missed")

    db.session.commit()
```

---

### 4. Pending Reward Expiration
**Schedule**: Every day at 00:01

**Purpose**: Auto-reject pending reward claims after 7 days

**Logic**:
```python
@scheduler.scheduled_job('cron', hour=0, minute=1)
def expire_pending_rewards():
    expired = RewardClaim.query.filter(
        RewardClaim.status == 'pending',
        RewardClaim.expires_at <= datetime.utcnow()
    ).all()

    for claim in expired:
        claim.status = 'rejected'

        # Refund points
        user = User.query.get(claim.user_id)
        user.adjust_points(
            delta=claim.points_spent,
            reason=f"Reward claim expired: {claim.reward.name}",
            reward_claim_id=claim.id
        )

        logger.info(f"Expired reward claim {claim.id}")
        fire_webhook('reward_rejected', claim, reason='expired')

    db.session.commit()
```

---

### 5. Points Balance Audit
**Schedule**: Every day at 02:00

**Purpose**: Verify all users' points match their history

**Logic**:
```python
@scheduler.scheduled_job('cron', hour=2, minute=0)
def audit_points_balances():
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

---

## Webhook Events

### Configuration

Store webhook URL in config:
```python
WEBHOOK_URL = os.getenv('HA_WEBHOOK_URL')
# Example: http://homeassistant.local:8123/api/webhook/chorecontrol-abc123
```

### Event Payload Format

All events follow this structure:
```json
{
  "event": "event_name",
  "timestamp": "2025-01-15T14:30:00Z",
  "data": {
    // Event-specific data
  }
}
```

### Event Types

#### 1. `chore_instance_created`
**Trigger**: New instance created (only if due today or NULL due date)

**Payload**:
```json
{
  "event": "chore_instance_created",
  "timestamp": "2025-01-15T00:00:00Z",
  "data": {
    "instance_id": 123,
    "chore_id": 5,
    "chore_name": "Make bed",
    "due_date": "2025-01-15",
    "assigned_to": 2,
    "assigned_to_name": "Kid A",
    "points": 5,
    "status": "assigned"
  }
}
```

---

#### 2. `chore_instance_claimed`
**Trigger**: Kid claims a chore

**Payload**:
```json
{
  "event": "chore_instance_claimed",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "instance_id": 123,
    "chore_id": 5,
    "chore_name": "Make bed",
    "claimed_by": 2,
    "claimed_by_name": "Kid A",
    "claimed_at": "2025-01-15T10:30:00Z",
    "claimed_late": false,
    "due_date": "2025-01-15",
    "points": 5
  }
}
```

---

#### 3. `chore_instance_approved`
**Trigger**: Parent approves or auto-approval occurs

**Payload**:
```json
{
  "event": "chore_instance_approved",
  "timestamp": "2025-01-15T14:30:00Z",
  "data": {
    "instance_id": 123,
    "chore_id": 5,
    "chore_name": "Make bed",
    "claimed_by": 2,
    "claimed_by_name": "Kid A",
    "approved_by": 1,
    "approved_by_name": "Parent",
    "approved_at": "2025-01-15T14:30:00Z",
    "points_awarded": 5,
    "auto_approved": false
  }
}
```

---

#### 4. `chore_instance_rejected`
**Trigger**: Parent rejects a claimed chore

**Payload**:
```json
{
  "event": "chore_instance_rejected",
  "timestamp": "2025-01-15T14:30:00Z",
  "data": {
    "instance_id": 123,
    "chore_id": 5,
    "chore_name": "Make bed",
    "claimed_by": 2,
    "claimed_by_name": "Kid A",
    "rejected_by": 1,
    "rejected_by_name": "Parent",
    "rejected_at": "2025-01-15T14:30:00Z",
    "rejection_reason": "Bed not made properly"
  }
}
```

---

#### 5. `points_awarded`
**Trigger**: Any point change (chore approval, manual adjustment, etc.)

**Payload**:
```json
{
  "event": "points_awarded",
  "timestamp": "2025-01-15T14:30:00Z",
  "data": {
    "user_id": 2,
    "username": "Kid A",
    "points_delta": 5,
    "new_balance": 45,
    "reason": "Completed chore: Make bed",
    "created_by": 1,
    "created_by_name": "Parent",
    "chore_instance_id": 123,
    "reward_claim_id": null
  }
}
```

---

#### 6. `reward_claimed`
**Trigger**: Kid claims a reward

**Payload**:
```json
{
  "event": "reward_claimed",
  "timestamp": "2025-01-15T15:00:00Z",
  "data": {
    "claim_id": 10,
    "reward_id": 3,
    "reward_name": "30 minutes screen time",
    "user_id": 2,
    "username": "Kid A",
    "points_spent": 20,
    "new_balance": 25,
    "status": "pending",
    "requires_approval": true,
    "expires_at": "2025-01-22T15:00:00Z"
  }
}
```

---

#### 7. `reward_approved`
**Trigger**: Parent approves a pending reward claim

**Payload**:
```json
{
  "event": "reward_approved",
  "timestamp": "2025-01-15T16:00:00Z",
  "data": {
    "claim_id": 10,
    "reward_id": 3,
    "reward_name": "30 minutes screen time",
    "user_id": 2,
    "username": "Kid A",
    "approved_by": 1,
    "approved_by_name": "Parent",
    "points_spent": 20
  }
}
```

---

#### 8. `reward_rejected`
**Trigger**: Parent rejects or claim expires

**Payload**:
```json
{
  "event": "reward_rejected",
  "timestamp": "2025-01-22T15:00:00Z",
  "data": {
    "claim_id": 10,
    "reward_id": 3,
    "reward_name": "30 minutes screen time",
    "user_id": 2,
    "username": "Kid A",
    "approved_by": 1,
    "approved_by_name": "Parent",
    "points_refunded": 20,
    "new_balance": 45,
    "reason": "expired"
  }
}
```

---

### Webhook Delivery

**Implementation**:
```python
import requests

def fire_webhook(event_name, instance_or_claim, **kwargs):
    if not WEBHOOK_URL:
        logger.warning("Webhook URL not configured")
        return

    payload = build_payload(event_name, instance_or_claim, **kwargs)

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=5  # Don't block for too long
        )
        response.raise_for_status()
        logger.info(f"Webhook fired: {event_name}")
    except Exception as e:
        logger.error(f"Webhook delivery failed: {e}")
        # Don't raise - webhook failures shouldn't break the app
```

---

## API Endpoint Changes

### New Endpoints

#### 1. Get Instances Due Today
```
GET /api/instances/due-today
```

**Response**:
```json
{
  "instances": [
    {
      "id": 123,
      "chore_id": 5,
      "chore_name": "Make bed",
      "due_date": "2025-01-15",
      "assigned_to": 2,
      "assigned_to_name": "Kid A",
      "status": "assigned",
      "points": 5
    }
  ]
}
```

---

#### 2. Reassign Instance
```
POST /api/instances/{id}/reassign
```

**Request**:
```json
{
  "new_user_id": 3,
  "reassigned_by": 1
}
```

**Response**: Updated instance object

---

#### 3. Unclaim Instance
```
POST /api/instances/{id}/unclaim
```

**Request**:
```json
{
  "user_id": 2
}
```

**Response**: Updated instance object (status back to 'assigned')

---

#### 4. Unclaim Reward
```
POST /api/rewards/claims/{id}/unclaim
```

**Request**:
```json
{
  "user_id": 2
}
```

**Response**: Success message (claim deleted, points refunded)

---

### Updated Endpoints

#### 1. `POST /api/chores` - Create Chore
**Add validation**:
- If `recurrence_type='weekly'`, validate `days_of_week` is non-empty
- If `recurrence_type='monthly'`, validate `days_of_month` is non-empty
- Validate `allow_late_claims` and `late_points` fields

**After creation**:
- Generate instances through look-ahead window
- Fire webhooks for instances due today

---

#### 2. `PUT /api/chores/{id}` - Update Chore
**If recurrence pattern changes**:
1. Delete future assigned instances
2. Regenerate based on new pattern
3. Fire webhooks for new instances due today

---

#### 3. `POST /api/instances/{id}/claim` - Claim Instance
**Add logic**:
- Check if `due_date` passed → Set `claimed_late=True`
- Fire `chore_instance_claimed` webhook

---

#### 4. `POST /api/instances/{id}/approve` - Approve Instance
**Add logic**:
- Accept optional `points` parameter for parent override
- Calculate points based on `claimed_late` and `late_points`
- Fire `chore_instance_approved` webhook
- Fire `points_awarded` webhook

---

#### 5. `POST /api/rewards` - Create Reward
**Add validation**:
- Validate `requires_approval` field

---

#### 6. `POST /api/rewards/{id}/claim` - Claim Reward
**Add logic**:
- If `requires_approval=True`, set `status='pending'` and `expires_at`
- Fire `reward_claimed` webhook

---

#### 7. `POST /api/rewards/claims/{id}/approve` - Approve Reward Claim
**Add logic**:
- Fire `reward_approved` webhook

---

#### 8. `POST /api/rewards/claims/{id}/reject` - Reject Reward Claim
**Add logic**:
- Refund points
- Fire `reward_rejected` webhook

---

#### 9. `POST /api/points/adjust` - Manual Points Adjustment
**Add logic**:
- Fire `points_awarded` webhook (supports negative deltas)

---

## Validation Rules

### Business Rules Enforced

1. ✅ Can't claim a chore you're not assigned to
2. ✅ Can't approve your own chore claim
3. ✅ Only parents can approve chores
4. ✅ Can't claim a reward you can't afford
5. ✅ Verify cooldown, max claims limits on rewards
6. ✅ Can't delete active chores with pending instances (soft delete only)
7. ✅ Prevent negative point balances (validate before deduction)
8. ✅ Can't claim instances in 'missed' status
9. ✅ Can't unclaim instances that are already approved
10. ✅ Can't reassign shared chores (only individual)

### Data Validation

1. **Recurrence patterns**:
   - `type='weekly'` → `days_of_week` must be non-empty array
   - `type='monthly'` → `days_of_month` must be non-empty array
   - `days_of_week` values must be 0-6
   - `days_of_month` values must be 1-31

2. **Points**:
   - `chore.points` >= 0
   - `chore.late_points` >= 0 or NULL
   - `reward.points_cost` > 0
   - User balance cannot go negative

3. **Dates**:
   - `chore.end_date` >= `chore.start_date` (if both set)
   - `instance.due_date` <= `chore.end_date` (if chore has end_date)

4. **Status transitions**:
   - Only valid state transitions allowed (see state machine)

---

## Implementation Checklist

### Phase 1: Database Changes
- [ ] Add fields to `ChoreInstance` (`assigned_to`, `claimed_late`)
- [ ] Add fields to `Chore` (`allow_late_claims`, `late_points`)
- [ ] Add field to `Reward` (`requires_approval`)
- [ ] Add field to `RewardClaim` (`expires_at`)
- [ ] Update `User.role` constraint to include `'system'`
- [ ] Update `ChoreInstance.status` constraint to include `'missed'`
- [ ] Create system user in seed data
- [ ] Create database migration

### Phase 2: Core Business Logic
- [ ] Implement recurrence pattern parser (`calculate_next_due_date()`)
- [ ] Implement instance generator (`generate_instances_for_chore()`)
- [ ] Update `ChoreInstance.can_claim()` to handle `assigned_to`
- [ ] Update `ChoreInstance.award_points()` to handle late points
- [ ] Implement duplicate checking logic
- [ ] Implement schedule modification handling (delete + regenerate)

### Phase 3: Background Tasks
- [ ] Set up APScheduler
- [ ] Implement daily instance generator job
- [ ] Implement auto-approval checker job
- [ ] Implement missed instance marker job
- [ ] Implement pending reward expiration job
- [ ] Implement points balance audit job

### Phase 4: Webhook Integration
- [ ] Implement `fire_webhook()` utility
- [ ] Add webhook configuration to config
- [ ] Fire webhooks for all 8 event types
- [ ] Test webhook delivery and error handling

### Phase 5: API Endpoints
- [ ] Create `GET /api/instances/due-today`
- [ ] Create `POST /api/instances/{id}/reassign`
- [ ] Create `POST /api/instances/{id}/unclaim`
- [ ] Create `POST /api/rewards/claims/{id}/unclaim`
- [ ] Update all existing endpoints with new logic
- [ ] Add validation for new fields

### Phase 6: Testing
- [ ] Unit tests for recurrence pattern logic
- [ ] Unit tests for instance generation
- [ ] Unit tests for late/missed status transitions
- [ ] Unit tests for reward approval workflow
- [ ] Integration tests for background jobs
- [ ] Integration tests for webhooks
- [ ] Update existing API tests

---

**End of Specification**
