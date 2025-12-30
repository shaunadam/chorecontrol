# Commit Skill

## What is a Skill?
A skill is a modular instruction file that Claude Code loads when relevant to the current task. Skills keep context focused and avoid bloating every conversation with unnecessary instructions.

## When This Activates
This skill auto-loads when you mention: "commit", "save changes", "push", "git commit"

---

## Pre-Commit Hooks

This project uses pre-commit hooks that run automatically. They will check:

1. **ruff** - Python linter (fast, replaces flake8)
2. **black** - Code formatter
3. **mypy** - Static type checking
4. **bandit** - Security vulnerability scanner

### If Hooks Fail

```bash
# Run hooks manually to see issues
pre-commit run --all-files

# Auto-fix formatting issues
black chorecontrol/
ruff check --fix chorecontrol/
```

Common fixes:
- Unused imports: Remove them
- Line too long: Break into multiple lines
- Type errors: Add type annotations or fix the actual bug
- Security issues: Review bandit output carefully

---

## Commit Message Format

Use conventional commits style:

```
<type>: <short description>

<optional body with more detail>
```

Types:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code restructuring (no behavior change)
- `test:` Adding/updating tests
- `docs:` Documentation only
- `chore:` Build/tooling changes

Examples:
```
feat: add reset endpoint for one-time chores

fix: prevent N+1 query in my_rewards page

refactor: extract instance workflow to service layer
```

---

## Commit Checklist

Before committing:
- [ ] Tests pass: `PYTHONPATH=chorecontrol python3 -m pytest chorecontrol/tests/ -v`
- [ ] Pre-commit hooks pass: `pre-commit run --all-files`
- [ ] No debug code left (print statements, commented code)
- [ ] Webhook events fired for new state transitions
