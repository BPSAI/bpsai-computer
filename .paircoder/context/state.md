# Current State

> Last updated: 2026-04-15

## Status: Track 2 Independent Sprint In Progress

## Active Plan

**Plan:** plan-sprint-2-engage
**Current Sprint:** T2I — Track 2 Independent

## What Was Just Done

- **T2I.5 done** (2026-04-15)

- **T2I.5 COMPLETE** — Channel escalation routing (bpsai-computer)
  - ✓ `PermissionRequestContent` Pydantic model: `path`, `operation` (read/write/execute), `reason`, `task_id`
  - ✓ `PermissionResponseContent` Pydantic model: `approved` (bool), `scope` (file/directory/glob), `ttl` (seconds), `request_id` (optional)
  - ✓ Field validators: operation must be read/write/execute, scope must be file/directory/glob, ttl >= 0
  - ✓ Both models exported in `contracts/__init__.py` and registered in `schema_export.py` for cross-repo validation
  - ✓ `A2AClient.post_permission_request()` — POST /messages with type=permission-request
  - ✓ `A2AClient.post_permission_response()` — POST /messages with type=permission-response
  - ✓ `poll_dispatches()` now includes permission-response in poll filter (daemon receives responses)
  - ✓ Daemon registers `permission-response` handler by default, acks with "permission-noted"
  - ✓ Malformed permission-response content logged as warning, not crash
  - ✓ 22 new contract tests + 15 new escalation tests (A2A client + daemon routing)
  - ✓ 607/607 tests passing, arch check: daemon.py import violation is pre-existing

- **T2I.8 done** (2026-04-15)

- **T2I.8 COMPLETE** — Daemon multi-message-type support (bpsai-computer)
  - ✓ `_message_handlers` registry dict on Daemon, populated with dispatch/resume at init
  - ✓ `register_message_handler(type, handler)` — adding a new type is define + register
  - ✓ `_route_message()` replaces if/else chain in `run()` loop
  - ✓ Unknown message types: logged as warning + acked as `unsupported_message_type`
  - ✓ Existing dispatch and resume flows unchanged (35 existing tests still pass)
  - ✓ 12 new tests: registry structure (5), routing (4), unknown type handling (3)
  - ✓ 47/47 tests passing, arch check clean on test file (daemon.py has pre-existing import violation)

- **T2I.3 done** (2026-04-14)

- **T2I.3 COMPLETE** — Shared message schema definitions (bpsai-computer)
  - ✓ `src/computer/contracts/` package with Pydantic v2 models as single source of truth
  - ✓ All existing A2A message types: ChannelEnvelope, DispatchContent, ResumeContent, DispatchResultContent, SessionStarted/Complete/Failed, SessionOutput, SignalBatch, Heartbeat
  - ✓ Phase C types defined: PlanProposalContent, DriverStatusContent, ReviewResultContent, SessionResumeContent
  - ✓ JSON Schema export via `all_schemas()` for cross-repo validation
  - ✓ 32 new contract tests (20 existing types + 12 Phase C/export), 558/558 passing
  - ✓ Arch check clean on all new files

- **DBS.1 done** (2026-04-09)

- **DBS.1 COMPLETE** — Update collectors to use /signals/batch (bpsai-computer)
  - ✓ SignalPusher, GitSummaryCollector, CISummaryCollector POST to `/signals/batch`
  - ✓ Payload format: `{operator, repo, signals: [{signal_type, severity, timestamp, payload, signal_id}]}`
  - ✓ Deterministic `signal_id` via SHA-256 hash of signal content (16 hex chars)
  - ✓ Timestamps normalized to `YYYY-MM-DDTHH:MM:SSZ` (canonical UTC, no microseconds)
  - ✓ Fire-and-forget preserved — batch failure logged, doesn't block daemon
  - ✓ Tests updated: 61 collector tests passing, arch check clean
  - ✓ 2 new tests: deterministic signal_id, different signals get different IDs

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

1. DBS.2 — Next task in DBS sprint (if any)
2. Branch protection setup (BPSAI/paircoder#121)

```yaml
project: bpsai-computer
status: in_progress
tests: 235+ (bpsai-computer)
sprints_done: [CD1, CD2, CD2-FIX, CD3, DWC]
sprint_active: DBS
```
