# Portfolio Reconciliation — 2026-03-25

> Cross-repo strategic content extraction and merge into framework.
> Every item gets a disposition. Nothing deleted until confirmed.

### Disposition Summary (2026-03-25)

| Disposition | Count | Items |
|-------------|-------|-------|
| ABSORBED | 20 | #1-8, #10-20, #22-23 |
| SHIPPED | 1 | #9 (SyncProviderAdapter, FW-S5) |
| PARTIALLY SHIPPED | 1 | #2 (PreToolUse shipped, compaction/timeout open) |
| TRACKED | 8 | #24-31 (deferred work in status.yaml) |
| **Total** | **31** | |

**Files modified:**
- `docs/portfolio/strategy.md` — pricing, competitive, API vision, exemptions, incidents, cost/quality, open questions, milestones
- `docs/portfolio/status.yaml` — `deferred_work` section (8 items)
- `docs/portfolio/decisions/D-014.yaml` through `D-019.yaml` — 6 new decisions
- `docs/portfolio/decisions/README.md` — index updated
- `docs/portfolio/reconciliation-2026-03-25.md` — this file (dispositions added)

## Items Requiring Decision (UNIQUE — not in framework)

### A. Architecture & Design (absorb into framework)

| # | Item | Source | Recommendation |
|---|------|--------|----------------|
| 1 | **Gate hooks intentionally in OBSERVATION mode** — not a bug. Hardcoded thresholds premature because file role (test vs service) matters. Data collection → dynamic thresholds is the path. | CLI anthropic-autonomy-self-review.md | **ABSORBED** — D-015, strategy.md enforcement taxonomy note. A6 NOT yet shipped (CLI-S43). |
| 2 | **Dual-mode containment gaps** — Advisory mode loses awareness during compaction, no session timeout, state in-memory only. Three fixes: save config to snapshot, PreToolUse hook, optional timeout. | CLI anthropic-autonomy-self-review.md | **PARTIALLY SHIPPED** — PreToolUse hook shipped (CLI-S40 T40.4). Compaction snapshot: evaluate CC 2.1.83 improvements (noted in strategy.md). Session timeout: still open. |
| 3 | **PM Architecture: A2A over embedding** — 5 principles: (1) A2A over embedding, (2) separate ABCs + shared protocol, (3) async at framework/sync at boundary, (4) trigger + discover, (5) presets are data not code | CLI backlog.md | **ABSORBED** — D-014 created |
| 4 | **Query patterns are the API contract** — storage swappable beneath intent patterns. Method chaining vs dict filters still unresolved. | CLI queryable-state-design.md | **ABSORBED** — strategy.md "Open Design Questions" section |
| 5 | **Content safety two-tier model** — Tier 1 (internal, all sources) vs Tier 2 (A2A public, filtered). Field-level granularity. Security title keyword filter. | API content_safety.md | **ABSORBED** — D-016 created |
| 6 | **Engagement-first cognitive loop** — baseline behavior runs every cycle, LLM only decides post/reflect/idle. Proves enforcement pipeline ordering matters. | Bot S32 state.md | **ABSORBED** — D-017 created |
| 7 | **A2A service topology finalized** — framework (pip schemas) → bpsai-a2a (transport) → consumers (CLI, API, bot) | A2A project.md | **ABSORBED** — D-018 created (includes auth boundary from #8) |
| 8 | **A2A auth boundary** — LicenseClient HTTP validation, no shared DB. 1 retry on 5xx, 3s timeout. | A2A state.md | **ABSORBED** — folded into D-018 (A2A service topology) |
| 9 | **Async/sync impedance is real** — bot deferred `build_voice_pipeline()` because framework is async, bot is sync. Needs SyncProviderAdapter. | Bot S32 deferred | **SHIPPED** — SyncProviderAdapter exists in framework since FW-S5 (`orchestration/sync_adapter.py`). Bot needs to adopt it. Tracked as deferred item `bot-promptbuilder-adoption` in status.yaml. |

### B. Business & Competitive (absorb into strategy.md or decisions/)

| # | Item | Source | Recommendation |
|---|------|--------|----------------|
| 10 | **Pricing: Solo $29, Pro $79, Enterprise $199/seat** | CLI roadmap.md | **ABSORBED** — strategy.md "Pricing Tiers" section |
| 11 | **API rate limits: Solo 100/day, Pro 5,000/day, Enterprise unlimited** | API roadmap.md | **ABSORBED** — strategy.md "Pricing Tiers" table (consolidated with #10) |
| 12 | **Claude.md freshness as competitive angle** — PairCoder generates 284-line CLAUDE.md; gap is auto-refresh. "Claude.md as Service" positioning. | CLI anthropic-autonomy-self-review.md | **ABSORBED** — strategy.md "Competitive Positioning" section |
| 13 | **5 marketing one-liners with evidence** from autonomy audit | CLI anthropic-autonomy-self-review.md | **ABSORBED** — strategy.md "Competitive Positioning" section (marketing evidence list) |
| 14 | **API dogfood exit criteria all passed** — 8/8 criteria met, production-ready | API state.md | **ABSORBED** — strategy.md "Milestones" section |
| 15 | **Long-term API vision: 3 modes** — skill server (current), content ingestion (future), direct subagent execution (future) | API roadmap.md | **ABSORBED** — strategy.md "API Vision: Three Modes" section |
| 16 | **Bot content model: Claude Sonnet ($7/mo) over Qwen 14B** — better first-attempt quality, fewer enforcement retries | Bot state.md | **ABSORBED** — strategy.md "Cost/Quality Tradeoffs" section |

### C. Incidents & Lessons (absorb into decisions/ or signals)

| # | Item | Source | Recommendation |
|---|------|--------|----------------|
| 17 | **Key Vault firewall outage (Mar 9-17)** — 80 Container App IPs not whitelisted, 8.5 days broken checkout, zero alerts. Post-incident: deep health checks + Azure Monitor alerts. | API state.md | **ABSORBED** — strategy.md "Incidents & Lessons" section |
| 18 | **Bot production deployment failures** — framework import failed (no PYTHONPATH), service names wrong in docs, .pth file needed. | Bot S32 | **ABSORBED** — strategy.md "Incidents & Lessons" section |
| 19 | **Navigator provided stale service names** — no reconciliation step between docs and actual systemd units | Bot S32 | **ABSORBED** — strategy.md "Incidents & Lessons" section (folded into #18) |

### D. Process & Conventions (absorb or confirm duplicate)

| # | Item | Source | Recommendation |
|---|------|--------|----------------|
| 20 | **Architecture exemptions** — API clients, state machines, MCP register functions exempt from 400-line limit. cli.py exempt from 20-import limit (39 imports unavoidable). | CLI decomp-status.md | **ABSORBED** — strategy.md "Architecture Exemptions" section |
| 21 | **Effort values: only S/M/L (0-30/31-60/61-100)** — no XS or XL | CLI bps-board-conventions.md | **ABSORBED** — D-019 created |
| 22 | **Release process: template drift detection via CI** — `bpsai-pair template check --fail-on-drift` | CLI RELEASING.md | **ABSORBED** — strategy.md "Incidents & Lessons" > "Process Gaps Identified" (noted as CLI-specific) |
| 23 | **CC CHANGELOG monitoring: daily 9 UTC cron** — automated platform change detection | CLI backlog.md | **ABSORBED** — strategy.md "Incidents & Lessons" > "Process Gaps Identified" (noted as CLI automation) |

### E. Deferred Work (track in status.yaml or backlogs)

| # | Item | Source | Recommendation |
|---|------|--------|----------------|
| 24 | **A2A Phase 4 hardening** — tenant isolation, all 7 skills wired, container hardening, auth logging | A2A state.md | **TRACKED** — status.yaml `deferred_work` section |
| 25 | **Content safety Phase 2** — session log ingestion for distillation | API deferred | **TRACKED** — status.yaml `deferred_work` section |
| 26 | **Bot PromptBuilder adoption** — async/sync impedance | Bot S33 deferred | **TRACKED** — status.yaml `deferred_work` section (note: SyncProviderAdapter exists since FW-S5) |
| 27 | **Bot structural enforcement** — `limited_structures` not consumed | Bot S33 deferred | **TRACKED** — status.yaml `deferred_work` section |
| 28 | **Bot reception-informed engagement** — use reception data for targeting | Bot S33 deferred | **TRACKED** — status.yaml `deferred_work` section |
| 29 | **bpsai-pair doctor command** — holistic health check | CLI backlog.md | **TRACKED** — status.yaml `deferred_work` section |
| 30 | **--json output on all commands** — enable scripting | CLI backlog.md | **TRACKED** — status.yaml `deferred_work` section |
| 31 | **TaskCompleted hook bridge** — high UX impact, needs design (~100cx) | CLI backlog.md | **TRACKED** — status.yaml `deferred_work` section |

## Items Confirmed DUPLICATE (framework already has)

These exist in both the sibling repo and the framework. Safe to remove from sibling after migration.

- "The model codes, Python enforces" (framework core principle)
- Enforcement taxonomy (A1-A8, QS-1 through QS-4)
- Task naming convention (T{sprint}.{seq})
- Plan types (feature/bugfix/refactor/chore, not maintenance)
- State.md non-negotiable update rule
- Trello completion workflow
- Definition of Done (6 criteria)
- File size/function limits (400/50/15)
- Sprint backlogs authored centrally
- Estimation bias (5% of estimated effort)
- Worktree isolation systemic problem
- A2A server migration decision
- Provider pattern convergence
- Signal → route → dispatch → compose
- All "What NOT to Lose" items 1-47

## Items to DROP (superseded or obsolete)

| Item | Source | Reason |
|------|--------|--------|
| CLI roadmap.md version refs (v2.15.11, v2.16.1 as "current") | CLI | Superseded by status.yaml |
| CLI project.md feature matrix (stops at v2.15.11) | CLI | Will be replaced by thin execution context |
| API roadmap.md (stops at S42, missing S43) | API | Superseded by status.yaml |
| Bot README test counts (1,722) | Bot | Update to 2,311 then maintain via release skill |
| API README test counts (900) | API | Update to 1,075 then maintain via release skill |
| Open design questions (human intervention signal) | CLI backlog.md | Resolved — subsumed by A6 |
| Open design question (SQLite vs TelemetryStore) | CLI queryable-state-design.md | Resolved — SQLite shipped in S40 |

## Migration Plan

1. **Absorb unique items** (#1-23) into framework docs
2. **Update status.yaml** with deferred items (#24-31)
3. **Slim sibling repo context/** to execution-only:
   - Keep: state.md, project.md (thin), workflow.md
   - Remove: roadmap.md, strategic docs, architecture docs
   - Replace removed docs with stub pointers to framework
4. **Update sibling READMEs** with correct metrics
5. **Commit everything atomically per repo**
