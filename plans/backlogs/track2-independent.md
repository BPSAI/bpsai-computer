# Track 2 Independent — A2A Wiring + ABC Review + Contract Tests

> **Budget:** ~60-75cx
> **Repos:** bpsai-a2a, paircoder_api, bpsai-computer, bpsai-framework (read-only)
> **Sprint ID:** T2I
> **Owner:** Mike
> **Depends on:** Nothing (runs while David extracts Track 1)
> **Feeds into:** Track 2 orchestration tasks (drafted after David's receiving modules land)

---

## Context

Track 2 (Computer Orchestration, ~150cx) depends on Track 1 extraction code landing in bpsai-computer. But several pieces can start now:

1. **A2A endpoints** that Track 2 and CCH both need
2. **Framework ABC review** to flag gaps to David before he extracts (Risk R9)
3. **Message schema contracts** to prevent the 4-mismatch pattern from Phase A (Risk R7)
4. **Permission manifest support** in A2A for D-024 channel escalation (Risk R4)

This backlog covers Mike's independent work while David runs FW-C1.x through FW-C2.x.

---

## Risk Register Cross-Reference

| Risk | Task(s) | Mitigation |
|------|---------|------------|
| R4 (.claude/ path blocks) | T2I.5 | Channel escalation routing in A2A |
| R7 (schema mismatches) | T2I.3 | Shared message schemas + contract tests |
| R9 (ABCs insufficient) | T2I.1 | Review and flag gaps before extraction |
| R3 (session-resume blocks CCH.5) | T2I.2 | Build endpoint early |

---

### Phase 1: ABC Review + Schema Contracts

### T2I.1 — Framework ABC review for Computer fitness | Cx: 8 | P0

**Description:** Review all framework abstractions that Track 1 will extract into bpsai-computer and assess fitness for Computer's orchestration needs. Produce a gap report for David so he can extend ABCs during extraction rather than after.

Known gaps from initial analysis:
- **NavigatorOrchestrator:** Hard dep on BacklogDeliverer, no injectable decision logic, synchronous only
- **Dispatcher:** Fire-and-forget, no lifecycle/streaming interface
- **CompletionDetector:** Poll-only (channel or git), no streaming/webhook
- **StatusUpdater:** Sequential, no async update/notification
- **HeadlessHook/PathClass:** Hardcoded working area paths, not extensible
- **NextSprintAuthor:** Hardcoded task ID format (`T{prefix}.{seq}`), non-parameterizable phase logic
- **BacklogParser:** Strict regex patterns, no programmatic backlog building API

Assess each gap: is it a blocker (must fix before extraction), a follow-up (Computer wraps it), or not applicable (Computer reimplements locally)?

**AC:**
- [ ] Gap report written to `bpsai-computer/docs/design/framework-abc-review.md`
- [ ] Each gap classified as blocker / wrap / reimplement
- [ ] Blockers filed as issues on bpsai-framework with tag `phase-c`
- [ ] David has reviewed and acknowledged the gap report
- [ ] No surprise gaps surface during Track 2 wiring

---

### T2I.3 — Shared message schema definitions | Cx: 10 | P0

**Description:** Define the message schemas used between CC, daemon, and A2A as Pydantic models in a shared location. During Phase A E2E we hit 4 schema mismatches because each repo defined its own format. Phase C adds new message types (plan proposals, driver status, review results, session-resume) which multiplies the surface area (Risk R7).

Options:
- **Option A:** Small `bpsai-contracts` package on PyPI — all three repos depend on it
- **Option B:** Schema definitions in bpsai-a2a (source of truth), snapshot tests in CC and daemon
- **Option C:** JSON Schema files in bpsai-a2a, validated in each repo's test suite

Decide on approach, implement it, and migrate existing message types (`dispatch`, `lifecycle`, `result`, `signal`).

**AC:**
- [ ] All existing A2A message types have a single source-of-truth schema definition
- [ ] New Phase C message types have schema definitions before implementation
- [ ] CC, daemon, and A2A each have tests that validate against the shared schema
- [ ] Adding a new message type requires updating one place, not three
- [ ] Schema for `plan-proposal`, `driver-status`, `review-result`, `session-resume` defined (even if endpoints don't exist yet)

---

### Phase 2: A2A Endpoints

### T2I.2 — Session-resume message type | Cx: 8 | P0

**Description:** New A2A message type so CC (and future Navigator) can request the daemon resume a paused or interrupted session. Shared dependency for CCH.5 (session drill-down) and Track 2 (Navigator resume flow). Risk R3 mitigation.

The daemon already has `ResumeMessage` dataclass (`dispatcher.py` line ~35) with `session_id` and `target`. The A2A side needs:
- Message type `session-resume` accepted by `POST /messages`
- Routing: `to_project` + `operator` + `workspace` targeting (same as dispatch)
- Daemon poll picks it up, constructs `ResumeMessage`, calls `claude --resume <session_id>`

**AC:**
- [ ] `POST /messages` accepts `type: "session-resume"` with `session_id` in metadata
- [ ] Daemon polls receive session-resume messages
- [ ] Daemon correctly constructs `ResumeMessage` and resumes the Claude Code session
- [ ] Lifecycle events posted for resumed sessions (session-resumed, session-complete/failed)
- [ ] If session_id is invalid or expired, daemon posts error lifecycle event
- [ ] Contract test validates schema between CC, A2A, and daemon

---

### T2I.4 — License-to-org lookup (retire operator workaround) | Cx: 12 | P0

**Description:** Currently, operator tokens can assert `org_id` via the `purpose: "operator"` exception in `jwt_validator.py`. This is a Phase A workaround — the token issuer (paircoder-api) shouldn't be trusted to assert org membership. Proper fix: A2A resolves `org_id` from `license_id` by calling paircoder-api's license lookup endpoint (or caching the mapping).

This removes the security gap where any paircoder-api token with `purpose: "operator"` can claim any org_id.

**AC:**
- [ ] A2A resolves `org_id` from `license_id` on token validation (not from JWT claims)
- [ ] `purpose: "operator"` exception removed from `jwt_validator.py`
- [ ] Lookup is cached with reasonable TTL (e.g., 5 min) to avoid per-request API calls
- [ ] If license_id has no org association, request proceeds without org scoping (backward compat)
- [ ] paircoder-api has an endpoint or the existing one returns org_id in license data
- [ ] All existing daemon auth flows continue to work
- [ ] Contract test validates the auth chain end-to-end

---

### T2I.5 — Channel escalation routing (D-024) | Cx: 8 | P1

**Description:** When a driver hits a permission wall on non-`.claude/` paths, it sends an A2A channel message requesting escalation. A2A needs to route this to the appropriate approval authority (Navigator or human operator). D-024 Hybrid E+F — this is the "F" part (channel escalation at runtime).

New message flow:
1. Driver posts `type: "permission-request"` to A2A with `path`, `operation`, `reason`
2. A2A routes to operator's approval queue (filterable in CC)
3. Operator (or Navigator) approves/denies via `type: "permission-response"`
4. Driver polls for response, updates local containment config, retries

**AC:**
- [ ] `permission-request` message type accepted by `POST /messages`
- [ ] `permission-response` message type accepted by `POST /messages`
- [ ] Request includes: `path`, `operation` (read/write/execute), `reason`, `task_id`
- [ ] Response includes: `approved` (bool), `scope` (file/directory/glob), `ttl` (seconds)
- [ ] CC can filter messages by `type: "permission-request"` for approval UI
- [ ] Schema defined in shared contracts (T2I.3)

---

### T2I.6 — Notification severity routing | Cx: 5 | P1

**Description:** A2A needs severity-based filtering so CC can populate the Notifications panel (CCH.7) without polling all messages. Messages already have a `severity` field but A2A doesn't support filtering by it on `GET /messages/feed`.

**AC:**
- [ ] `GET /messages/feed` accepts `severity` query parameter (info, warning, error, critical)
- [ ] `GET /messages/feed` accepts `min_severity` for threshold filtering (e.g., min_severity=warning returns warning+error+critical)
- [ ] Existing messages without severity default to `info`
- [ ] Contract test validates severity filtering

---

### T2I.7 — Workspace listing endpoint | Cx: 5 | P1

**Description:** CCH.9 (workspace selector in CC header) needs a list of workspaces accessible to the current operator/org. This endpoint belongs in paircoder-api since it owns the license/org/workspace relationship.

**AC:**
- [ ] `GET /workspaces` returns workspaces for the authenticated operator
- [ ] Response includes `workspace_id`, `name`, `workspace_root` (optional), `status`
- [ ] Scoped by org_id from JWT claims
- [ ] CC can call this to populate the workspace dropdown
- [ ] Works with both portal JWT and operator JWT auth

---

## Phase 3: Computer Daemon Hardening

### T2I.8 — Daemon multi-message-type support | Cx: 5 | P0

**Description:** The daemon currently handles `dispatch` and `resume` message types. Track 2 adds `plan-proposal`, `permission-request`, `permission-response`, and potentially `review-request`. The dispatcher's `_parse_dispatch` method needs to be a proper message type router rather than a conditional chain.

**AC:**
- [ ] Dispatcher has a registry of message type handlers
- [ ] Adding a new message type is: define handler function + register it
- [ ] Unknown message types are logged and acked (not silently dropped, not crashed)
- [ ] Existing dispatch and resume flows unchanged
- [ ] Tests cover each registered message type

---

## Summary

| Task | Title | Cx | Priority | Repo | Risk |
|------|-------|----|----------|------|------|
| T2I.1 | Framework ABC review | 8 | P0 | bpsai-computer (output) | R9 |
| T2I.2 | Session-resume message type | 8 | P0 | bpsai-a2a + bpsai-computer | R3 |
| T2I.3 | Shared message schemas | 10 | P0 | bpsai-a2a (primary) | R7 |
| T2I.4 | License-to-org lookup | 12 | P0 | bpsai-a2a + paircoder_api | — |
| T2I.5 | Channel escalation routing | 8 | P1 | bpsai-a2a | R4 |
| T2I.6 | Notification severity routing | 5 | P1 | bpsai-a2a | — |
| T2I.7 | Workspace listing endpoint | 5 | P1 | paircoder_api | — |
| T2I.8 | Daemon message type router | 5 | P0 | bpsai-computer | — |
| **Total** | | **~61** | | | |

### Execution Order

```
Phase 1 (no deps, start immediately):
  T2I.1 (ABC review) — output feeds David's extraction decisions
  T2I.3 (shared schemas) — foundation for all A2A work below

Phase 2 (after T2I.3 schemas exist):
  T2I.2 (session-resume) — unblocks CCH.5 + Track 2 Navigator resume
  T2I.4 (license→org lookup) — removes security workaround
  T2I.8 (daemon message router) — prep for new message types

Phase 3 (after Phase 2 endpoints exist):
  T2I.5 (channel escalation) — D-024 runtime path
  T2I.6 (notification severity) — unblocks CCH.7
  T2I.7 (workspace listing) — unblocks CCH.9
```

### Handoff to Track 2 Orchestration

When David's FW-C1.x and FW-C2.x extraction tasks land and receiving modules exist in bpsai-computer, a second backlog will be drafted covering the orchestration wiring:
- Navigator orchestration using extracted NavigatorOrchestrator
- Backlog parsing + sprint authoring using extracted planners
- Dispatch routing + operator assignment using extracted dispatch
- Status updater + review automation using extracted status code

That backlog will incorporate findings from T2I.1 (ABC review) and use the schemas from T2I.3.
