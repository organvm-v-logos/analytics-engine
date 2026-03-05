## Summary

Brief description of the changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] CI/CD improvement

## Checklist

- [ ] I have performed a self-review
- [ ] I have added/updated tests for behavior changes
- [ ] I ran `ruff check src/ tests/` and `pytest tests/ -v`
- [ ] No secrets or credentials were added
- [ ] Related issue is linked with acceptance criteria

## Dashboard Security Checklist (If Dashboard Output Changed)

- [ ] Any text sourced from analytics/report JSON is HTML-escaped before rendering
- [ ] No user/content-derived field is interpolated into HTML attributes without sanitization
- [ ] Regression tests cover escaping for titles, referrers, campaigns, and alert text
