# Review Skill

## What is a Skill?
A skill is a modular instruction file that Claude Code loads when relevant to the current task. Skills keep context focused and avoid bloating every conversation with unnecessary instructions.

## When This Activates
This skill auto-loads when you mention: "review", "PR review", "code review", "check my code"

---

## PR Review Checklist

### 1. Functionality
- [ ] Does the code do what it claims?
- [ ] Are edge cases handled?
- [ ] Is error handling appropriate?

### 2. Tests
- [ ] Are there tests for new functionality?
- [ ] Do tests cover happy path AND error cases?
- [ ] Run: `PYTHONPATH=chorecontrol python3 -m pytest chorecontrol/tests/ -v`

### 3. Architecture
- [ ] Business logic in services, not routes?
- [ ] Routes are thin controllers only?
- [ ] No duplicate code between API and UI routes?

### 4. Database
- [ ] No N+1 queries? (check for loops with queries inside)
- [ ] Indexes exist for filtered columns?
- [ ] Migrations included if models changed?

### 5. Webhooks
- [ ] State transitions fire appropriate webhooks?
- [ ] Use `fire_webhook(event_name, entity)` from `utils.webhooks`
- [ ] Events: `chore_instance_claimed`, `chore_instance_approved`, `chore_instance_rejected`, `points_awarded`

### 6. Auth & Security
- [ ] Routes use `@ha_auth_required` or `@parent_required`?
- [ ] User can only modify their own resources (or is parent)?
- [ ] No SQL injection (use SQLAlchemy ORM properly)?
- [ ] No secrets in code?

### 7. Home Assistant Integration
- [ ] Does this affect the HA custom component?
- [ ] API contract changes documented?
- [ ] Webhook payloads consistent?

---

## Common Issues to Flag

### Business Logic in Routes
```python
# BAD - logic in route
@bp.route('/claim')
def claim():
    instance.status = 'claimed'
    instance.claimed_by = user.id
    user.points += instance.chore.points  # Business logic!
    db.session.commit()

# GOOD - delegate to service
@bp.route('/claim')
def claim():
    result, error = InstanceService.claim(instance.id, user.id)
    if error:
        return jsonify({'error': error}), 400
    return jsonify(result)
```

### N+1 Queries
```python
# BAD - query per reward
for reward in rewards:
    claim_count = RewardClaim.query.filter_by(reward_id=reward.id).count()

# GOOD - single query
claim_counts = db.session.query(
    RewardClaim.reward_id,
    func.count(RewardClaim.id)
).group_by(RewardClaim.reward_id).all()
```

### Missing Webhook
```python
# GOOD - fire webhook after state change
instance.status = 'approved'
db.session.commit()
fire_webhook('chore_instance_approved', instance)
```
