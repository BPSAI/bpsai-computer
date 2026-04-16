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

## Decision 2: What IS Command Center's relationship to Computer Prime?

**The fundamental question:** Is CC a chat UI that composes dispatch messages for A2A, or is it the actual interface to Computer Prime — a direct connection to a daemon where the AI orchestrates in real-time?

This isn't a technical detail. It determines what CC becomes as a product.

### Model A: Chat → Dispatch Layer (Current)

CC is a chat UI. Human types intent. CC posts a message to A2A. Daemon picks it up seconds later. Fire-and-forget. Results trickle back through the feed.

```
Human → CC Chat → POST /messages (A2A) → Daemon polls → Executes → Results via feed
```

**What it feels like:** Sending emails to a robot. You describe what you want, wait, check back later.

**Where it works well:**
- Async work (fire a sprint, come back tomorrow)
- Multi-machine fleet (David's daemon + Mike's daemon poll same A2A)
- Public SaaS — CC never touches private infrastructure
- Offline daemons pick up work when they reconnect
- Audit trail for everything that happened

**Where it breaks down:**
- Latency: 5s poll delay makes interactive work painful
- No streaming: can't watch Claude Code think in real time
- Indirect: "run this now" feels like putting a letter in a mailbox
- The operator is removed from the loop — you dispatch and hope

### Model B: CC as Computer Prime's Frontend

CC establishes a persistent session with a specific daemon. The daemon IS Computer Prime — it has the AI brain, repo access, agent dispatch. CC is just the rendering layer. Like VS Code Remote or claude.ai/code — the UI is in the browser, the intelligence runs on the machine.

```
Human → CC ←→ Persistent Session ←→ Daemon (Computer Prime)
                                       ├── reads repos
                                       ├── dispatches agents
                                       ├── streams output to CC
                                       └── posts audit trail to A2A
```

**What it feels like:** A cockpit. You see what Computer Prime sees. You can steer. Output streams live. You approve plans inline. You watch drivers execute.

**Where it works well:**
- Interactive orchestration — "plan sprint 42" and watch it happen
- Real-time output streaming — see Claude Code's thinking as it runs
- Direct control — pause, redirect, resume mid-session
- Natural for the "I'm at my desk driving Computer Prime" use case

**Where it gets complicated:**
- Daemon must be reachable from CC (direct address, tunnel, or relay)
- Auth changes — CC authenticates with daemon, not just A2A
- Daemon on a laptop behind NAT needs a tunnel (ngrok, Cloudflare Tunnel, tailscale)
- Can't be a pure public SaaS without a relay/proxy layer
- Two modes: "connected to a daemon" vs "browsing the feed offline"

**A2A's role changes:** A2A becomes the audit/persistence/offline layer, not the communication channel. Daemon still posts lifecycle events and signals to A2A. CC can still browse the A2A feed when not connected to a daemon. But live interaction goes direct.

### Model C: MCP Bridge

CC connects to the daemon as an MCP client. Daemon exposes MCP tools (read-file, run-tests, dispatch-agent, get-plan-status, browse-signals). CC's AI uses those tools to interact with the machine. This is how Claude Code's IDE extensions work — MCP tools bridge the gap.

```
Human → CC (with AI) → MCP tools → Daemon (MCP server)
                                      ├── tool: read_file(path)
                                      ├── tool: dispatch_agent(spec)
                                      ├── tool: get_plan_status(plan_id)
                                      ├── tool: list_sessions()
                                      └── tool: stream_output(session_id)
```

**What it feels like:** Like having Claude Code in the browser, but with Computer Prime's tools. The AI in CC can read repos, dispatch work, check status — all through MCP.

**Where it works well:**
- Leverages existing MCP ecosystem (Claude Code already speaks MCP)
- Daemon becomes a tool provider, not a message consumer
- CC's AI can compose complex operations (read state → decide → dispatch → monitor)
- Clean separation: CC owns the AI conversation, daemon owns the machine

**Where it gets complicated:**
- Same reachability problem as Model B (daemon must be addressable)
- MCP is request/response, not streaming — need a separate channel for live output
- Daemon needs an MCP server implementation (new code)
- CC needs an MCP client in the browser (or in a Next.js server route)

