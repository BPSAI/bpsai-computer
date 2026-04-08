# Execution Priorities — Post-Unified-Auth Assessment

> **Updated:** 2026-04-08 (Phase B complete, agent-core v0.3.0, extractions done, CLI v2.21.5)
> **Authors:** Mike Doggett + David Wiens + Computer
> **Purpose:** Priority-ranked execution plan for next sprint planning
> **Principle:** Ship the intelligence layer first. Every sprint that improves planning, retrieval, and self-awareness makes every subsequent sprint faster. Features ship faster through a smarter system than through a dumber one shipping features.
> **Architecture shift:** G3 (Framework Computer Dispatch, 150cx) is **cancelled**. Orchestration behavior builds directly in bpsai-computer. Framework becomes a clean shared library. See computer-daemon-plan.md, computer-prime-recursive-dispatch.md, recursive-enforcement-architecture.md.
> **Agent licensing:** Shared group license with required `agent_id` on all API calls. Per-agent telemetry via agent_id segmentation. Migration to individual licenses is config-only (no architecture change) if needed later.

---

## What's Shipped (G1 + G2 + G3 + TH + Briefing)

The compounding intelligence stack is fully built. All three tiers complete. Telemetry integrity and cross-session intelligence are now live.

### Tier 1: Queryable + Self-Aware -- COMPLETE
- Skill Discovery MVP (SD.1-SD.8): IntelligentSkillRecommender, gate integration, `skill recommend`
- QS-3a/3b: A2A query handlers (project_context, agent_state)
- Context freshness auto-refresh (G2.9)
- Portfolio status.yaml, execution-priorities.md
- Auto-upgrade on version change

### Tier 2: Self-Reasoning -- COMPLETE
- Metis Phase 1 (Bot-S33): autonomous hypothesis generation, pattern detection, adversarial review
- Dynamic thresholds A6 (G2.1): 7-role taxonomy, telemetry-driven enforcement
- Fail-closed gate A7 (G2.2): unknown hooks fail-closed with timeout + signal emission
- SD Phase 4 (G2.6): IntelligenceConfig, task hooks, license gate, pipeline confidence
- CNS monitoring signals: signal hooks wired across all 5 repos (G2.D3)

### Tier 3: Autonomous Action -- COMPLETE
- Coordination channels plugin (G2.3): MCP push between sessions
- RemoteQueryClient QS-3c (G2.4): cross-project state queries
- Computer Sense + Learn (G2.7): 9 PhaseHook implementations (5 SENSE, 4 LEARN)
- Metis Phase 2 (G2.8): coordination channels push, real-time observation
- contained-auto --channels (G2.5): channels + enforcement together
- Computer Plan + Dispatch (G3): dispatch abstraction, sprint planner, navigator orchestrator

### Telemetry + Hypothesis Integrity -- COMPLETE
- Evidence dedup, confidence ceiling, tooling registry
- Intent-to-telemetry mapping, signal source tracking
- Sense + Learn hook observability (SenseEvent, LearnEvent)
- 14 hypotheses audited, confidence ceiling enforced

### Cross-Session Intelligence -- COMPLETE
- Metis session briefing: generator, channel push, persistence
- Briefing wired into heartbeat cycle
- BriefingReader SENSE hook (MB1.5): Computer reads Metis briefings
- Lounge briefing panel (MB1.4): briefings visible in Agent Lounge
- Heimdall platform sentinel: upgrade monitoring + Lounge presence
- Metis heartbeat restarted (confidence ceiling shipped)

---

## What's Next — Framework→Computer Migration + Feature Build-Out

### Strategic Context

The framework has served as the proving ground for orchestration machinery (SENSE/LEARN/dispatch/enforcement). That machinery is proven. The next phase is **migration**: Computer becomes the orchestrator, Framework becomes a clean shared library. G3 (150cx of new dispatch in framework) is cancelled — that effort goes directly into bpsai-computer.

**Target state:** David and Mike working from bpsai-computer in IDEs, dispatching and monitoring from Command Center.

---

### Phase A: Wire the Pipes

| Item | Repo | Effort | Status | Notes |
|------|------|--------|--------|-------|
| Org setup | bpsai-support | ~5cx | COMPLETE | BPS org created, Mike/David/Kevin added |
| CD3: Daemon JWT | bpsai-computer | ~15cx | In Progress — PR open | Daemon authenticates with operator-token |
| Metis fleet visibility | bpsai-computer + A2A + bot | ~50cx | In Progress — PR open | Daemon signal push, /signals endpoint, Metis reader |
| CC dispatch UI | bpsai-command-center | ~20cx | Ready | Trigger dispatches from Command Center UI |

