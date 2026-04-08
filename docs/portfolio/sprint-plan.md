# Sprint Plan — Global Execution

> **DEPRECATED (2026-04-08):** This file is superseded by [execution-priorities.md](execution-priorities.md), which is the current source of truth for execution planning. This file is retained for historical reference only.

> **Principle:** One sprint, multiple repos, one plan. Computer orchestrates.

---

## Sprint G1 — Queryable Intelligence + Hardening (COMPLETE)

> 17 tasks, ~395cx across CLI + API + FW.

---

## Sprint G2 — Self-Reasoning + Autonomous Communication (COMPLETE)

> 12 items, ~465cx across CLI + FW + Bot.

---

## Sprint G3 — Close Every Loop (COMPLETE)

> **Theme:** Metis self-sustaining, channels live, Computer dispatches. The system runs itself.
> **Shipped:** ~750cx across 8 repos.

### What Shipped

| Item | Cx |
|------|----|
| Bot-S34: Metis closes the loop (persistence, standup, dedup, doc integrity) | 80 |
| Bot-S35: Metis evidence engine (mapper, lifecycle, review bridge, stale re-eval) | 95 |
| Lounge S1+S2: Agent directory + standup dashboard | 120 |
| CLI engage fixes: 11 bugs found and fixed | 35 |
| G3.P0-P6: Full Computer Plan+Dispatch pipeline | 200 |
| G3.X1-X2: Hook filters + headless AskUserQuestion | 30 |
| A2A-S2: Production deployment + channel message endpoints | 40 |
| G3.C1-C3: Channel wiring — Bot connected to a2a.paircoder.ai | 30 |
| A2A agent cards: 15 agents discoverable at well-known paths | — |
| PairCoder registered on a2aregistry.org | — |
| Issue #3 Layer 2: Workspace permissions.deny | — |
| Evidence quality: meta-detector, threshold tuning, project grouping | — |
| Metis heartbeat: systemd wired to MetisHeartbeat (replaces Moltbook) | — |
| HYP-008 corrected: evidence reset, support grouped, sources clarified | — |
| Design doc: Agent intelligence scoring (3-layer architecture, belief provenance, marketplace convergence) | — |

### Remaining from G3

| Item | Cx | Status |
|------|----|--------|
| Observability: Instrument blind spots | 60 | PENDING — HYP-008 refined, clear scope now |
| Metis A2A transport | 20 | PENDING — WorkspaceReader queries A2A for multi-user |
| CI health across all repos (#21) | — | PENDING — every repo has CI issues |
| Agent registration on both registries | — | IN PROGRESS — PairCoder done, 14 remaining |

---

## Active Work

### Lounge-S3: A2A Card Integration + PairCoder Profile (40cx) — IN PROGRESS

Navigator dispatched. PairCoder profile, A2A card viewer on agent pages, registration badges, JSON download.

---

## G4 Planning Inputs

| Item | Source |
|------|--------|
| Agent mythology renaming (.claude/agents/*.md) | Deferred from G3 |
| Lounge as A2A registry | Design discussion — no official Linux Foundation registry exists yet |
| Agent intelligence scoring implementation | Design doc at docs/design/agent-intelligence-scoring-design.md |
| Agent foundry base package (pip install bpsai-lounge) | Design doc — 10 open questions for Mike |
| Belief provenance (hash-chained observation logs) | Design doc — patent candidate |
| Metis centralization (service deployment) | After A2A transport mode |
| CI health sprint | Issue #21 |

---

## Deferred (Tier 4 — Features)

| Title | Cx | Repo |
|-------|----|------|
| QC Phase 2 (6 tasks) | 140 | CLI |
| Voice Engine Extraction | 180 | FW |
| Workspace Command Center | 210 | FW/CLI |
| bpsai-pair route | 50 | CLI |
| bpsai-pair doctor | 60 | CLI |
| --json output | 80 | CLI |
| TaskCompleted hook bridge | 100 | CLI |

---

## How This Works

1. David/Mike + Computer plan the sprint — review this doc, approve scope
2. Computer delivers backlogs to each repo's `.paircoder/context/sprint-backlog.md`
3. Computer dispatches Navigators via `bpsai-pair engage` — parallel headless execution
4. Navigators dispatch Drivers — TDD, implementation, tests
5. Review automation dispatches reviewer + security agents post-completion
6. Status.yaml auto-updated from outcomes
7. Next sprint drafted from Metis standup + carry-over items
