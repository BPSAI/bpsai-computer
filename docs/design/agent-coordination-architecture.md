# Agent Coordination Architecture — Cross-Session Task Orchestration

> **Created:** 2026-03-23
> **Status:** Draft — David review: recursive Computer model corrections applied (2026-03-23)
> **Authors:** Mike + Claude (Navigator analysis), David corrections (Computer hierarchy framing)
> **Depends on:** bpsai-coordination channel design, Computer adaptive loop, Claude Code v2.1.80+ channels
> **Context:** Synthesizes coordination channel design, adaptive loop proposal, and Claude Code channels reference into a concrete agent dispatch and review model.

---

## The One-Sentence Version

Computer₁ (the project Navigator) orchestrates tasks by launching Driver, Security, and IT agents as **separate Claude Code sessions** that communicate through the `bpsai-coordination` channel — and Computer₀ orchestrates the Computer₁ instances the same way.

---

## The Recursive Computer Model

The architecture is recursive. Every Navigator is a Computer at its own scale:

- **Computer₁** is the Navigator for a project. It runs inside the target repo, has the project's CLAUDE.md, tools, and permissions. It dispatches Drivers, Reviewers, Security agents within that project.
- **Computer₀** is the Navigator of Navigators. It orchestrates across projects. It dispatches Computer₁ instances, not Drivers directly.
- **The boundary is fluid.** A single-repo Navigator that decides a new repo needs to be created — and spawns it — becomes Computer₀ at that moment. The new project gets its own Computer₁. This isn't an upgrade or a configuration change. It's an emergent property of the project's complexity.

This distinction matters because it determines where dispatch logic lives, who talks to whom, and how the coordination channel is used.

---

## Why Cross-Session, Not Subagents

Claude Code's Agent tool spawns subagents inside a single session. That works for quick searches or parallel research within one repo. It doesn't work for our dispatch model because:

- **Drivers need worktree isolation** for parallel execution — multiple Drivers modifying the same repo need separate working copies
- **Reviewers need to operate on completed work** without the Driver's session state, context, or in-progress mutations
- **Computer₀ dispatches Computer₁ instances into different repos** — these are separate processes with separate contexts by nature
- **Sessions dispatched via `bpsai-pair engage` or Remote Control `--spawn`** create separate Claude Code processes, which is the right isolation boundary

Note: ORCHESTRATION.md describes "Framework Navigator dispatches driver agents directly into the sibling repo" as an **interim/emergency pattern** — used when the Framework Navigator (acting as CNS) needs to apply direct fixes because there's no way to notify a project's Navigator. In the target architecture, Computer₀ dispatches to Computer₁, and Computer₁ dispatches its own Drivers. The coordination channel replaces the need for emergency direct dispatch.

---

## Workflow Layering: Graduation, Not Opt-In

The cross-session coordination model is not a premium feature that projects "opt in" to. It's the natural evolution of any non-trivial project. The coordination channel infrastructure is dormant until needed.

| Context | What runs | Who is Computer? | Channels? |
|---------|-----------|-----------------|-----------|
| **Single dev, single repo** | `bpsai-pair engage` → Navigator session | Navigator IS Computer₁ (and Computer₀, trivially) | Dormant |
| **Single repo, needs review** | Navigator spawns Security/IT as local subagents or cross-session | Computer₁ dispatches review agents | Optional |
| **Project spawns a second repo** | Navigator dispatches to new repo | Navigator graduates to Computer₀. New repo gets Computer₁ | Active |
| **Multi-repo orchestration** | Computer₀ adaptive loop dispatches everywhere | Explicit Computer₀/Computer₁ hierarchy | Active |

A PairCoder user running `bpsai-pair engage sprint-42.md` in their repo gets exactly what they get today: a Claude Code session that does the work. The Navigator IS Computer₁ for that project. If the project never grows beyond one repo, it stays that way.

The moment that Navigator decides a new agent, repo, or coordination boundary is needed — the moment it "assimilates into the Borg" — it becomes Computer₀ and the infrastructure activates. This isn't a configuration change. It's the system recognizing that the project's complexity has crossed a threshold.