**Milestone:** CC → daemon → execute → result loop working. First taste of working from Command Center.

### Phase B: Clean the Foundation

**Phase B: COMPLETE ✅ — Framework is clean shared library (1,146 tests)**

> A2A prototype removed from framework (2026-04-08).

| Item | Repo | Effort | Status | Notes |
|------|------|--------|--------|-------|
| AF2: Agent Foundry Phase 2 | bpsai-agents | ~100cx | COMPLETE | agent-core v0.3.0 shipped: multi-plan, Vaivora agent, clustering, synthesis |
| Twin extraction | FW → bpsai-twins | ~60-80cx | COMPLETE | bpsai-twins extracted (65 tests) |
| Hook extraction | FW → bot + computer | ~40-60cx | COMPLETE | SENSE/LEARN hooks extracted to owning agents |
| Portfolio docs migration | FW → bpsai-computer | ~30cx | COMPLETE | status.yaml, decisions, hypotheses, execution-priorities migrated |
| Dead code cleanup | FW | ~10cx | COMPLETE | dispatch_types.py, enforcement_config.py, content_router.py removed |

**Milestone:** Framework is a clean shared library — data stores, orchestration primitives, enforcement implementations. No behavior, no portfolio state, no agent-specific hooks.

### Phase C: Build Orchestration in Computer (replaces G3)

| Item | Repo | Effort | Status | Notes |
|------|------|--------|--------|-------|
| Navigator orchestration | bpsai-computer | ~50cx | Design exists (computer-daemon-plan.md Phase 3) | plan_and_propose, dispatch, monitor, review — built in Computer, importing framework abstractions |
| Backlog parsing + sprint authoring | bpsai-computer | ~40cx | Design exists | Backlog parser, sprint planner, deliverer |
| Dispatch routing + operator assignment | bpsai-computer | ~30cx | Design exists (computer-prime-recursive-dispatch.md) | Domain Computer routing, operator lane isolation |
| Status updater + review automation | bpsai-computer | ~30cx | Design exists | Portfolio state management from Computer |

**Milestone:** David and Mike working from bpsai-computer IDEs, dispatching and monitoring from Command Center. Computer owns the orchestration loop.

### Parallel Tracks (Kevin + David)

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Iris Phase 3b: produce 4 videos | Kevin | Next | Pipeline complete (S11-S13). README update first. |
| Iris S13 review fixes | Kevin | 13 findings posted | PR #20, 7 P1 + 6 P2 |
| Amunet: Lounge codebase panel | Kevin | Backlog ready (LG-CP, 58cx) | Consume Amunet output in Lounge 3D |
| CLI v2.21.5 released | David | Complete | Review command, targeted tests, engage fixes |
| CLI-EB: enforcement bootstrap | David | Backlog ready (115cx) | Dep split + branch enforcement |
| CLI-IMS: intent merge strategy | David | Backlog ready (50cx) | Squash vs merge based on intent |
| Metis dedup fix | David | Shipped | Cycle loop fixed, git identity, no exclusions |
| Agent mythology renaming | David | Deferred | Cross-repo rename, needs Mike alignment |

### Tier 4: Features + Infrastructure (post-migration)

| Item | Repo | Effort | Status | Notes |
|------|------|--------|--------|-------|
| QC Phase 2 browser testing | CLI | ~135cx | Backlogged | Element discovery, execution runtime, persistence |
| Divona QC suites | CC | ~10cx | Ready | Browser-based CC auth flow tests |
| A2A Phase 4 hardening | A2A | ~60cx | Shipped (A2A-H) | JWT auth, tenant isolation, container hardening |
| `bpsai-pair route` | CLI | ~50cx | None | Model routing observability |
| `bpsai-pair doctor` | CLI | ~60cx | None | Holistic health check |
| `--json` output | CLI | ~80cx | None | Machine consumption |
| TaskCompleted hook bridge | CLI | ~100cx | Design needed | High UX impact |
| Bot PromptBuilder adoption | Bot | ~20cx | SyncProviderAdapter exists | Framework voice consumption |
| Observability sprint | support/website | ~40cx | Metis HYP-008 flagged | Zero observability on customer-facing systems |
| Lifecycle Tier 2/3 | FW | ~30cx | Needs design | SQL event table for idea/doc audit trail |

---

## Recommended Sprint Sequence

