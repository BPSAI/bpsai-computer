# Current State

> Last updated: 2026-04-08

## Status: DWC Sprint In Progress

## Active Plan

**Plan:** plan-sprint-0-engage
**Current Sprint:** DWC — Per-workspace Daemon Configs

## What Was Just Done

- **DWC.2 done** (2026-04-08)

- **DWC.2 COMPLETE** — Concurrent daemon isolation (bpsai-computer)
  - ✓ Cursor files scoped by workspace: `~/.bpsai-computer/{workspace}/signal_cursors.json`
  - ✓ Same for git_cursors.json and ci_cursors.json
  - ✓ PID file per workspace: `~/.bpsai-computer/{workspace}.pid` with write/read/remove helpers
  - ✓ `configure_workspace_logging()` prefixes log messages with `[{workspace}]`
  - ✓ New `workspace.py` module for isolation utilities (PID, logging, paths)
  - ✓ Two configs loaded independently, cursor files don't collide (verified in tests)
  - ✓ 16 new workspace isolation tests, 245/245 passing (6 pre-existing failures excluded)
  - ✓ Arch check clean on all new/modified files

- **DWC.1 done** (2026-04-08)

- **DWC.1 COMPLETE** — Per-workspace config file resolution (bpsai-computer)
  - ✓ `load_config()` accepts optional `workspace` parameter
  - ✓ When workspace provided: tries `~/.bpsai-computer/{workspace}.yaml`, then `config.yaml`
  - ✓ When no workspace: uses `config.yaml` (existing behavior)
  - ✓ CLI `--workspace` flag passes workspace to `load_config()`
  - ✓ Clear `FileNotFoundError`: "No config found. Create ~/.bpsai-computer/{workspace}.yaml"
  - ✓ 6 new workspace resolution tests (specific config, fallback, error, default, overrides, explicit path)
  - ✓ 22/22 config+CLI tests passing, arch check clean

- **CD3.5 done** (2026-04-07)

- **CD3.5 COMPLETE** — End-to-end JWT auth verification (bpsai-computer)
  - ✓ Daemon starts with operator from config + auto-discovered license_id
  - ✓ TokenManager obtains JWT from api.paircoder.ai/api/v1/auth/operator-token
  - ✓ A2A accepts JWT (200 on poll, not 401)
  - ✓ Test dispatch from CC reaches daemon (operator routing matches)
  - ✓ Dispatch result posted back to A2A with valid JWT
  - ✓ Integration test: 6 new e2e tests verify JWT present on all A2A requests
  - ✓ README updated: license install, config with operator/workspace, JWT auth flow
  - ✓ 162/162 tests passing, arch check clean

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

1. DWC.3 — Next task in DWC sprint (if any)
2. Branch protection setup (BPSAI/paircoder#121)

```yaml
project: bpsai-computer
status: in_progress
tests: 235+ (bpsai-computer)
sprints_done: [CD1, CD2, CD2-FIX, CD3]
sprint_active: DWC
```
