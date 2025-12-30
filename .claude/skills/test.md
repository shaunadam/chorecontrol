# Test Skill

## What is a Skill?
A skill is a modular instruction file that Claude Code loads when relevant to the current task. Skills keep context focused and avoid bloating every conversation with unnecessary instructions.

## When This Activates
This skill auto-loads when you mention: "test", "run tests", "pytest", "testing"

---

## Running Tests

### Full Test Suite
```bash
PYTHONPATH=chorecontrol python3 -m pytest chorecontrol/tests/ -v
```

### Specific Test File
```bash
PYTHONPATH=chorecontrol python3 -m pytest chorecontrol/tests/test_instances.py -v
```

### Specific Test Function
```bash
PYTHONPATH=chorecontrol python3 -m pytest chorecontrol/tests/test_instances.py::test_claim_instance_success -v
```

### With Coverage
```bash
PYTHONPATH=chorecontrol python3 -m pytest chorecontrol/tests/ --cov=chorecontrol --cov-report=term-missing
```

---

## Test Structure

Tests are in `chorecontrol/tests/`:
- `test_instances.py` - Instance workflow (claim/approve/reject)
- `test_chores.py` - Chore CRUD
- `test_rewards.py` - Reward marketplace
- `test_users.py` - User management
- `test_points.py` - Points adjustments
- `conftest.py` - Shared fixtures

---

## Key Fixtures (from conftest.py)

```python
@pytest.fixture
def app():
    """Flask app configured for testing."""

@pytest.fixture
def client(app):
    """Test client for making requests."""

@pytest.fixture
def sample_user(app):
    """Creates a test parent user."""

@pytest.fixture
def sample_kid(app):
    """Creates a test kid user."""

@pytest.fixture
def sample_chore(app, sample_user):
    """Creates a test chore."""

@pytest.fixture
def sample_instance(app, sample_chore, sample_kid):
    """Creates a test chore instance."""
```

---

## Writing Tests

### Pattern: Arrange-Act-Assert

```python
def test_claim_instance_success(client, sample_instance, sample_kid):
    # Arrange - setup is done by fixtures

    # Act
    response = client.post(
        f'/api/instances/{sample_instance.id}/claim',
        headers={'X-Remote-User-Id': sample_kid.ha_user_id}
    )

    # Assert
    assert response.status_code == 200
    assert response.json['status'] == 'claimed'
```

### Testing Auth
Use headers to simulate HA auth:
```python
headers = {
    'X-Remote-User-Id': user.ha_user_id,
    'X-Remote-User-Name': user.username
}
```

### Testing Errors
```python
def test_claim_already_claimed(client, claimed_instance, sample_kid):
    response = client.post(
        f'/api/instances/{claimed_instance.id}/claim',
        headers={'X-Remote-User-Id': sample_kid.ha_user_id}
    )
    assert response.status_code == 400
    assert 'already claimed' in response.json['error'].lower()
```

---

## Common Test Issues

1. **Database state leaking**: Each test should use fresh fixtures
2. **Missing PYTHONPATH**: Always set `PYTHONPATH=chorecontrol`
3. **Import errors**: Check that `__init__.py` files exist
4. **Datetime issues**: Use `freezegun` for time-dependent tests