```
PHASE A — Wire the Pipes:
├── Org setup (BPS org in Function App DB)
├── CD3: Daemon JWT (auth for daemon <-> A2A)
├── Metis fleet visibility (50cx) — daemon signal push to A2A
├── CC dispatch UI — trigger dispatches from Command Center
│   MILESTONE: CC → daemon → execute → result loop working
│
PHASE B — Clean the Foundation: COMPLETE ✅
├── AF2: Agent Foundry Phase 2 — agent-core v0.3.0 shipped ✅
├── Twin extraction — bpsai-twins (65 tests) ✅
├── Hook extraction — SENSE/LEARN to owning agents ✅
├── Portfolio docs migration — all docs in bpsai-computer ✅
├── Dead code cleanup — removed from framework ✅
│   MILESTONE: Framework is a clean shared library (1,146 tests)
│
PHASE C — Build Orchestration in Computer (replaces G3):
├── Navigator orchestration (~50cx) — plan, dispatch, monitor, review
├── Backlog parsing + sprint authoring (~40cx)
├── Dispatch routing + operator assignment (~30cx)
├── Status updater + review automation (~30cx)
│   MILESTONE: Working from bpsai-computer IDEs + Command Center
│
AFTER:
├── Feature sprint (CLI QC Phase 2 + platform, ~190cx)
├── Observability sprint (support/website instrumentation)
└── Bridge Phase 0: Web Command Center → Unity tablet (per command-center-vision.md)
```

### Cancelled / Superseded

| Item | Reason |
|------|--------|
| **G3: Framework Computer Dispatch (150cx)** | **Superseded.** Orchestration behavior builds directly in bpsai-computer (Phase C). Framework abstractions already exist. Building in framework then extracting is wasted motion. |
| **Workspace Command Center (210cx)** | **Absorbed** by Command Center project (bpsai-command-center). Already live at command.paircoder.ai. |
| **Voice Engine Extraction (180cx)** | **Replaced** by Twin extraction (60-80cx) + agent-core packaging. Leaner scope. |
| **A2A consumer cutover** | **Completed.** A2A deployed, JWT auth live, Key Vault integrated. |
| **CI health sprint (#21)** | **Completed.** All repos green as of 2026-04-07. |
| **Ultraplan enforcement (#28)** | **Completed.** Bootstrap script + SessionStart hook shipped in v2.21.1-v2.21.3. Remaining gaps in CLI-EB backlog. |
| **Individual agent licensing** | **Deferred.** Shared group license with agent_id. Migration to individual is config-only if needed. |

---

## Patent Timeline

All 4 candidates now have production code:

| Candidate | Evidence | Status |
|-----------|----------|--------|
| 1. Enforcement Pipeline | 1,608 FW + 11,412 CLI tests | **Production** — ready |
| 2. Agent Lounge / Epistemic Exchange | Signal Store, Decision Journal, Computer loop, Sense+Learn hooks, session briefings | **Production** — ready |
| 3. Skill Discovery | Full intelligence pipeline: signals -> mappers -> recommender -> gate integration | **Production** — ready |
| 4. Agent Lounge as Platform | Metis cognitive loop, coordination channels, briefings, 3,056 bot tests | **Production** — ready |

**All 4 candidates ready for attorney meeting.** No remaining blockers.

---

## Effort Summary

| Tier | Status | Remaining |
|------|--------|-----------|
| **Tier 1** (Queryable) | Complete | -- |
| **Tier 2** (Self-Reasoning) | Complete | -- |
| **Tier 3** (Autonomous Action) | Complete | -- |
| **TH** (Telemetry Integrity) | Complete | -- |
| **Briefing** (Cross-Session) | Complete | -- |
| **Unified Auth** | Complete | -- |
| **Phase A** (Wire the Pipes) | In Progress | ~90cx |
| **Phase B** (Clean Foundation) | Complete | -- |
| **Phase C** (Computer Orchestration) | After B | ~150cx |
| **Tier 4** (Features) | Backlogged | ~700cx+ |

## Test Portfolio (2026-04-08)

| Repo | Tests | Notes |
|------|-------|-------|
| CLI | 12,500+ | v2.21.5: review command, targeted tests, engage fixes |
| Framework | 1,146 | Clean shared library (post-extraction) |
| Bot | 2,961 | Metis Phase 1+2 + briefings + dedup fix |
| A2A | 200+ | JWT auth + Key Vault + org scoping |
| Command Center | 200+ | Zoho OAuth + session catalog + UAT |
| Computer | 144 | CD2 + security fixes |
| Agents | 133 | agent-core v0.3.0 |
| Twins | 65 | Extracted from framework |
| Vaivora | 49 | Extracted, synthesis + clustering |
| Iris | 3,600+ | S13 Phase 3 (instructional pipeline) |
| Amunet | 704 | S4 workspace validation |
| Lounge | 318 | Agent directory + briefing panel |
| Support | 1,651 | Portal JWT + license linking + functions |
| **Total** | **~23,800+** | |