### Model D: Hybrid — A2A for Async, Direct for Live

Both models coexist. A2A is the default — always available, works offline, handles fleet operations. When an operator wants interactive control, CC establishes a direct session (Model B or C) with a specific daemon.

```
Default mode:  CC → A2A → Daemon (async dispatch, fleet-wide)
Live mode:     CC ←→ Daemon (direct session, single machine)
Both modes:    Daemon → A2A (audit trail, signals, lifecycle events always posted)
```

**What it feels like:** You can browse the fleet dashboard (A2A-backed) anytime. When you want to drive, you "connect" to a daemon and get real-time control. Like having both a mission control dashboard and a direct radio to the astronaut.

**Where it works well:**
- Best of both worlds
- Public SaaS users get the A2A experience (Model A)
- Power users (Mike, David) get direct control (Model B/C)
- Graceful degradation — if daemon goes offline, CC still shows the A2A feed

**Where it gets complicated:**
- Two code paths for interaction
- UI must handle connected vs disconnected state
- More surface area to test and maintain

### What we need to decide:
- [ ] Which model? (A = chat/dispatch, B = direct frontend, C = MCP bridge, D = hybrid)
- [ ] If B/C/D: how does the daemon become reachable? (Tunnel service? Tailscale? Only works on same network?)
- [ ] If B/C/D: what's the connection protocol? (WebSocket? MCP over HTTP? gRPC?)
- [ ] If D: does live mode use the same CC UI or a separate "cockpit" view?
- [ ] Product question: will customers run CC against their own daemons, or only against our hosted A2A? This determines whether Model A is sufficient long-term.
- [ ] Scope question: is this a Phase C decision or a Phase D decision? If Phase C, it changes what Track 2 builds (~90cx becomes ~150-200cx). If Phase D, we ship the basic loop with Model A now and evolve.

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
| D2: CC↔Daemon model | Model A — keep dispatch layer (~0cx) | Model B/C — direct session (~60-80cx) | +60-80 |
| D3: Plan lifecycle | CC Chat trigger + Chat approval (~30cx) | Full UI with approval button + progress view (~50cx) | +20 |

Conservative path (Model A + GitHub + Chat approval): ~90cx
Mid path (Model A + GitHub + approval UI): ~110cx
Rich path (Model D hybrid + GitHub + approval UI): ~170-200cx

---

## Recommended Starting Point

Two viable strategies depending on where you want CC to end up:

### Strategy 1: Ship the loop, evolve the cockpit (Phase C = ~90cx, Phase D = cockpit)

1. **D1: Option C (Hybrid)** — GitHub for project artifacts, A2A for live status.
2. **D2: Model A (Dispatch)** — Keep A2A dispatch. Reduce poll interval to 2s. It works, it's proven.
3. **D3: Chat trigger + Chat approval** — Simplest path to the Phase C completion criteria.

Then Phase D adds the direct session capability (Model B/C/D) once the basic Navigator loop works end-to-end. You ship Phase C faster and learn what the cockpit actually needs from real usage.

### Strategy 2: Build the cockpit now (Phase C = ~170-200cx)

1. **D1: Option C (Hybrid)** — Same.
2. **D2: Model D (Hybrid)** — A2A for async/fleet, direct session for interactive. Build the connection layer now.
3. **D3: Full UI** — Approval buttons, plan viewer, streaming output in CC.

Bigger investment but CC becomes the real product — not a chat wrapper around A2A. If the vision is "CC is how you operate Computer Prime," this is the direct path.

### The product question that decides it:

**Is CC a dashboard for monitoring your agent fleet, or is it the cockpit for flying Computer Prime?**

- Dashboard = Strategy 1. A2A is the backbone. CC renders what happened. Chat dispatches work.
- Cockpit = Strategy 2. CC IS the interface. You connect to your daemon. You see what it sees. You steer.

Both are valid. The dashboard ships faster and serves the SaaS use case. The cockpit is what you actually want to use daily.
