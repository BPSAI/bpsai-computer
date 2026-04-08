# Current State

> Last updated: 2026-04-07

## Status: CD3 Sprint In Progress

## Active Plan

**Plan:** plan-sprint-3-engage
**Current Sprint:** CD3 — Daemon JWT + Operator Identity

## What Was Just Done (2026-04-07)

- **CD3.2 COMPLETE** — Include operator claim in portal JWT (bpsai-support FastAPI)
  - ✓ `mint_access_token` adds `"operator"` claim from `user_data["operator_id"]`
  - ✓ Claim only included when `operator_id` is not None (backward compat)
  - ✓ `validate_portal_token` returns `operator` claim (already returns all claims)
  - ✓ 5 new tests: include, omit-when-None, omit-when-missing, round-trip, round-trip-without
  - ✓ 44/44 portal session tests passing, 136/136 auth tests passing

- **CD3.1 COMPLETE** — Add operator_id to PortalUser (bpsai-support Function App)
  - ✓ `operator_id` column added to PortalUser model (String(100), unique, nullable)
  - ✓ Auto-generation: `first_name.lower() + "-" + secrets.token_hex(4)` (8 hex chars)
  - ✓ Fallback to `user-{random}` when no first name
  - ✓ Unique constraint with collision retry (generate_operator_id_with_retry)
  - ✓ GET user endpoint returns `operator_id` via response_dict()
  - ✓ Create endpoint auto-generates operator_id
  - ✓ Alembic migration: d4e5f6g7h8i9
  - ✓ 15 new tests (format, uniqueness, fallback, collision retry)
  - ✓ 32/32 portal user tests passing

## What's Next

1. CD3.3 — CD3.4 — CD3.5 (remaining sprint tasks)
2. Branch protection setup (BPSAI/paircoder#121)

```yaml
project: bpsai-computer
status: in_progress
tests: 126 (bpsai-computer) + 15 new (bpsai-support)
sprints_done: [CD1, CD2, CD2-FIX]
sprint_active: CD3
```
