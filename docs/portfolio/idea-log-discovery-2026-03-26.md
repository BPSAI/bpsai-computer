# Idea Log Architecture — Discovery & Alignment Session

> **Date:** 2026-03-26
> **Participants:** Mike (Claude Desktop ideation) + David (framework refactoring) + Claude (framework session synthesis)
> **Status:** Discovery complete, design direction established, implementation not yet started
> **Relates to:** Agent Lounge (issues #13-16), Metis (Bot-S33), Hypothesis Backlog (#34), QS-4b belief propagation

---

## Background

Over the past weeks, significant drift and lost ideas accumulated across the portfolio. Mike and David independently recognized the problem — ideas emerge in conversations, get partially captured in docs, and evaporate when those docs are revised or when sessions end. The formal planning artifacts (backlogs, sprint plans, task breakdowns) capture ideas that survived the filter. They do not capture the ideas that didn't make it, or the half-formed hypotheses that existed somewhere between a thought and a task.

David addressed this by restructuring `docs/portfolio/` — centralizing strategic state, creating the decision record series (D-013 through D-022), formalizing hypotheses (HYP-001 through HYP-005), and producing the reconciliation doc that rescued 31 items from sibling repos.

Mike, working in Claude Desktop, explored what a scalable idea storage architecture would look like — one that preserves ideas across their full lifecycle and scales from individual use to multi-organization collaboration.

This document captures the synthesis session where these two threads converged.

---

## The Core Insight: The Portfolio Structure IS a File-Based Idea Store

The portfolio directory maps directly to the idea log's event types:

| Idea Log Event Type | Portfolio Equivalent | File(s) |
|---------------------|---------------------|---------|
| `IdeaCapture` | Hypotheses | `hypotheses/HYP-001..005.yaml` |
| `IdeaRefined` | Decision records | `decisions/D-013..022.yaml` |
| `IdeaPromoted` | Sprint plan tasks | `sprint-plan.md` task rows |
| `IdeaAbandoned` | Reconciliation "drop" items | `reconciliation-2026-03-25.md` |
| Current state projection | status.yaml | `status.yaml` |
| Strategic context | strategy.md | `strategy.md` |
| Execution ordering | execution-priorities.md | `execution-priorities.md` |

This mapping is not a coincidence — both structures solve the same problem (preserve the full lifecycle of ideas). The difference is coverage: the portfolio handles the **right half** of the idea spectrum (hypothesis → decision → task) well, but the **left half** (raw thought → rough observation → pre-hypothesis) has no home.

Ideas exist on a spectrum:

```
raw thought → observation → hypothesis → decision → sprint task
     ^                          ^                        ^
     |                          |                        |
  no home today          portfolio/hypotheses/     sprint-plan.md
```

---

## Discovery: The Infrastructure Already Exists

The framework's engine and orchestration layers already implement the core patterns the idea log needs. This is not a greenfield build — it is a composition problem.

| Idea Log Need | Existing Component | File | Status |
|---------------|-------------------|------|--------|
| Append-only event capture | **Signal Store** | `engine/signal_types.py` | Working, JSONL-backed |
| Decision tracking with rationale | **Decision Journal** | `engine/decision_journal.py` | Working, JSONL-backed |
| Hypothesis lifecycle (observed → actionable) | **Hypothesis Backlog** | `engine/hypothesis_backlog.py` | Working, YAML persistence |
| Semantic search over prose | **Episodic Index** | `engine/episodic_index.py` | Working, pure-Python cosine similarity |
| Text chunking for indexing | **Corpus Chunker** | `engine/corpus_chunker.py` | Working |
| Document lifecycle (active → resolved → archived) | **Document Lifecycle** | `orchestration/document_lifecycle.py` | Working |
| State machine transitions | **Workflow Engine** | `orchestration/workflow_engine.py` | Working, config-driven |
| Sync protocol | **Sync Manager** | `orchestration/sync_manager.py` | Working, bidirectional with conflict detection |
| Cross-agent query protocol | **A2A Schemas** | `a2a/query_schemas.py` | Working, 5 query surfaces |
| Memory extraction from edits | **Memory Store** | `engine/memory.py` | Working |

**Implication:** The minimum viable idea log is not building new infrastructure. It is:
1. An `IdeaStore` following the Signal Store's JSONL pattern (~50 lines of new code)
2. Lifecycle transitions wired through the existing Workflow Engine
3. A capture surface (CLI command and/or MCP tool)
4. The Episodic Index pointed at portfolio docs for semantic search

---

## Metis Is the Automated Producer

Metis (Bot-S33, **COMPLETE**, 2,507 tests, awaiting deployment) is the first automated capture surface for the idea log. Its cognitive loop maps directly to idea log events:

| Metis Action | Idea Log Event | Description |
|-------------|---------------|-------------|
| `observe` | `IdeaObserved` | Reads telemetry, detects patterns across repos |
| `hypothesize` | `IdeaCapture` (agent-generated) | Proposes new hypotheses from 3+ matching signals |
| `update` | `IdeaRefined` | Updates confidence scores with new evidence |
| `heartbeat push` | Batch write to portfolio | Commits updated hypotheses + observations to framework |

Metis already writes to `docs/portfolio/`:
- Updated hypothesis YAML files (confidence, evidence_count, last_reviewed)
- `metis-observations.md` (timestamped observations — effectively a human-readable event log)
- `doc-health.yaml` (document freshness tracking)

**The idea log and Metis solve the same problem from two directions:**
- **Idea log** = the STORE (where ideas live, how they're indexed, how they scale)
- **Metis** = the PRODUCER (the agent that generates ideas from cross-project telemetry observation)

Both converge on the portfolio structure. The design question is whether Metis should write to the idea log as its primary output (with hypothesis YAML and `metis-observations.md` as derived views) or continue writing directly to files with the idea log wrapping around it later.

---

## Scalability Architecture (From Mike's Claude Desktop Session)

Mike's ideation session identified that the system needs to scale across four tiers:

```
Org
 +-- Portfolio
      +-- Project / Repo
           +-- User / Agent Session
```

Each tier is autonomous but syncs upward. The key insight: **ideas are naturally append-only**, which means the merge problem dissolves. Union the logs, deduplicate by event ID. No conflict resolution required.

### Tier Design

| Tier | Scope | Storage | Notes |
|------|-------|---------|-------|
| 0 | User / Agent session | SQLite or JSONL | Fully offline, append-only |
| 1 | Project / Repo | JSONL in git | Aggregates from Tier 0 via cursor sync |
| 2 | Portfolio | PostgreSQL or SQLite | Cross-project querying, materialized views |
| 3 | Org | PostgreSQL + optional vector store | Semantic search across prose at scale |

### The Schema That Works at Every Tier

```sql
CREATE TABLE events (
  id          TEXT PRIMARY KEY,   -- ulid, globally unique
  scope       TEXT NOT NULL,       -- 'org/portfolio/project/user'
  scope_id    TEXT NOT NULL,       -- actual identifier at that scope
  type        TEXT NOT NULL,       -- IdeaCapture, IdeaRefined, IdeaPromoted...
  parent_id   TEXT,                -- references another event.id
  tags        TEXT,                -- JSON array
  body        TEXT,                -- unstructured prose, no schema imposed
  metadata    TEXT,                -- JSON, anything structured
  created_at  TEXT NOT NULL,       -- ISO8601
  created_by  TEXT NOT NULL        -- user or agent ID
);
```

### Sync Protocol

Each tier exposes:
```
GET /events?since=<cursor>&scope=<project-id>
POST /events  (batch ingest from lower tier)
```

The cursor is a ULID or timestamp. Since events are append-only, "give me everything after X" is always safe and idempotent.

### Graduation Model

Individual users start at Tier 0-1 (local SQLite/JSONL, project-level). As they join or form organizations, their events sync upward to Tier 2-3. Organizations can merge by unioning their event logs. The append-only property makes this safe.

### Fit with Existing Infrastructure

| Concern | Existing Component | Constraint? |
|---------|-------------------|-------------|
| JSONL vs SQLite | Signal Store uses JSONL | No — interchangeable backends behind same interface |
| Separate stores vs unified | Signals, hypotheses, decisions are separate | No — unified `events` table is the Tier 2+ aggregation view |
| Append-only | Signal Store and Decision Journal are already append-only | Aligned |
| ULID + scope addressing | Not yet in schemas | Additive — new fields, not a rewrite |
| Sync protocol | Sync Manager handles bidirectional sync | Append-only is actually easier than what Sync Manager already does |
| Multi-org | A2A schemas define cross-agent boundaries | Org-level scoping is a schema extension |

**Nothing in the existing infrastructure restricts the long-term scalability vision.** The patterns are at a lower level of abstraction — they provide the primitives that the idea log composes into a higher-level system.

---

## Capture Surfaces (Planned)

Ideas originate in conversations, not documents. The capture mechanisms need to live inside or adjacent to the working surfaces:

| Surface | Mechanism | Fidelity | Event Type |
|---------|-----------|----------|------------|
| CLI tool | `bpsai-pair idea capture "..."` | High | `IdeaCapture` — intentional |
| Claude Code MCP tool | `log_idea(body, tags, source)` | Medium-High | `IdeaCapture` with `agent_extracted: true` |
| Metis (automated) | Cognitive loop observation | Medium-High | `IdeaObserved` — from telemetry pattern detection |
| Claude.ai end-of-session | Manual extraction before closing tab | Medium | `IdeaObserved` — needs confirmation |
| Zoho Cliq | `/idea <text>` bot command | High | `IdeaCapture` — intentional |
| Email ingestion | Forward to dedicated address | Medium | `IdeaObserved` — needs triage |

Lower-fidelity observations flow into a **triage queue** — a single human-in-the-loop checkpoint where `IdeaObserved` events get promoted to `IdeaCapture` or discarded.

---

## Agent Lounge Open Questions — Updated Status

The Lounge doc (`docs/agent-lounge-epistemic-exchange.md`) has 11 open questions. This session answered or partially answered 9 of them.

### Fully Answered

**Q1 — Lounge message format (minimum viable reasoning trace):**
`metis-observations.md` IS the format. Hypothesis updates with evidence chains, new proposals with signal references, document health. Already designed and tested in Bot-S33. The idea log event schema (`{id, created, source, tags, body, status, parent_id, metadata}`) generalizes this for all capture surfaces. `body` carries unstructured reasoning, `metadata` carries structured annotations, `parent_id` chains to what it's responding to.

**Q3 — Persistence vs freshness (how beliefs age):**
Append-only resolves this. Beliefs don't decay by schedule — they're superseded by new events with `parent_id` pointing to the old one. Freshness = most recent event in the chain. Document Lifecycle (`orchestration/document_lifecycle.py`) already tracks when docs become purgeable via `resolves` fields — same pattern extends to ideas. An idea with `status: promoted` and a link to the sprint task is "resolved." An idea with `status: raw` and no children hasn't aged out — it just hasn't been attended to yet.

**Q5 — Bootstrap (approximating the Lounge before it exists):**
Metis IS the bootstrap. Lounge Resident #1 operating autonomously on the portfolio. Once systemd timers are flipped, it demonstrates the full pattern: autonomous reasoning about reasoning, cross-project pattern detection, hypothesis lifecycle management. The portfolio structure with decision rationale (D-013 through D-022) serves as the static Lounge transcript for new sessions.

**Q7 — Evidence graph (view or replacement):**
View. Files and JSONL are source of truth; SQLite/graph is a derived index regenerated on demand. Consistent with Mike's Claude Desktop conclusion ("files are source of truth, live in git; SQLite DB is ephemeral and regenerated on demand") and with the existing infrastructure pattern (all stores use JSONL/YAML files with in-memory load).

**Q10 — Reasoning trace format:**
Both structured and unstructured. The event schema provides `body` (full prose — "I considered A, B, C and chose B because...") and `metadata` (structured JSON — evidence chains, Signal/Hypothesis references, confidence scores). `parent_id` chain IS the structured evidence chain. Agents that reason programmatically use `metadata`; humans read `body`.

### Substantially Answered

**Q4 — Lounge capacity and partitioning:**
The four-tier federation provides natural partitioning. A project-level agent sees ideas from its tier + what propagated from below. Portfolio tier is where cross-project patterns become visible. Capacity bounded per tier. Still open: within a tier, does tag/relevance scoring handle filtering or is there further partitioning (security lounge vs architecture lounge)?

**Q6 — Meta-recursion depth (how many levels of self-reference):**
One. The idea log is flat but self-referential through `parent_id` and tags. The system generates hypotheses about its own performance (HYP-001 about token efficiency, HYP-003 about IDE friction). Those hypotheses are ideas in the same store. No separate meta-meta layer needed.

**Q9 — Topology (structured or discovered):**
Prescribed by the tier model. Ideas propagate upward (User → Project → Portfolio → Org), reasoning traces propagate laterally within a tier and upward through the orchestrator. This follows the Computer hierarchy (Computer1 per project, Computer0 per portfolio). Whether the system should also discover optimal interaction patterns within that structure is still open but less urgent.

**Q11 — What does "better" mean for epistemic self-improvement:**
The idea log adds a concrete metric: **idea-to-action conversion rate** (how many captured ideas become sprint tasks, how many hypotheses reach actionable, average time from raw to promoted). Combined with Decision Journal's `effectiveness_rate()`, this gives a two-part metric: "are we capturing the right ideas?" and "are the decisions from those ideas working?" Still open: whether these two metrics are sufficient or if additional metrics are needed.

### Partially Answered

**Q2 — Relevance scoring algorithm:**
Metis uses signal category matching (estimation/duplication/planning/coordination) against hypothesis `review_after` criteria. This is a working baseline algorithm but not sufficient for full Lounge-scale adversarial relevance evaluation.

### Still Open

**Q8 — Cascade circuit breaker ownership:**
Not addressed in this session. The Lounge doc correctly identifies these as the one thing that should NOT be self-modifiable. Remains the most important open design question for belief propagation safety.

---

## Mike's Claude Desktop Session — Full Reasoning Arc

The following is the complete reasoning arc from Mike's Claude Desktop ideation session, preserved here because the ideas that generated the architecture are as important as the architecture itself.

### The Problem

Little ideas get lost in the shuffle. A markdown doc gets revised. Something that was present in a previous version disappears. The formal planning artifacts capture ideas that survived the filter — not the ideas that didn't make it, or the half-formed hypotheses between a thought and a task.

The question: what would it mean to store planning data in a way that is persistent, versioned, and inexpensive to query — especially when the data is ideas and hypotheses rather than structured records?

### Storage Approaches Considered

1. **Append-only event log (SQLite or flat files)** — Never edit, only append. Ideas are immutable events that evolve by spawning new entries referencing old ones.

2. **One-idea-per-file markdown with YAML frontmatter** — Each idea has its own file with status, tags, project, created, related in frontmatter. Git provides version history. Ideas are never overwritten, only linked to.

3. **SQLite with unstructured text body** — Hybrid: structured fields for querying + prose body with no schema imposed. FTS5 for full-text search at near-zero cost.

4. **Event sourcing** — Every action is an event (IdeaCapture, IdeaRefined, IdeaPromoted, IdeaAbandoned). Current state derived by replaying events.

5. **Recommended hybrid** — One-idea-per-file markdown as the human authoring surface, with SQLite as a derived index built by a script that parses frontmatter. Files are source of truth, live in git. Agents write the same format.

### The Document Reference Question

The event log stores the idea as the body, not as a reference to a document. If an idea is later promoted into a sprint task, a new `IdeaPromoted` event carries the repo reference in metadata:

```json
{
  "repo": "bpsai/computer",
  "path": "sprints/sprint-04.md",
  "line": 42,
  "commit": "a3f9c12"
}
```

The relationship is event -> document, not document -> event. The document is a projection of ideas that made it through the filter. The event log is the full unfiltered history. A doc revision that drops an idea doesn't destroy it — the idea stays in the log with no promotion event attached.

### Fit with the Computer Framework

The idea log maps onto Computer's scope and dispatch architecture:
- A project-level agent has read/write access to Tier 1 and below
- The portfolio orchestrator queries Tier 2
- An org-level orchestrator sits at Tier 3
- Agents do not reach past their tier without going through the orchestrator

The event log becomes the shared memory substrate that agents at different levels read from. A project agent captures a hypothesis -> it lives in Tier 1 -> the portfolio orchestrator pulls it into Tier 2 -> a cross-project pattern becomes visible that no individual agent could see alone.

---

## Assumption Validation (15 Research Papers)

David validated 9 design assumptions against the belief propagation landscape analysis (15 papers, `docs/belief-propagation-landscape-analysis.md`). All assumptions either validated or sharpened — none invalidated.

### Key Resolutions

**A1 — Fork paths (not all ideas are hypotheses): VALIDATED.**
EoG (Paper 2) distinguishes evidence (local facts) from beliefs (global inferences). Feature requests are evidence; hypotheses are beliefs. Different lifecycles. **Design change:** Tag ideas as `evidence` vs `belief` at capture time so the system knows which lifecycle applies.

**A3 — Append-only vs mutable: RESOLVED (the big one).**
- **IdeaStore (capture layer): MUTABLE.** Ideas don't propagate autonomously — promoted by humans or Metis with explicit decisions. No cascade risk. Mutable records with status updates in place (follows existing SignalStore pattern).
- **Future BP layer (belief exchange): APPEND-ONLY.** Bank Runs (Paper 10): if a false signal cascades through belief propagation, you need full audit trail of how each belief was updated, by what evidence, from which source. Mutable records destroy that trail.
- **Insight:** Different layers have different safety requirements. This is a Phase 2 decision made consciously now.

**A5 — Embedding availability: CLOSED.**
Ollama running on bot server (systemd dependency). `nomic-embed-text` (274M, CPU) available via `ollama pull`. Framework has `make_ollama_embed()` + `EpisodicIndex`. All three relevance scorer signals (category + cosine + evidence strength) are available. **Design:** Build pluggable `SimilarityProvider` protocol with `CosineSimilarityProvider` and `KeywordSimilarityProvider` fallback (~10 extra lines).

**A9 — Triage auto-promotion: VALIDATED with safety warning.**
Lying with Truths (Paper 11): truthful evidence fragments combined deceptively achieve 74% attack success. Auto-promoted ideas MUST have audit flags — this is a **safety mechanism, not optional decoration**. The triage tier system (high/medium/low fidelity) is correct but audit flags on medium-fidelity auto-promotions are mandatory.

### Simplified Lifecycle (Post-Validation)

```
observed → captured → promoted → resolved | abandoned
```

5 states for ideas (down from 7). The hypothesis lifecycle (OBSERVED → INSTRUMENTED → INCUBATING → ACTIONABLE) remains unchanged — it's a unique novelty in the landscape and should not be collapsed.

Ideas fork at `captured`:
- **Evidence-type ideas** (feature requests, process changes) → direct to decision/sprint
- **Belief-type ideas** (patterns, observations) → HypothesisBacklog lifecycle

### IDs

ULIDs from the start. Tier sync requires globally unique IDs. No migration needed when multi-org arrives.

---

## Decisions Made (All Sessions Combined)

1. **Portfolio structure is the right foundation** — extend leftward, don't replace.
2. **Composition over construction** — IdeaStore follows SignalStore's mutable JSONL pattern. ~200-250 lines total new code.
3. **Fork paths at capture** — ideas tagged `evidence` vs `belief` determine which lifecycle applies. Not everything goes through hypothesis.
4. **Mutable IdeaStore, append-only future BP layer** — different safety requirements at different layers (Paper 10).
5. **ULIDs from the start** — globally unique, time-sortable, no migration for multi-org.
6. **Pluggable similarity backend** — `SimilarityProvider` protocol with cosine (Ollama + EpisodicIndex) and keyword fallback. Cosine IS available on deployment target.
7. **Conservative scorer thresholds, calibrate from real Metis output** — provisional scaffolds (ABBEL/DANCeRS confirm learned weights replace hand-tuned at maturity).
8. **Auto-promotion audit flags are mandatory safety mechanisms** (Paper 11).
9. **Metis is the automated producer; the idea log is the store** — converge on `docs/portfolio/`, designed as one system.
10. **Nothing restricts the long-term scalability vision** — tier federation, multi-org graduation all compatible.

---

## Validation: The Workspace Command Center Case

During this session, Mike asked whether `paircoder/docs/features/workspace-command-center.md` (a 583-line feature proposal from 2026-03-15) had been captured in the portfolio. The answer: **partially adopted, partially lost.**

- The Sense layer concept was absorbed into FW-S8/S9 (shipped)
- Phases 3/5 (dispatch, web UI) were explicitly superseded by RC (Framework #5 decision, 2026-03-18)
- Phases 1-2 (monitoring dashboard, ~210cx) were **not tracked anywhere** — not in reconciliation, not in status.yaml deferred_work, not in execution priorities

Mike's assessment: the Command Center is still essential. RC handles execution dispatch, but the **human oversight layer across directories, machines, and sessions** is a separate concern RC doesn't cover. "The control tower, not the aircraft."

**This is exactly the kind of loss the idea log prevents.** A document with partially-adopted ideas where the unadopted parts had no formal tracking. The idea didn't get abandoned — it got partially consumed and the remainder evaporated. With the IdeaStore, the original proposal would be an `IdeaCapture` event. The adopted parts would spawn `IdeaPromoted` events linking to FW-S8/S9. The remaining parts would stay as `captured` ideas with no promotion — queryable, visible, never lost.

**Action taken:** Added `workspace-command-center` to `status.yaml` deferred_work (target: FW-S12+, depends on Computer Sense + Learn).

## Remaining Open Questions

1. **Sequencing relative to G1/G2:** Where does the IdeaStore mini-sprint fit against the current sprint plan?
2. **Q8 (cascade circuit breakers):** Non-self-modifiable containment boundary for BP layer. Phase 2 concern but design should start early.
3. **Q2 at Lounge scale:** Full relevance algorithm beyond Phase 1 scorer. Phase 2.

---

## Related Documents

| Document | Relevance |
|----------|-----------|
| `docs/agent-lounge-epistemic-exchange.md` | Open questions Q1-Q11 updated by this session |
| `docs/portfolio/hypotheses/HYP-005.yaml` | Cross-session divergence — the problem this architecture addresses |
| `docs/portfolio/decisions/D-020.yaml` | Metis as Lounge Resident #1 |
| `docs/portfolio/decisions/D-022.yaml` | Document lifecycle + Metis purge checks |
| `docs/portfolio/status.yaml` | Bot-S33 complete, deployment pending |
| `docs/portfolio/execution-priorities.md` | Tier 1-4 priority structure |
| `docs/computer-adaptive-loop-proposal.md` | Five-phase loop that Metis extends |
| `plans/backlogs/bot-sprint-33.md` | Metis Phase 1 implementation details |