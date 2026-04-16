# Track 2 Orchestration — Architecture Decisions Needed

> **For:** David + Mike review
> **Date:** 2026-04-16
> **Context:** Track 1 (extraction) and T2I (contracts, message router) are shipped. Track 2 Orchestration (~90cx) is the last Phase C deliverable. Three architecture questions need answers before we can draft the backlog.

---

## Decision 1: How does CC see project state?

**Question:** CC needs to surface plans, state.md, backlogs, and task status. What's the right mechanism?

### Option A: GitHub MCP Integration

CC uses GitHub's API (or an MCP tool) to read `.paircoder/context/state.md`, `plans/backlogs/*.md`, and `.paircoder/tasks/*.md` directly from repos.

**Pros:**
- Source of truth is always the repo — no sync lag
- Works for any repo in the org without daemon involvement
- Read-only, no new message types needed
- MCP tools already exist for GitHub (file read, search, issues, PRs)
- David and Mike can also browse these files in their IDEs — same data

**Cons:**
- Requires GitHub auth in CC (OAuth scopes or a GitHub App)
- Rate limits on GitHub API for frequent polling
- Can't show in-flight state (daemon is mid-task but hasn't committed yet)
- No push notifications — must poll

### Option B: A2A State Messages

Daemon posts state snapshots to A2A as messages (`type: "state-update"`, `type: "plan-status"`). CC reads from A2A feed like everything else.

