# BPS AI Portfolio Strategy

> **Purpose:** Strategic context that survives across sprints. Read during major planning sessions.
> **NOT an execution tracker.** For current status, see `status.yaml`. For hypotheses, see `hypotheses/`. For decisions, see `decisions/`.

---

## The Big Picture

BPS AI is building an agent foundry. Three levels:

**Level 1 — Individual Agents.** Each agent is a deployment of the same six-layer architecture with different configuration. PairCoder CLI, PairCoder Bot, Digital Twins, Support Triage, Aurora, Platform Impact, IT Agent. Each is a product.

**Level 2 — A2A Marketplace.** Every agent speaks A2A (JSON-RPC 2.0). Discoverable via agent cards, metered by tier, queryable by third-party agents.

**Level 3 — Orchestration + Intelligence as Product.** The CNS pattern (planning, review, enforcement, self-improvement) combined with the Agent Lounge (epistemic exchange, belief propagation) is a deployable system. Organizations purchase custom agent teams that get smarter through collective learning.

Each level compounds the others.

---

## Product Direction

- **The 80% base agent is the product.** Human polish is the feature. (D-001)
- **Corpus connectors, not upload pipelines.** Meet users at Outlook, Drive, SharePoint via connectors/MCP. (D-005)
- **Skill discovery via telemetry, not static libraries.** PairCoder observes patterns and generates skills organically. (D-012)
- **Observation-only deployment is a product.** Framework deployment that ingests existing workflow, collects signal, produces ROI report. Entry point for L3.

## Architecture Principles

- **Signal -> route -> dispatch -> compose** is the unifying pattern. (D-005)
- **All enforcement runs locally.** API role is opt-in telemetry + pull-model recommendations. No user code leaves the machine. (D-006)
- **Provider patterns converge.** DistributionProvider, ProjectManagementProvider, A2A handlers share ABCs: capabilities(), registry, async execution, structured results. (D-005)
- **Two hats are recursive, not competing.** Hat 1: Framework as CNS. Hat 2: PairCoder as product. Hat 2 serves Hat 1. (D-007)
- **Computer hierarchy is L3 recursive.** Computer1 per project, Computer0 manages Computers. Same CNS pattern, self-similar. (D-008)

## Enforcement Taxonomy

```
STATIC GATES (always-on)
  A1: Token budget (CLI-S37) ........... DONE
  A4: Containment tiers (CLI-S40) ...... DONE (PreToolUse hook shipped T40.4)
      Containment gaps: compaction snapshot — evaluate CC 2.1.83 improvements
      Session timeout — still open (advisory mode loses awareness)
  A7: Fail-closed (CLI-S43) ............ PLANNED
  Post-sprint review dispatch (CLI-S37)  DONE
  CI verification (CLI-S38) ............ DONE
  State.md update enforcement .......... DONE

DYNAMIC THRESHOLDS (telemetry-informed)
  A6: Dynamic arch thresholds (CLI-S43)  PLANNED (needs QS-3 data)
  Human intervention signal ............ Resolved (subsumed by A6)
  NOTE: Gate hooks are intentionally in OBSERVATION mode (D-015).
        Hardcoded thresholds are premature — file role matters.
        Data collection → dynamic thresholds is the design path.

CAPABILITY AWARENESS
  Intent-to-capability check (CLI-S37)   DONE
  Skill discovery MVP .................. IN PROGRESS (patent-critical)

TELEMETRY PIPELINE
  QS-1: Handoffs (CLI-S37/38) ......... DONE
  QS-2: SQLite + session recording ..... DONE (CLI-S39/40/41)
  QS-3: Cross-project A2A queries ...... IN PROGRESS (CLI-S42)
  QS-4: Push + beliefs + retrospective   PLANNED (v3.0.0)
```

## CNS Monitoring Maturity

```
v2.16.1 (QS-1): Agent self-awareness — handoffs survive compaction
v2.17.x (QS-2): Structured outcomes — session recording + SQLite
v2.18.0 (QS-3): Cross-project monitoring — CNS queries via A2A
v3.0.0  (QS-4): Push coordination + belief propagation + retrospective
```

## Pricing Tiers

| Tier | Price | Rate Limit | Key Features |
|------|-------|------------|--------------|
| Solo | $29/mo | 100 API calls/day | Local enforcement, local telemetry, static thresholds |
| Pro | $79/mo | 5,000 API calls/day | Multi-repo (Computer0), coordination channels, local telemetry-informed thresholds |
| Enterprise | $199/seat/mo | Unlimited | Fleet telemetry, Agent Lounge, belief propagation, A2A query (fleet), Lounge-informed thresholds |

Rate limits apply to API telemetry/licensing calls, not local CLI operations. Local enforcement is unlimited at all tiers.

See `docs/licensing-architecture.md` for full tier design and gating rationale.

## Competitive Positioning

**Claude.md as differentiator.** PairCoder generates a 284-line CLAUDE.md that encodes project conventions, enforcement rules, and workflow patterns. The gap is auto-refresh: keeping CLAUDE.md current as the project evolves. "Claude.md as Service" is a positioning angle — PairCoder is the tool that keeps your Claude Code instructions accurate and comprehensive without manual maintenance.

**Marketing evidence from autonomy audit (CLI):**
1. "PairCoder generated 284 lines of Claude.md instructions that encode your entire workflow"
2. "7,000+ tests enforce the same standards whether you're awake or not"
3. "Budget enforcement caught 3 over-scope attempts in Sprint 37 alone"
4. "Containment mode: your agent can read architecture docs but can't modify enforcement code"
5. "The agent that built this feature was governed by the same enforcement pipeline it ships"

## API Vision: Three Modes

The API evolves through three modes:

