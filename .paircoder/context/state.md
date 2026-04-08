# Current State

> Last updated: 2026-04-07

## Status: CD3 Sprint In Progress

## Active Plan

**Plan:** plan-sprint-3-engage
**Current Sprint:** CD3 — Daemon JWT + Operator Identity

## What Was Just Done

- **CD3.4 done** (auto-updated by hook) (2026-04-07)

- **CD3.4 COMPLETE** — Auto-discover license_id from license.json (bpsai-computer)
  - ✓ `config.py`: `license_id` already defaults to None (no change needed)
  - ✓ New `license_discovery.py`: finds `~/.paircoder/license.json`, reads `payload.license_id`
  - ✓ `BPSAI_LICENSE_FILE` env var overrides default path
  - ✓ `daemon.py`: `resolve_license_id()` auto-discovers when config has no `license_id`
  - ✓ Clear error: "No license found. Run: bpsai-pair license install <file>"
  - ✓ Config `license_id` overrides auto-discovery (for cloud VMs)
  - ✓ 9 new license_discovery tests + 3 daemon integration tests (12 total)
  - ✓ 48/48 tests passing

- **CD3.3 COMPLETE** — Show operator ID in Command Center (bpsai-command-center)
  - ✓ Added `operator?: string` to `JwtClaims` interface in `oauth.ts`
  - ✓ `evaluateAuth` now returns `operatorId` from JWT `operator` claim
  - ✓ Middleware sets `cc_operator_id` cookie (non-httpOnly) for client JS
  - ✓ Callback, refresh-session, and logout routes updated for `cc_operator_id` cookie
  - ✓ `getOperatorIdFromCookie()` helper in `use-operator.ts`
  - ✓ `OperatorIdDisplay` component with copy-to-clipboard button
  - ✓ Legacy users see "Not assigned — contact admin" when no operator ID
  - ✓ Wired into dashboard header next to operator name
  - ✓ 15 new tests (cookie helper, component, middleware integration)
  - ✓ 227/227 tests passing (excluding 5 pre-existing failures)

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

1. CD3.5 (remaining sprint task)
2. Branch protection setup (BPSAI/paircoder#121)

```yaml
project: bpsai-computer
status: in_progress
tests: 126 (bpsai-computer) + 15 new (bpsai-support)
sprints_done: [CD1, CD2, CD2-FIX]
sprint_active: CD3
```
