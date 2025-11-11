# Contributing to ChoreControl

Thank you for your interest in contributing to ChoreControl! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Community](#community)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and professional in all interactions.

**Expected Behavior**:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Give and receive constructive feedback gracefully
- Focus on what's best for the community and project

**Unacceptable Behavior**:

- Harassment or discrimination of any kind
- Trolling, insulting comments, or personal attacks
- Public or private harassment
- Publishing others' private information without permission

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- Basic knowledge of Flask, SQLAlchemy, and Home Assistant
- A Home Assistant instance for testing (optional but recommended)

### Development Setup

1. **Fork the repository** on GitHub

2. **Clone your fork**:

   ```bash
   git clone https://github.com/YOUR_USERNAME/chorecontrol.git
   cd chorecontrol
   ```

3. **Add upstream remote**:

   ```bash
   git remote add upstream https://github.com/shaunadam/chorecontrol.git
   ```

4. **Create virtual environment**:

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install dependencies**:

   ```bash
   pip install -e ".[dev]"
   ```

6. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

For detailed setup instructions, see [docs/development.md](docs/development.md).

## How to Contribute

### Types of Contributions

We welcome many types of contributions:

- **Bug fixes**: Fix issues and improve stability
- **New features**: Add functionality described in [NEXT_STEPS.md](NEXT_STEPS.md)
- **Documentation**: Improve or add documentation
- **Tests**: Add or improve test coverage
- **Code quality**: Refactor code, improve performance
- **Examples**: Add example configurations, dashboards, automations
- **Translations**: Add support for other languages (future)

### Finding Issues to Work On

1. Check the [issue tracker](https://github.com/shaunadam/chorecontrol/issues)
2. Look for issues labeled:
   - `good first issue`: Good for newcomers
   - `help wanted`: We need help with these
   - `bug`: Bug fixes needed
   - `enhancement`: New features
3. Check [NEXT_STEPS.md](NEXT_STEPS.md) for current development priorities

### Before You Start

1. **Check for existing issues**: Search to see if someone is already working on it
2. **Create an issue**: If one doesn't exist, create one to discuss your idea
3. **Wait for feedback**: Maintainers may provide guidance or suggestions
4. **Claim the issue**: Comment that you're working on it to avoid duplicates

## Development Workflow

### 1. Create a Branch

```bash
# Make sure you're up to date
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feat/your-feature-name
# or for bug fixes
git checkout -b fix/your-bug-fix
```

**Branch naming conventions**:

- `feat/feature-name`: New features
- `fix/bug-name`: Bug fixes
- `docs/description`: Documentation updates
- `test/description`: Test additions/updates
- `refactor/description`: Code refactoring

### 2. Make Changes

- Write clean, readable code
- Follow the [code style guidelines](#code-style-guidelines)
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run linters
pre-commit run --all-files

# Test manually in Home Assistant (if applicable)
```

### 4. Commit Your Changes

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```bash
git commit -m "feat: add reward cooldown enforcement"
git commit -m "fix: correct points calculation for approved chores"
git commit -m "docs: update API reference with new endpoints"
git commit -m "test: add unit tests for User model"
```

**Commit message format**:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example**:

```
feat(rewards): add cooldown period enforcement

Add validation to prevent users from claiming the same reward
too frequently. Cooldown period is configurable per reward.

Closes #123
```

### 5. Push and Create Pull Request

```bash
# Push your branch
git push origin feat/your-feature-name

# Create pull request on GitHub
```

## Code Style Guidelines

ChoreControl follows strict code style guidelines to maintain consistency.

### Python Code Style

- **Python Version**: 3.11+
- **Line Length**: 100 characters
- **Formatting**: Black + Ruff
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Google-style docstrings

**Example**:

```python
from typing import List, Optional

def get_user_chores(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 50
) -> List[dict]:
    """
    Get chores for a specific user.

    Args:
        user_id: The ID of the user
        status: Optional status filter (assigned, claimed, approved, rejected)
        limit: Maximum number of chores to return (default: 50)

    Returns:
        List of chore dictionaries

    Raises:
        ValueError: If user_id is invalid
        DatabaseError: If database query fails

    Example:
        >>> chores = get_user_chores(user_id=1, status='assigned')
        >>> len(chores)
        5
    """
    if user_id <= 0:
        raise ValueError("user_id must be positive")

    # Implementation here
    return []
```

### Automated Formatting

Pre-commit hooks automatically format your code. Run manually:

```bash
# Format all files
ruff format .
black .

# Check for issues
ruff check .
mypy addon/
```

### Import Organization

Imports are automatically sorted by ruff/isort:

```python
# Standard library imports
import json
import os
from typing import List, Optional

# Third-party imports
from flask import Flask, request
from sqlalchemy import Column, Integer, String

# Local application imports
from chorecontrol.models import User, Chore
from chorecontrol.services.points import calculate_points
```

## Testing Guidelines

### Writing Tests

- **Write tests for all new features**: Aim for 70%+ code coverage
- **Test edge cases**: Don't just test the happy path
- **Use descriptive test names**: `test_user_cannot_claim_reward_with_insufficient_points`
- **Use pytest fixtures**: Leverage conftest.py fixtures
- **Use markers**: Tag tests with `@pytest.mark.unit`, `@pytest.mark.integration`, etc.

**Example test**:

```python
import pytest

class TestChoreClaimWorkflow:
    """Tests for chore claiming workflow."""

    @pytest.mark.integration
    def test_kid_can_claim_assigned_chore(self, client, kid_headers, sample_chore):
        """
        Test that a kid can claim a chore assigned to them.

        Given: A chore assigned to the kid
        When: Kid POSTs to /api/instances/{id}/claim
        Then: Status changes to 'claimed' and timestamp is set
        """
        # Arrange
        instance_id = sample_chore.instances[0].id

        # Act
        response = client.post(
            f'/api/instances/{instance_id}/claim',
            headers=kid_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['status'] == 'claimed'
        assert data['data']['claimed_at'] is not None
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run with coverage
pytest --cov=addon --cov-report=html

# Run only unit tests (fast)
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

### Test Coverage

- Aim for **70%+ overall coverage**
- **80%+ for critical business logic** (points calculation, chore scheduling)
- **60%+ for API endpoints**
- Don't obsess over 100% - focus on valuable tests

## Pull Request Process

### Before Submitting

- [ ] Tests pass: `pytest`
- [ ] Linters pass: `pre-commit run --all-files`
- [ ] Documentation updated (if applicable)
- [ ] CHANGELOG.md updated (for significant changes)
- [ ] Branch is up to date with main

### Pull Request Template

When creating a PR, include:

```markdown
## Description

Brief description of what this PR does

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing

Describe how you tested your changes:

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manually tested in Home Assistant

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-reviewed my own code
- [ ] Commented code where necessary
- [ ] Updated documentation
- [ ] Tests pass locally
- [ ] No new warnings introduced

## Related Issues

Closes #123
```

### Review Process

1. **Automated checks run**: GitHub Actions runs tests and linters
2. **Maintainer review**: A maintainer reviews your code
3. **Feedback**: You may receive feedback or change requests
4. **Approval**: Once approved, your PR will be merged
5. **Celebration**: Your contribution is now part of ChoreControl! 🎉

### Getting Your PR Merged Faster

- **Keep PRs small**: Focus on one issue/feature
- **Write good descriptions**: Help reviewers understand your changes
- **Respond to feedback**: Address comments promptly
- **Be patient**: Maintainers volunteer their time

## Reporting Bugs

### Before Reporting

1. **Check existing issues**: Your bug may already be reported
2. **Try latest version**: Bug might be fixed in main branch
3. **Minimal reproduction**: Create simplest case that reproduces the bug

### Bug Report Template

```markdown
## Bug Description

Clear description of what the bug is

## Steps to Reproduce

1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior

What you expected to happen

## Actual Behavior

What actually happened

## Screenshots

If applicable, add screenshots

## Environment

- ChoreControl version: [e.g. 0.1.0]
- Home Assistant version: [e.g. 2025.11.0]
- Python version: [e.g. 3.11.5]
- Browser (if UI bug): [e.g. Chrome 119]

## Additional Context

Any other context about the problem

## Logs

```
Paste relevant log output here
```
```

## Suggesting Features

### Before Suggesting

1. **Check existing issues**: Feature may already be requested
2. **Check [NEXT_STEPS.md](NEXT_STEPS.md)**: Feature might be planned
3. **Check [PROJECT_PLAN.md](PROJECT_PLAN.md)**: See Phase 2 backlog

### Feature Request Template

```markdown
## Feature Description

Clear description of the feature you'd like

## Problem it Solves

What problem does this solve for you?

## Proposed Solution

How do you envision this working?

## Alternatives Considered

What alternatives have you considered?

## Additional Context

Any other context, screenshots, or examples
```

## Development Best Practices

### Code Quality

- **Write self-documenting code**: Use clear variable names
- **Keep functions small**: Each function should do one thing
- **Avoid deep nesting**: Extract nested logic into functions
- **Handle errors gracefully**: Don't let exceptions crash the app
- **Log appropriately**: Use proper log levels (debug, info, warning, error)

### Database Changes

- **Always create migrations**: Don't modify the database directly
- **Test migrations**: Test both upgrade and downgrade
- **Seed data**: Update seed.py if schema changes
- **Backward compatibility**: Be careful with breaking changes

### API Changes

- **Document endpoints**: Update docs/api-reference.md
- **Version breaking changes**: Don't break existing endpoints
- **Validate input**: Never trust user input
- **Return consistent formats**: Follow established patterns

## Community

### Getting Help

- **Documentation**: Check [docs/](docs/) first
- **Discussions**: [GitHub Discussions](https://github.com/shaunadam/chorecontrol/discussions)
- **Issues**: [GitHub Issues](https://github.com/shaunadam/chorecontrol/issues)

### Communication

- **Be respectful**: Treat others as you want to be treated
- **Be patient**: Maintainers are volunteers
- **Be constructive**: Focus on solutions, not blame
- **Ask questions**: No question is too simple

## Recognition

Contributors are recognized in:

- GitHub contributor graph
- Release notes
- CONTRIBUTORS.md file (TODO: Create this)

Thank you for contributing to ChoreControl! 🎉

---

## Current Development Priorities

Looking for something to work on? Check out:

- **[NEXT_STEPS.md](NEXT_STEPS.md)**: Current development streams
- **[PROJECT_PLAN.md](PROJECT_PLAN.md)**: Overall project plan
- **[GitHub Issues](https://github.com/shaunadam/chorecontrol/issues)**: Open issues

## Questions?

Feel free to open a [discussion](https://github.com/shaunadam/chorecontrol/discussions) or ask in an issue!