**Pros:**
- Consistent with existing CC architecture — everything comes through A2A
- Real-time push via SSE feed (no polling)
- Can include in-flight state (daemon knows what's running right now)
- Works even if GitHub is down

**Cons:**
- Daemon must serialize and post state on every change — adds complexity
- State in A2A diverges from repo if daemon crashes mid-update
- Need new message types and contracts (state-update, plan-status, backlog-summary)
- A2A becomes a state store, not just a message bus — scope creep

### Option C: Hybrid (Recommended?)

- **Live status** (what's running now, active sessions, recent signals): A2A feed (already works)
- **Project artifacts** (plans, backlogs, state.md, task files): GitHub API read-through
- CC has a "Project" panel that fetches from GitHub on demand, with a cache TTL
- Daemon doesn't need to post state — it already posts lifecycle events and signals

**Trade-off:** Two data sources in CC, but each serves its natural purpose. A2A for real-time, GitHub for durable project state.

### What we need to decide:
- [ ] Which option (A, B, C)?
- [ ] If GitHub integration: GitHub App or OAuth scope extension? MCP or direct API?
- [ ] If A2A state messages: which state fields get posted, at what cadence?
- [ ] Does CC need a dedicated "Project" panel, or do plans/state surface in existing panels (Agent Detail, Sessions)?

---

## Decision 2: CC → Daemon communication model

**Question:** Is CC a remote control for daemons (direct connection), or does everything go through the A2A dispatch layer?

### Option A: Always Through A2A (Current Architecture)

```
CC → POST /messages (A2A) → Daemon polls → Executes → POST result (A2A) → CC reads feed
```

**Pros:**
- Already works — Phase A E2E proved this
- A2A handles auth, org scoping, message persistence, audit trail
- CC doesn't need to know daemon addresses
- Multiple daemons on different machines just work (poll same A2A)
- CC can be a public SaaS UI — never touches private infrastructure directly
- Offline daemons pick up work when they reconnect

**Cons:**
- Latency: poll interval (currently 5s) adds delay
- No streaming: daemon output arrives in batches, not real-time
- A2A is a bottleneck — if it goes down, no dispatches flow
- Feels indirect for "run this now" commands

### Option B: Direct WebSocket to Daemon

```
CC ←→ WebSocket ←→ Daemon (real-time bidirectional)
```

**Pros:**
- Sub-second latency, real-time streaming output
- True "remote control" feel — type command, see output immediately
- No poll interval delay

**Cons:**
- Daemon must be directly addressable (public IP/DNS or tunnel)
- Auth model changes — CC authenticates directly with daemon, not A2A
- Breaks multi-tenant model — CC is coupled to specific daemon instances
- Can't be a public SaaS UI without a relay layer (which is just A2A with extra steps)
- Daemon on a laptop behind NAT isn't reachable
- Two communication channels to maintain (WebSocket for live, A2A for persistence)

### Option C: A2A with SSE Streaming Enhancement

```
CC → POST /messages (A2A) → Daemon polls → Executes
Daemon → POST /messages/stream (A2A) → A2A pushes via SSE → CC receives real-time
```

Keep A2A as the dispatch layer but add real-time output streaming through it. Daemon posts output lines to A2A as `session-output` messages (contract already exists in T2I.3). CC's SSE feed picks them up in near-real-time.

**Pros:**
- Best of both: real-time feel with A2A's auth/persistence/multi-tenant model
- CC remains a SaaS-ready UI — no direct daemon coupling
- Output is persisted in A2A for session drill-down (CCH.5 already built for this)
- Contract already exists (`SessionOutputContent` in contracts package)

**Cons:**
- Not true real-time — A2A adds a hop (but milliseconds, not seconds)
- Daemon must post output frequently (per-line or per-batch)
- A2A storage grows with streaming output
- Need to implement the SSE push path in A2A (currently poll-based)

### What we need to decide:
- [ ] Which option (A, B, C)?
- [ ] If A (current): is the 5s poll delay acceptable, or do we reduce it?
- [ ] If C (SSE streaming): does A2A push output events to connected SSE clients, or does CC poll faster for session-output messages?
- [ ] Long-term: will CC ever need to connect to daemons outside our org (customer daemons)? If yes, A2A-only is the right answer.

---

## Decision 3: Plan lifecycle — who creates, who renders, who approves?

**Question:** The Navigator orchestration flow is: parse backlog → create plan → get approval → dispatch drivers → monitor → review. Where does each step happen?

### Current Flow (CLI-based)

```
Human runs `bpsai-pair engage backlog.md`
  → CLI parses backlog (BacklogParser)
  → CLI creates plan (SprintPlanner)
  → CLI dispatches drivers (Dispatcher)
  → CLI monitors completion (CompletionDetector)
  → CLI posts results
```

Everything happens in the CLI process. The human approves by running the command.

### Proposed Flow (Daemon-based)

```
Trigger: CC dispatch ("plan sprint 42 for bpsai-computer")
  → Daemon receives dispatch
  → Navigator agent parses backlog, creates plan
  → Navigator posts plan-proposal to A2A
  → CC renders plan-proposal in UI (Decision 1)
  → Human approves in CC
  → CC posts plan-approved message to A2A
  → Daemon receives approval, dispatches drivers
  → Drivers execute, post status updates
  → CC shows progress (Decision 1 + existing Activity Feed)
  → Review agents run, post review-result
  → CC shows review results
```

### Sub-decisions:

**3a. Who triggers Navigator?**
- Option i: Human types "plan sprint 42" in CC Chat → dispatch to daemon → daemon runs Navigator agent
- Option ii: Human drops backlog file in repo → daemon detects new file → auto-triggers Navigator
- Option iii: Human runs `bpsai-pair engage` locally → CLI orchestrates (status quo)
- Recommended: Option i for CC-driven workflow, Option iii remains available for CLI users

**3b. Who creates the plan document?**
- Option i: Navigator agent (Claude Code session) writes the plan to the repo and posts a summary to A2A
- Option ii: Navigator agent posts full plan to A2A as a `plan-proposal` message, daemon writes to repo on approval
- Recommended: Option i — plan lives in repo (source of truth), summary posted to A2A for CC rendering

**3c. How does approval work?**
- Option i: Human reviews plan in CC, clicks "Approve" → CC posts `plan-approved` message → daemon reads approval → begins dispatching
- Option ii: Human reviews plan in repo (PR review), merges → daemon detects merge → begins dispatching
- Option iii: Human approves in CC Chat ("looks good, send it") → CC posts approval
- Recommended: Option i or iii — CC is the control surface. Option ii is a fallback for CLI-only users.

**3d. How do drivers report progress?**
- `driver-status` contract already exists (T2I.3)
- Daemon posts status updates as tasks start/complete/fail
- CC renders in Activity Feed + Agent Detail panel (already built in CCH)
- No decision needed — just implement

**3e. What about the extracted code?**
The planning, orchestration, status, and review modules extracted in Track 1 are available in bpsai-computer. The orchestration backlog adapts them:

| Module | Current State | Adaptation for Daemon |
|--------|--------------|----------------------|
| `planning/backlog.py` | Parses markdown from file | Works as-is — Navigator agent reads file from repo |
| `planning/planner.py` | Creates SprintBacklog | Works as-is — Navigator agent calls it |
| `planning/author.py` | Generates next sprint | Needs parameterizable ID format |
| `orchestration/navigator.py` | Synchronous, hard deps | Needs async adaptation for daemon event loop |
| `orchestration/dispatcher.py` | Subprocess fire-and-forget | Types-only — daemon's own dispatcher handles execution |
| `status/completion.py` | Poll-based (git/channel) | Needs A2A lifecycle detection |
| `status/updater.py` | Local YAML writes | Needs A2A-backed variant for CC visibility |
| `review/automation.py` | Uses framework Dispatcher | Needs to use daemon's dispatch + A2A status posting |

### What we need to decide:
- [ ] 3a: Navigator trigger — CC Chat dispatch, file detection, or CLI?
- [ ] 3b: Plan creation — repo-first or A2A-first?
- [ ] 3c: Approval mechanism — CC button, Chat confirmation, or PR merge?
- [ ] Does the daemon need to run Navigator as a Claude Code session, or can it use the extracted Python code directly?

---

## Impact on Backlog Sizing

Depending on decisions, the ~90cx estimate shifts:

| Decision | If simpler option | If richer option | Delta |
|----------|------------------|-----------------|-------|
| D1: Project state | GitHub API read-through (~15cx) | A2A state messages (~25cx) | +10 |
| D2: Communication | Keep current A2A polling (~0cx) | SSE streaming (~20cx) | +20 |
| D3: Plan lifecycle | CC Chat trigger + Chat approval (~30cx) | Full UI with approval button + progress view (~50cx) | +20 |

Conservative path (simpler options): ~90cx as estimated
Rich path (all richer options): ~140cx

---

## Recommended Starting Point

If you want to ship Phase C quickly and iterate:

1. **D1: Option C (Hybrid)** — GitHub for project artifacts, A2A for live status. Start with GitHub read-through in a new "Project" panel.
2. **D2: Option A (Current)** — Keep A2A dispatch. Reduce poll interval to 2s. SSE streaming is a Phase D enhancement.
3. **D3: Options i/i/iii** — CC Chat triggers Navigator, Navigator writes plan to repo + posts summary to A2A, human approves in Chat ("send it"). Simplest path that enables the full loop.

This keeps the backlog at ~90cx and delivers the Phase C completion criteria: "type 'plan sprint' in CC Chat, see it happen, review results."

The richer options (dedicated Project panel with GitHub integration, SSE streaming, approval buttons) are natural Phase D work once the basic loop works.