**Single-repo review is still subagent-based.** Within one repo, a session can spawn Security/IT review agents using the Agent tool (subagents within the same session). This is the existing pattern and continues to work. Cross-session coordination adds the *multi-repo* dimension that emerges as projects grow.

---

## Transport Architecture: Channels + A2A Are Different Layers

A common question: does the `bpsai-a2a` backend conflict with the local MCP channel model? No — they're complementary layers.

```
Claude Code session (machine A)
    ↕ stdio / MCP protocol
Channel MCP server (local process, spawned by Claude Code as subprocess)
    ↕ HTTPS
bpsai-a2a backend (single remote instance)
    ↕ HTTPS
Channel MCP server (local process on machine B)
    ↕ stdio / MCP protocol
Claude Code session (machine B)
```

**Claude Code never talks to bpsai-a2a directly.** The channel MCP server is a local bridge: it speaks MCP/stdio to Claude Code on one side and HTTPS to the a2a backend on the other. Claude Code just sees `<channel>` tags arriving — it doesn't know or care about the transport behind them.

**For deployed autonomous systems:** Single bpsai-a2a server instance. Every channel MCP server points at it. This is what the coordination channel design already specifies — all messages route through bpsai-a2a as the single source of truth. The a2a backend handles persistence, cross-machine relay, and replay of unacknowledged messages on session connect.

**For local development (same machine):** Same architecture, but everything is localhost. The a2a backend could even be a lightweight local process during development — the channel server doesn't care where the endpoint is.

---

## How It Works

### The Basic Loop

```
1. Navigator receives task (from Computer₀ DISPATCH or human)

   PRE-FLIGHT (optional, based on task risk profile)
2. Navigator launches Security pre-flight session with task spec
   └── "What are the constraints and risks for this task?"
   └── Returns: security policies, red flags, required patterns
3. Navigator launches IT pre-flight session with task spec
   └── "What infrastructure constraints apply?"
   └── Returns: deployment targets, approved base images, network policies
   (These are cheap — reading a task description, not a codebase)

   EXECUTION
4. Navigator launches Driver session in project repo
   └── Driver starts with: --channels bpsai-coordination
   └── Driver's prompt includes pre-flight constraints from steps 2-3
5. Driver works (writes code, runs tests, commits)
6. Driver sends "done" via channel → Navigator receives it

   POST-REVIEW
7. Navigator launches Security review session (same branch)
8. Navigator launches IT review session (same branch)
   └── Both review the Driver's work on disk
9. Security/IT send findings via channel → Navigator receives them
10. If findings: Navigator forwards to Driver via channel
    └── Driver still has its session open, full context intact
    └── Driver fixes, sends "done" again → back to step 7
11. If clean: Navigator merges / marks complete
```

The pre-flight step prevents the Driver from making architectural mistakes that get caught in post-review and require expensive rewrites. Security reviewing a task spec is far cheaper than Security reviewing 14 changed files and saying "start over with a different auth pattern."

### What the Driver Sees

The Driver session is a normal Claude Code session with the coordination channel enabled. When it finishes work:

```
Driver sends via channel:
  type: "task-status"
  status: "complete"
  content: "Implementation done. 14 files changed, tests pass."
  task_id: "T42.3"
  branch: "feat/data-layer"
```

The Driver session stays alive. When review findings come back:

```
<channel source="bpsai-coordination" type="review-feedback" task_id="T42.3" severity="must-fix">
SQL injection in data_layer.py:47 — needs parameterized query.
Missing TLS config in deploy.yaml.
</channel>
```

The Driver acts on the findings **with full context** — it remembers every file it touched, every decision it made. No re-discovery, no context rebuilding.

### What the Navigator Sees

The Navigator is the hub. All messages route through it. It sees:

```
<channel source="bpsai-coordination" type="task-status" role="driver" task_id="T42.3">
Implementation done. 14 files changed, tests pass.
</channel>

<channel source="bpsai-coordination" type="task-status" role="security" task_id="T42.3">
1 must-fix: SQL injection in data_layer.py:47.
</channel>

<channel source="bpsai-coordination" type="task-status" role="it" task_id="T42.3">
1 must-fix: TLS not configured in deploy.yaml.
</channel>
```