1. **Skill server (current)** — A2A skills exposed via JSON-RPC, metered by tier. Licensing, telemetry aggregation, fleet calibration.
2. **Content ingestion (future)** — Session logs, corpus data, and signal events flow into the API for cross-project analysis. Feeds fleet-level skill discovery and Lounge intelligence.
3. **Direct subagent execution (future)** — API hosts agent instances that execute tasks on behalf of callers. Full six-layer pipeline running server-side for enterprise deployments.

Each mode builds on the previous. Mode 2 requires QS-3 data flowing. Mode 3 requires the full enforcement pipeline to be deployable as a service.

## Architecture Exemptions

Known legitimate exceptions to standard file size / import limits:

| File | Exemption | Rationale |
|------|-----------|-----------|
| API clients (e.g., `trello_client.py`) | 400-line limit | HTTP client methods are thin wrappers; splitting creates unnecessary indirection |
| State machines (e.g., `task_state.py`) | 400-line limit | State transition tables are inherently tabular; splitting loses the overview |
| MCP register functions | 400-line limit | Tool registration is declarative; each tool adds ~20 lines of boilerplate |
| `cli.py` (Click entry point) | 20-import limit (has 39) | Click CLI requires importing every command group; unavoidable |

These exemptions are tracked by the architecture checker. When A6 dynamic thresholds ship, they will incorporate file-role awareness to handle these cases automatically. (D-015)

## Key Cross-Cutting Concerns

Full design docs live in `docs/`. Brief pointers:

- **Agent Lounge** — epistemic exchange surface. `docs/agent-lounge-epistemic-exchange.md`
- **Andon Cord** — agent-initiated swarming via Signal Store + dynamic thresholds + channels
- **IT Agent** — continuous deployment participant. `Aurora/.paircoder/context/a2a-it-agent-design-principle.md`
- **DevOps Handbook** — the three ways map directly to the agent platform
- **Hypothesis Backlog** — slow-cadence self-improvement loop. `docs/portfolio/hypotheses/`
- **Belief Propagation** — `docs/belief-propagation-landscape-analysis.md`
- **Coordination Channels** — `docs/bpsai-coordination-channel-design.md`

## Open Design Questions

### Query Patterns as API Contract (QS-3)

Storage is swappable beneath intent patterns. The query layer defines the contract; the backing store (SQLite, API aggregate, fleet) is an implementation detail. Unresolved: method chaining vs dict filters for the query DSL. Both approaches work; method chaining reads better but dict filters compose better for dynamic queries. Decision deferred until QS-3a/3b implementation reveals which pattern dominates in practice.

Source: CLI queryable-state-design.md (reconciliation item #4)

---

## Milestones

- **API dogfood exit criteria passed (2026-03-20):** All 8/8 criteria met. API is production-ready for internal consumption. Source: API state.md.

---

## What NOT to Lose

47 strategic decisions and context items. Full list preserved in `docs/bps-portfolio-plan.md` (the original document). Key items indexed in `docs/portfolio/decisions/README.md`.

The most critical ones:
1. Dynamic enforcement is a design principle, not a backlog item
2. The agent circumvention story motivated read-only enforcement paths
3. The twins force framework extraction (architectural forcing function)
4. Aurora solves David's capture bandwidth problem
5. Memory capture from human edits is proven (Sprint 4)
6. Sprint backlogs authored centrally, tasks planned locally
7. Pre-merge review is the gate, not post-merge discovery

---

## Incidents & Lessons

### Key Vault Firewall Outage (2026-03-09 to 2026-03-17)

**Impact:** 8.5 days of broken checkout flow. 80 Container App IPs were not whitelisted in the Key Vault firewall. Zero alerts fired.

**Root cause:** Azure Container Apps uses a pool of outbound IPs. The Key Vault firewall was configured with a static allowlist that didn't cover the full pool. No health check validated KV connectivity.

**Post-incident actions:**
- Deep health checks added (verify actual secret retrieval, not just endpoint reachability)
- Azure Monitor alerts configured for KV access failures
- Lesson: health checks must validate the full path, not just the edge

### Bot Deployment Failures (Bot S32)

**Impact:** First production deployment of the bot failed on multiple fronts.

**Failures:**
1. Framework import failed — no `PYTHONPATH` configured in the deployment environment. Required `.pth` file to resolve.
2. Service names in deployment docs were stale — Navigator provided names that didn't match actual systemd units.
3. No reconciliation step existed between documentation and actual deployed infrastructure.

**Post-incident actions:**
- Deployment template now includes PYTHONPATH verification step
- Added reconciliation check: docs vs actual systemd units before deployment
- CNS lesson: never trust doc-stated service names without verifying against `systemctl list-units`

### Process Gaps Identified

- **Template drift detection (CLI):** `bpsai-pair template check --fail-on-drift` added to CI. CLI-specific but the pattern (detect config/template drift via CI) applies to all repos.
- **CC changelog monitoring (CLI):** Daily 9 UTC cron job monitors Claude Code changelog for platform changes that affect PairCoder behavior. CLI automation, noted here for awareness.

---

## Cost/Quality Tradeoffs

### Bot Content Model Selection (Bot S32)

**Decision:** Claude Sonnet ($7/mo estimated) over Qwen 14B (self-hosted) for bot content generation.

**Rationale:** Better first-attempt quality means fewer enforcement retries. The enforcement pipeline catches quality issues, but each retry costs tokens and latency. Sonnet's higher base quality reduced retry rate enough to offset the API cost vs self-hosted savings. At bot-scale content volume (~50-100 posts/month), the cost difference is negligible.

**Precedent:** When enforcement retry cost exceeds model cost difference, choose the higher-quality model.
