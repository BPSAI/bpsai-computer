# Portfolio Index — What to Read When

> **For sprint planning:** Read status.yaml + execution-priorities.md. That's it.
> **For "why did we decide X?":** Search decisions/
> **For deep design context:** Use the reference table below.

---

## Quick Access (Daily Use)

| Question | Read This |
|----------|-----------|
| What's the status of all projects? | `status.yaml` |
| What should we work on next? | `execution-priorities.md` |
| What have we decided? | `decisions/README.md` (20 decisions indexed) |
| What are we investigating? | `hypotheses/*.yaml` (5 hypotheses) |
| What's the strategic vision? | `strategy.md` |
| What got migrated from sibling repos? | `reconciliation-2026-03-25.md` |
| How does the idea log fit with Metis + portfolio? | `idea-log-discovery-2026-03-26.md` |

---

## Deep Reference (When You Need the Why)

| Topic | File | When to Read |
|-------|------|-------------|
| **Six-layer architecture, product levels, agent types** | `docs/bps-agent-framework-design.md` | When designing a new agent or explaining the platform |
| **Cross-project orchestration protocol** | `docs/ORCHESTRATION.md` | When dispatching work across repos or reviewing branch model |
| **Computer adaptive loop (tick-based CNS)** | `docs/computer-adaptive-loop-proposal.md` | When working on FW-S11+ (Sense/Learn/Plan/Dispatch) |
| **Agent Lounge epistemic exchange** | `docs/agent-lounge-epistemic-exchange.md` | When working on Metis, belief propagation, or Lounge protocol |
| **Belief propagation landscape** | `docs/belief-propagation-landscape-analysis.md` | When comparing our approach to academic prior art |
| **Agent mythology naming** | `docs/agent-mythology-naming.md` | When naming a new agent or updating branding |
| **Coordination channels (MCP push)** | `docs/bpsai-coordination-channel-design.md` | When working on CLI-S43 channels plugin |
| **Agent coordination architecture** | `docs/agent-coordination-architecture.md` | When working on Computer dispatch model |
| **Enterprise security contract** | `docs/enterprise-data-tier-security-contract.md` | When working on QS-3 enterprise path or A2A auth |
| **Workspace Command Center** | `paircoder/docs/features/workspace-command-center.md` (CLI repo) | When working on FW-S12+ monitoring dashboard. Sense layer shipped (FW-S8/S9); Phases 1-2 remain (~210cx). See status.yaml deferred_work. |
| **Idea log discovery + alignment** | `docs/portfolio/idea-log-discovery-2026-03-26.md` | When working on IdeaStore, Metis integration, or Lounge architecture |
| **Licensing architecture (tiers)** | `docs/licensing-architecture.md` | When working on tier gating or pricing |
| **Patent candidates** | `docs/patent-briefing.md` | When preparing for attorney meeting |
| **Content strategy** | `docs/content-plan.md` | When drafting blog/LinkedIn/Reddit content |
| **Bot voice alignment audit** | `docs/bot-voice-alignment.md` | When Metis consumes framework voice profile |
| **Project brief (executive summary)** | `docs/project-brief.md` | When explaining BPS to someone new |
| **Full portfolio plan (historical)** | `docs/bps-portfolio-plan.md` | When you need the 47 "What NOT to Lose" items or full revision history |
| **Deployment patterns** | `docs/portfolio/infra/deployment-patterns.md` | When deploying a new service or auditing infrastructure |
| **A2A deployment handoff** | `docs/portfolio/infra/a2a-deployment-handoff.md` | When working on A2A-S2 production deployment |

---

## Open GitHub Issues (as of 2026-03-26)

### Framework (10 open)

| # | Title | Covered By | Action |
|---|-------|-----------|--------|
| 18 | Platform Impact CC 2.1.79-2.1.83 | execution-priorities.md Tier 3 (CLI-S43) | **Keep** — active reference for platform adaptation |
| 13-16 | Agent Lounge (4 design issues) | Not yet triaged into sprints | **Keep** — Lounge design parking lot for focused session with Mike |
| 10 | QS-2 → QS-3 data path gap | execution-priorities.md Tier 1 (CLI-S42 T42.10/T42.11) | **Close** — fully covered |
| 9 | CC v2.1.80 channels assessment | Superseded by #18 | **Close** — consolidated |
| 5 | Remote Control + Orchestration | execution-priorities.md Tier 3, D-009 | **Close** — decisions made, work scheduled |
| 3 | Workspace permission model | CLI-S42 T42.13 | **Close** — scoped into sprint |
| 1 | A2A server migration | status.yaml blocker + deferred work | **Close** — tracked, cutover pending |

### CLI (2 open)

| # | Title | Covered By | Action |
|---|-------|-----------|--------|
| 103 | contained-auto + channels | execution-priorities.md Tier 3 (CLI-S43, ~15cx) | **Keep** — user-facing feature request |
| 91 | bpsai-pair route | execution-priorities.md Tier 4 | **Close** — tracked in deferred work |