Navigator consolidates findings and forwards to Driver. Simple routing logic, no intelligence needed at this layer.

---

## Four Design Decisions

### 1. Pre-Flight Security/IT Check Before Driver Starts

**Decision:** Before dispatching the Driver, the Navigator optionally spawns Security and IT with the *task spec* (not code) to gather constraints and flag risks upfront.

**Why:**
- Security reviewing a task description is cheap — minutes, not the 30+ minutes of reviewing a full implementation
- Prevents the expensive pattern: Driver builds → Security reviews → "wrong auth pattern, start over"
- The Driver receives pre-flight output as part of its prompt: approved patterns, required constraints, known risks
- Pre-flight is optional — Navigator decides based on task risk profile (credential handling, infrastructure changes, new external dependencies warrant it; a CSS fix doesn't)

**What pre-flight is NOT:** It's not a gate that blocks all work. It's the equivalent of a 5-minute standup question: "anything I should know before I start this?"

### 2. Security/IT Post-Review: Launch When Needed (Not Spawn and Wait)

**Decision:** Navigator launches Security and IT sessions *after* the Driver reports completion. They don't sit idle waiting.

**Why:**
- An idle Claude Code session is a running process burning compute for nothing
- Security/IT don't need the Driver's journey — they need the Driver's output (the diff on the branch)
- Review sessions are short-lived and focused: read the diff, check policies, report findings

**Future evolution:** A long-lived Security session that reviews work from *all* projects as it arrives (Agent Lounge pattern, portfolio item 38). But that's v3.0.0 — launch-when-needed is right for now.

### 3. Driver Stays Alive During Review

**Decision:** The Driver session stays open after reporting completion. It waits for channel messages.

**Why:**
- Rebuilding context is expensive — a Driver that worked for 30 minutes built up knowledge of 50+ files, test results, and design decisions
- Review takes ~10 minutes. Keeping the session alive for 10 minutes is far cheaper than re-creating all that context
- The channel delivers findings directly into the live session — the Driver can fix surgically

**Fallback:** If the Driver session dies (crash, timeout), the Navigator detects the missing ack and spawns a new Driver session with the findings as input. Less efficient, but resilient.

### 4. Mid-Task Questions: Supported, Not Required

**Decision:** The Driver *can* ask domain-specific questions mid-task via channel. It doesn't have to stop and wait.

**Example flow:**
```
Driver encounters credential storage question
  → Sends: type "coordination-issue", content "Key Vault or .env for API keys?"
  → Continues working on non-blocked items
  → Navigator routes question to Security session (or answers directly)
  → Answer arrives via channel
  → Driver incorporates answer when it reaches that work item
```

**Why this matters:** In a human team, the dev doesn't stop coding to wait for a Slack reply from security. They context-switch to unblocked work. Same pattern here. The Driver's instructions include: *"If you need domain expertise, send a coordination-issue and continue with unblocked work."*

**Why it's not required for v1:** The post-work review loop (steps 5-8 above) catches 80% of issues. Mid-task questions are an optimization for reducing review-fix cycles, not a prerequisite for the system to work.

---

## Message Types on the Coordination Channel

Building on the existing `bpsai-coordination` channel design, these additions support the task loop:

| Type | Direction | Purpose |
|------|-----------|---------|
| `task-dispatch` | Navigator → Agent | "Here's your assignment" — task spec, constraints, policies |
| `task-status` | Agent → Navigator | "Done" / "blocked" / "findings" — with task_id correlation |
| `coordination-issue` | Agent → Navigator | Mid-task question routed to the right specialist |
| `review-feedback` | Navigator → Driver | Consolidated findings from Security + IT |
| `blocker-alert` | Any → Navigator | Andon Cord — immediate escalation |

**Existing types unchanged:** `sprint-backlog`, `status-update`, `coordination-issue` (cross-project) all work as designed.

**Key addition:** Every message carries a `task_id` and `role` (driver/security/it/navigator) so the Navigator can correlate all messages for a single task.

---

## How This Maps to What We've Already Built

| Existing Piece | Role in This Architecture |
|----------------|--------------------------|
| Computer₀ adaptive loop (Framework S9, done) | DISPATCH phase sends tasks to Computer₁ (project Navigators) |
| `bpsai-pair engage` (CLI S39, done) | Launches Claude Code sessions — the mechanism Computer₁ uses to dispatch Drivers |
| `bpsai-coordination` channel (CLI S43, designed) | The nervous system at every level — Computer₀↔Computer₁, Computer₁↔Drivers |
| Signal Store + blocker alerts | Andon Cord — any agent at any level can pull the cord, Computer₀ triages |
| Remote Control `--spawn` (Framework #5) | Preferred dispatch mechanism — native streaming, mobile visibility |

**The recursive model means dispatch logic is the same at every level.** Computer₀ dispatches Computer₁ the same way Computer₁ dispatches Drivers. The coordination channel carries messages at every level. The only difference is scope: Computer₁ orchestrates within a project, Computer₀ orchestrates across projects.

---

## Implementation Sequence

| Step | What | Depends On |
|------|------|------------|
| 1 | Build `bpsai-coordination` MCP server (Phase 1 of channel design) | bpsai-a2a minimal endpoint |
| 2 | Add `task-dispatch`, `task-status`, `review-feedback` message types | Step 1 |
| 3 | Add `task_id` correlation and `role` metadata to message schema | Step 1 |
| 4 | Computer₁ dispatch skill — codifies the Navigator's dispatch→review→fix loop within a project | Step 2-3 |
| 5 | Test: Computer₁ (Navigator) in paircoder dispatches Driver, round-trip review | Steps 1-4 |
| 6 | Add Security and IT agent session templates (CLAUDE.md / agent frontmatter) | Step 5 proven |
| 7 | Computer₀ dispatch — same mechanism, but dispatches Computer₁ instances across projects | Step 5 + bpsai-computer repo |

Steps 1-3 are the `bpsai-coordination` Phase 1 + Phase 1.5 from the channel design doc. Steps 4-5 prove the pattern within a single project (Computer₁). Step 7 scales it across projects (Computer₀). The dispatch mechanism is the same at both levels — the recursive model means we build it once.

---

## What This Doesn't Cover (Deliberately)

- **Computer₀ internals** — how the adaptive loop decides *what* to dispatch. That's the Sense→Plan→Dispatch→Enforce→Learn design, already approved.
- **Cross-project coordination** — Computer₀ telling Computer₁ instances about contract changes. Already covered in `bpsai-coordination` channel design.
- **Agent Lounge** — long-lived specialist agents that hang out, learn from each other, get dispatched when work arrives, come back, and share what they learned. This is the graduation path: agents that start as short-lived review sessions evolve into persistent participants with accumulated knowledge. Portfolio item 38, v3.0.0.
- **The graduation trigger** — what causes a Computer₁ to recognize it needs to become Computer₀. Today this is human-initiated ("create a new repo for this concern"). The telemetry-based gap discovery mechanism (#54, QS-4b) is what makes this autonomous — the system recognizes that project complexity has crossed a threshold and proposes the split.
- **Permission relay** — Claude Code channels support forwarding tool approval prompts remotely. Useful for autonomous operation but orthogonal to this design.

---

## Summary for Quick Reference

**Model:** Navigator launches separate Claude Code sessions (not subagents) for Driver, Security, IT. They communicate via the `bpsai-coordination` channel.

**Key properties:**
- Driver keeps its session alive during review (preserves context for fixes)
- Security/IT launch after Driver completes (no idle sessions)
- Mid-task questions are supported but not required for v1
- All messages carry task_id + role for correlation
- Navigator is the routing hub — no direct agent-to-agent messaging needed

**Builds on:** coordination channel design, adaptive loop, ORCHESTRATION.md dispatch model. No new infrastructure beyond what's already planned.
