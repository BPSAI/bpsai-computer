# Phase C Completion + What's Next — Joint Plan

> **Authors:** David Wiens + Mike Doggett + Claude (Navigator role, drafted 2026-04-30)
> **Status:** DRAFT — pending joint David + Mike review
> **Supersedes upon ratification:**
> - `bpsai-framework/plans/phase-c-overview.md`
> - `bpsai-framework/plans/phase-c-execution-plan.md`
> - `bpsai-framework/plans/phase-c-abstraction-gaps.md`
> - `bpsai-framework/plans/backlogs/sprint-next-high-impact.md`
> - The Phase C section of `bpsai-computer/docs/portfolio/execution-priorities.md`
>
> **Scope:** Cross-repo planning for Phase C completion (Horizon 1, 1-2 sprints) and post-migration roadmap (Horizon 2, 3-6 months).
>
> **Audience:** David and Mike. This doc is the single source of truth for joint planning going forward; both operators work from it in Computer/CC.

---

## 0. Why this doc exists

We discovered on 2026-04-30 that planning artifacts had drifted ~2 weeks behind shipping reality. Verification across all repos established:

- **FW-C extraction (12 tasks, 115cx) is shipped.** Framework reduced to ~5,354 LOC (still includes back-compat shims). Working code lives in `bpsai-computer`.
- **CCH (Mike's CC hardening, 9 tasks, 84cx) is shipped.** All Activity Feed UX, drill-down, notifications, multi-op disambiguation, workspace selector landed and merged.
- **T2I (Computer Track 2 Independent) is 5 of 8 shipped (33cx done).** T2I.1 was folded into Track 2 Orchestration; T2I.2 (8cx) and T2I.4 (12cx) remain open.
- **Metis Live Pipeline (5 tasks, 72cx) is shipped.** 97 briefing files on disk; BriefingPanel live; BriefingReader injecting into Computer state.
- **Engage lifecycle (EA1-EA6, ~45cx) is 5 of 6 shipped** in v2.23.0 through v2.25.3. Only EA5 (deprecate `--hooks-advisory`) remains.
- **Reasoning trace schema is fully ratified** (David 2026-04-29; Mike 2026-04-30, commit `a47bb68`). PL.3 implementation is unblocked.

The planning docs being stale meant we underestimated how close we are to "orchestrate from Computer/CC" — that capability is one focused sprint away, not a multi-month track. This doc reflects verified ground truth and replaces the older partial views.

---

## 1. Branch state and switch trigger

The framework repo is in a **deliberate dev/main divergence posture**:

- `bpsai-framework/dev` — 59 commits ahead of `main`. Holds post-extraction shim cleanup, schema ratifications, recent design docs, version bumps.
- `bpsai-framework/main` — David's current operational baseline. Contains the FW-C extraction (so orchestration code is there), but lacks the recent ratifications and design artifacts. Held back as the safety rollback point until migration is verified end-to-end.

**The switch trigger is a discrete planning event**, not a side-effect. David flips from "orchestrating from `framework/main`" to "orchestrating from Computer/CC" when:

1. T2I.2 + T2I.4 shipped (20cx, see §3.1)
2. Mike's D1/D2/D3 decisions resolved (§2)
3. Track 2 Orchestration baseline shipped (Navigator + plan lifecycle minimum, §3.2)
4. CCD dispatch UI shipped (§3.3)
5. **Validation sprint:** one full sprint orchestrated end-to-end from CC → daemon → driver → review → result, with David monitoring rather than directly operating from framework

Post-switch, `bpsai-framework/dev → main` reconverges via normal merge; framework branch state returns to standard pattern. This reconvergence is **not** a prerequisite for switch — it's a follow-up housekeeping event.

**During the transition window:** doc/cleanup work in framework lands on `dev`, not `main`. Don't push directly to framework `main` until after switch is verified.

---

## 2. Decision block — Mike's three architectural decisions

Source: `bpsai-computer/docs/design/track2-orchestration-decisions.md` (and the recent reframe at commit `2d3c6c5` recasting D2 as a product question).

These three decisions shape Track 2 Orchestration scope. They need joint resolution **before** §3.2 work starts.

| ID | Question | Recommended | Cx swing |
|----|----------|-------------|----------|
| D1 | How does CC see project state? | Hybrid (GitHub for artifacts, A2A for live signals) | ~10cx |
| D2 | What is CC's relationship to Computer? | **Product-level question — dashboard (Model A) vs cockpit (Model D)** | 0-80cx |
| D3 | Plan lifecycle (who creates/renders/approves) | Chat trigger + chat approval (conservative) vs UI approval | ~20cx |

**D2 is the load-bearing decision.** Recent docs (`3b8150c`, `2d3c6c5`) reframe it as the fundamental product call: is CC an org-wide visibility surface that dispatches via A2A messages (Model A — leaner, faster to ship), or a cockpit with direct daemon sessions and rich interactivity (Model D — heavier, more interactive, longer to ship)?

**Cx implications of the resolved path:**

- **Conservative (D1: GitHub-heavy + D2: Model A + D3: Chat):** ~90cx Track 2 Orchestration
- **Mid-range (Hybrid + Model A + UI approval):** ~110cx
- **Rich cockpit (Hybrid + Model D + UI approval):** ~170-200cx

**Recommendation for Phase C completion:** Choose the conservative path. Ship the Model A dispatch loop, validate the switch trigger, and revisit Model D in Horizon 2 once usage shows whether richer interactivity is genuinely needed. Premature Model D commitment risks dragging Phase C completion into multiple sprints when a single conservative sprint plus a follow-up gets the same operational capability faster.

This recommendation is non-binding. David and Mike resolve these three together; this doc's only job is to surface the cx implications so the trade-off is visible.

---

## 3. Horizon 1 — Migration completion + epistemic minimum

**Goal:** Switch trigger fires. David orchestrates from Computer/CC. Reasoning-trace schema operationalized. Stale docs reconciled.

**Budget:** 130-240cx depending on D2 path. Conservative scope is one focused sprint; rich cockpit is two.

### 3.1 Computer T2I — finish what's open

Two unshipped P0 tasks from the existing T2I backlog:

| Task | Title | Cx | Owner | Notes |
|------|-------|----|-------|-------|
| T2I.2 | Session-resume A2A message type | 8 | Mike | No blockers; ready to start. Unblocks CCH.5 + Navigator resume flow. |
| T2I.4 | License → org_id lookup (retire `purpose=operator` workaround) | 12 | Mike + David | Cross-repo: needs paircoder-api endpoint. Security debt. |

**Subtotal: 20cx.**

### 3.2 Computer Track 2 Orchestration

**Depends on D1/D2/D3 resolution (§2).** Backlog to be drafted at `bpsai-computer/plans/backlogs/track-2-orchestration.md` once decisions land.

Conservative-path scope (D2 = Model A):

| Area | Cx | Notes |
|------|----|----|
| Navigator agent in Computer | ~30 | Imports framework planning primitives via shims; runs in daemon |
| Plan lifecycle (create/render/approve via Chat) | ~20 | Chat-driven trigger and approval; plan stored as A2A `plan-*` message |
| Status updater + review automation glue | ~20 | Wires extracted modules into Computer's portfolio state |
| D-024 hybrid E+F operator approval surface | ~20 | Infrastructure shipped (T2I.5); needs CC operator-prompt UI |

**Conservative subtotal: ~90cx.**

If the rich-cockpit path is chosen, scope grows to ~170-200cx (direct daemon sessions, richer plan UI, live interactivity).

### 3.3 CCD — CC dispatch UI

**Repo:** `bpsai-command-center`
**Backlog:** `bpsai-command-center/plans/backlogs/cc-dispatch-ui.md`
**Owner:** Mike
**Budget:** ~20cx
**Depends on:** D2 resolution

Last remaining Phase A item. Lets David trigger dispatches from CC Chat instead of CLI engage. Final piece for switch trigger.

### 3.4 Epistemic minimum (newly unblocked)

Mike's 2026-04-30 ratification of `reasoning-trace-schema-decision.md` §7.1-§7.8 unblocks the pull-forward proposal originally scoped for Phase D+. The minimum surface fits in Horizon 1:

| Track | Cx | Repos | Status |
|-------|----|----|--------|
| **PL.3 reasoning_trace implementation** | 17 | bpsai-framework + bpsai-a2a + bpsai-agents + bpsai-command-center | Backlog at `bpsai-framework/plans/backlogs/pl3-reasoning-trace-implementation.md` (header still says BLOCKED — needs unblock). 6 subtasks. |
| **PL.1/PL.2 prime-learn + #knowledge channel** | 13 | paircoder + bpsai-a2a | Backlog at `bpsai-framework/plans/backlogs/archive/prime-learn-command.md` (in archive — needs to come out). 2 subtasks. |
| **PL.4 belief store v1 design** | TBD | bpsai-a2a | Substrate decided per §9.4: **in-A2A, extraction-ready** (Mike, 2026-04-30). Needs backlog drafted at `bpsai-a2a/plans/backlogs/belief-store-v1.md`. Implementation cx unknown until designed. |

**Subtotal (PL.1/PL.2/PL.3): 30cx.** PL.4 design deferred to end of Horizon 1; implementation moves to Horizon 2.

PL.1/PL.2 can ship independently of PL.3 (narrative-only traces). PL.3 unblocks PL.4 implementation; PL.4 unblocks Plans 5-6 (Metis centralization, Lounge MVP) in Horizon 2.

### 3.5 Cleanup track (parallel, low priority)

| Item | Cx | Notes |
|------|----|----|
| Framework shim cleanup | ~15-25 | Physically delete shimmed orchestration modules (`engine/sprint_planner.py` et al.) once consumer migration is verified via `bpsai-pair sweep`. **Dev branch only** until switch trigger fires. |
| Backlog archival | ~5 | See §7. |
| In-review doc resolution (DanHil/harness adapter cluster) | ~10 (decision work, not implementation) | See §2 + Horizon 2 §4.3. |
| Stale doc cleanup (PL3 header, state.md, archive moves) | ~3 | See §7. |
| EA5 — deprecate `--hooks-advisory` | ~5 (or delete) | Only EA task that didn't ship. Trivial. |

**Subtotal: ~40cx parallel work.** Framework-side, can run alongside Computer Track 2 Orchestration.

### 3.6 Horizon 1 budget summary

| Component | Conservative | Rich |
|-----------|--------------|------|
| T2I.2 + T2I.4 | 20 | 20 |
| Track 2 Orchestration | 90 | 200 |
| CCD dispatch UI | 20 | 20 |
| Epistemic minimum (PL.1-PL.3) | 30 | 30 |
| Parallel cleanup | 40 | 40 |
| **Total** | **~200cx** | **~310cx** |

Conservative path: one focused sprint at full velocity, or split across two if parallel work claims capacity. Rich-cockpit path: two sprints minimum.

---

## 4. Switch trigger checklist

When all of these are green, David flips from `framework/main` orchestration to Computer/CC orchestration:

- [ ] T2I.2 shipped and merged
- [ ] T2I.4 shipped and merged (paircoder-api endpoint included)
- [ ] D1, D2, D3 resolved and committed to design doc
- [ ] Track 2 Orchestration baseline shipped (Navigator agent live + plan lifecycle minimum)
- [ ] CCD dispatch UI shipped and tested in CC
- [ ] Validation sprint completed: one end-to-end orchestration from CC Chat → daemon → driver → review → result, with David monitoring rather than running framework
- [ ] Framework `dev → main` merge planned post-switch (housekeeping)

Trigger condition is **all** boxes ticked. No partial flip.

---

## 5. Horizon 2 — Post-migration multi-track roadmap

Several tracks become parallelizable once orchestration moves to Computer/CC. This section is the candidate set; sprint composition is decided per-sprint against David + Mike capacity.

### 5.1 Epistemic exchange program continuation

Per the priming doc at `bpsai-framework/docs/design/epistemic-exchange-program.md`, Plans 1-11.

| Plan | Title | Status |
|------|-------|--------|
| 1 | Reasoning trace schema | ✅ Ratified |
| 2 | `reasoning_trace` on `HandlerResult` | Horizon 1 (PL.3) |
| 3 | `/prime-learn` + `#knowledge` channel | Horizon 1 (PL.1/PL.2) |
| 4 | Append-only belief store v1 (in-A2A per §9.4) | Horizon 2 (design end of H1, build H2) |
| 5 | Metis centralization | Horizon 2 (blocked on Plan 4) |
| 6 | Agent Lounge MVP (6a relevance / 6b updates / 6c UI) | Horizon 2 (blocked on Plans 4-5) |
| 7 | Surprisal formalization | Deferred (proxy is adequate; revisit post-Lounge MVP) |
| 8 | Hash-chained provenance | Horizon 2 (small, parallel; bolts onto trace_id) |
| 9 | Cascade circuit breakers | Horizon 2 (parallel to Lounge work) |
| 10 | GitHub thread reply (#13287) | Anytime, low effort |
| 11 | External paper / partner outreach | Background, gated on patent posture |

### 5.2 Heimdall extraction

Source: `bpsai-framework/plans/backlogs/heimdall-extraction.md` + Track A spec.

- **Scope:** ~95cx, 6 tracks. Extract to standalone `bpsai-heimdall` repo.
- **Two-tier eval:** local triage → frontier reasoning.
- **Depends on:** Phase C completion + A2A `/signals` endpoint (already shipped) + Lounge S1.
- **Sequencing call (from 2026-04-29 conversation):** Extract Track A first to establish repo separation, then build B-D in parallel.

### 5.3 Harness adapter — decision required

Two competing positions, decision still open after 2 weeks:

- **Path A** (`phase-c-overview.md`, 2026-04-14): ~5cx env-var docs + convenience command. Provider agnosticism via `ANTHROPIC_BASE_URL` since Claude Code is the universal harness.
- **Path B** (`docs/in_review/harness-adapter-extraction.md`, 2026-04-17): 35cx Protocol + extraction. Scaffolds for future Codex/local-model adapters.

**Stakes:** DanHil + AP Automation + four developer onboardings are waiting on this. Revenue-blocking.

**Recommendation:** Pick now. If Path A is sufficient for DanHil's actual needs, ship docs in Horizon 1's parallel cleanup track and unblock onboarding immediately. If the four developers genuinely need a different model surface, Path B is the right architecture but should be scoped against revenue impact, not architectural elegance.

### 5.4 Amunet knowledge scanner (force multiplier)

Source: `bpsai-framework/plans/backlogs/sprint-next-high-impact.md` Track 3.

- **Scope:** AKS1-AKS4, ~26cx, in `bpsai-amunet`.
- **What it does:** Extends Amunet from code scanning to knowledge scanning. Produces topic cards (~50 lines each) indexing scattered docs across 12 repos. Card catalog model, not Karpathy-wiki content migration.
- **Why now:** Reduces "where is that doc?" tax that compounds every sprint. Connects to Lounge (knowledge nodes), Prime/A2A (topic cards via signal), Metis (staleness as observation).

### 5.5 Attestation tiers (from 2026-04-29 paircoder conversation)

| Tier | Criteria | Status |
|------|----------|--------|
| Bronze | Registered + protocol-conformant | Ready post A2A-2 |
| Silver | Lifecycle-active + effectiveness-tracked | Ready today |
| Gold | Adversarially-survived + reasoning-trace-emitting | **Now unblocked by PL.3 ratification** |
| Platinum | Provenance-verifiable + independence-asserted | Hard by design (see §9.2 of schema doc — independence-under-shared-priors problem) |

Tier-gated launch path resolves the §9.1 public-exposure question (Bronze/Silver expose conclusions + hash chains; Gold exposes redacted excerpts under adversarial challenge; Platinum is operator-elective full disclosure).

### 5.6 Cross-track items

Smaller pieces that show up across multiple sprints:

- **bpsai-a2a:** signed agent cards (A2A-2), notification severity routing maturation, federation positioning (Discussion #741).
- **paircoder_api:** workspace listing endpoint (already partially shipped via T2I.7).
- **Bot:** PromptBuilder adoption (framework voice consumption).
- **Lounge:** continued S2+ work post-MVP.

---

## 6. Framework's role going forward

Once migration completes, framework becomes a **stewardship project with episodic contribution surges**, not a hot-development project. Most active development moves to Computer + agents + Lounge + CC. Framework's role is curation, schema authority, and patent-grade quality on the core primitives.

### 6.1 Near-term (next 1-2 sprints after switch)

| Track | Cx | Notes |
|-------|----|----|
| Shim cleanup | 15-25 | Physically remove shimmed orchestration modules. Hygienic, low-risk. |
| In-review doc shepherding | ~10 (decision work) | Resolve the 7 docs in `docs/in_review/`. Most route work to other repos rather than generating framework code. |
| Schema centralization | 10-20 | Decide where cross-cutting types canonically live (e.g., `ReasoningTrace` is currently slated for `a2a/schemas.py` but used by framework, agents, lounge, CC — there's an architectural argument for framework owning the source). |

### 6.2 Medium-term

| Track | Cx | Notes |
|-------|----|----|
| Patent #1 hardening (Enforcement Pipeline) | TBD | Formal claims doc, test-to-claim mapping, attorney materials. Framework owns this candidate per `patent-briefing.md`. |
| Eval framework expansion | ~50-100 | Cross-agent quality measurement. Framework already has `eval_dataset.py`/`eval_metrics.py`/`model_evaluator.py` foundations. |
| Lifecycle Tier 2/3 (SQL event table) | ~30 | Listed in `execution-priorities.md` Tier 4. Audit trail for ideas/docs. Framework-native. |
| Patent candidates that bolt onto framework primitives | varies | Plans 7 (surprisal), 8 (hash-chained provenance), 9 (cascade breakers). |

### 6.3 Long-term (Phase D+)

- **SDK for third-party agent integration** — once external partners want to plug in (DanHil and beyond), framework becomes the public-facing contract surface. Likely the single biggest framework chapter ahead.
- **Belief store schemas** — even though Mike's §9.4 ratification put the belief store substrate in-A2A, the **type definitions** may want to live in framework so Lounge, Metis, Computer import a single source of truth. Decision deferred to Plan 4 design.

### 6.4 Development cadence implication

Active framework development tapers significantly post-switch. Expect a few PRs per month for schema/eval/patent work. The active product surface lives in Computer + agents + Lounge + CC. This is the intended end-state of Phase C migration.

---

## 7. Backlog triage

### 7.1 Archive (shipped)

Move to `archive/` (or delete) in framework `dev`:

- `framework-phase-c-extraction.md` (12/12 shipped via `9cc3efd`/`154a7f9`)
- `metis-briefing-pipeline.md` (5/5 shipped Apr 8 — restoration artifact, never updated)
- `metis-live-pipeline.md` (verify; likely shipped)
- `phase-c-pr34-remediation.md` (per state.md, near-complete)
- `phase-c-david-sprint.md` (verify)
- `telemetry-hypothesis-integrity.md` (per execution-priorities, completed)
- `phase-c-overview.md` (superseded by this doc)
- `phase-c-execution-plan.md` (superseded)
- `phase-c-abstraction-gaps.md` (superseded — verify content not lost)
- `sprint-next-high-impact.md` (superseded; HE absorbed into §5.3, EA1-4/6 archived as shipped, EA5 in §3.5, AKS in §5.4)

### 7.2 Unblock and keep open

- `pl3-reasoning-trace-implementation.md` — header still says **BLOCKED**. Update to **READY**. Backlog content stands as written; both ratifications captured.

### 7.3 Move out of archive

- `archive/prime-learn-command.md` → move to active `plans/backlogs/prime-learn-command.md` (PL.1/PL.2 are Horizon 1 work).

### 7.4 Active framework backlogs (keep open, no change)

- `cli-release-hardening.md`
- `heimdall-extraction.md` and `heimdall-track-a-extraction.md` (Heimdall is its own project; stays framework-side until extracted)

### 7.5 In-review docs requiring resolution

Located in `bpsai-framework/docs/in_review/`. Resolve as part of §3.5 cleanup track:

| Doc | Decision needed |
|-----|-----------------|
| `harness-adapter-design.md` + `harness-adapter-extraction.md` | Pick Path A or Path B (§5.3) |
| `proposal-danhil-commercial-api.md` | Approve / modify / decline DanHil partnership scope |
| `runbook-ap-automation-key-migration.md` | Approve runbook for AP Automation cutover |
| `enterprise-consumer-onboarding.md` | Approve consumer onboarding flow |
| `enterprise-integration-playbook.md` | Approve enterprise integration path |
| `data-flow-per-deployment-mode.md` | Ratify deployment topology |

### 7.6 New backlogs to draft (during Horizon 1)

- `bpsai-computer/plans/backlogs/track-2-orchestration.md` — post-D1/D2/D3 resolution
- `bpsai-a2a/plans/backlogs/belief-store-v1.md` — PL.4 substrate per §9.4
- `bpsai-amunet/plans/backlogs/knowledge-scanner.md` — AKS1-AKS4 promoted from sprint-next-high-impact

### 7.7 Post-ratification follow-up pass

Items deliberately deferred until David + Mike ratify this plan and resolve §8 decisions. Single consolidated punch-list so nothing gets lost between decision and execution:

| Item | Where | Why deferred | Trigger |
|------|-------|--------------|---------|
| Rewrite Phase C section of `bpsai-computer/docs/portfolio/execution-priorities.md` as a thin index pointing to this doc | bpsai-computer | Avoid altering pre-existing canonical doc before joint sign-off | Plan ratified |
| Update `bpsai-computer/docs/portfolio/status.yaml` with verified test counts (Computer 648, Framework still 1,146, etc.) and Phase C completion percentages | bpsai-computer | Machine-readable portfolio state belongs to post-ratification pass | Plan ratified |
| Draft `bpsai-computer/plans/backlogs/track-2-orchestration.md` per resolved D1/D2/D3 path (conservative ~90cx or rich ~200cx) | bpsai-computer | Scope depends on D1/D2/D3 outcomes | D1/D2/D3 resolved |
| Draft `bpsai-a2a/plans/backlogs/belief-store-v1.md` per Mike's §9.4 ratification (in-A2A, extraction-ready) | bpsai-a2a | Substrate decided but design work not yet done | Anytime; ideally end of Horizon 1 |
| Draft `bpsai-amunet/plans/backlogs/knowledge-scanner.md` (AKS1-AKS4) | bpsai-amunet | Inclusion in Horizon 1 vs Horizon 2 is open decision (§8 AKS) | AKS decision resolved |
| Decide and document harness adapter Path A vs Path B; either ship Path A docs (~5cx) or kick off HE0.1 | bpsai-framework | DanHil revenue-blocking decision still open | HE decision resolved |
| Resolve where `ReasoningTrace` schema canonically lives (framework vs a2a) before PL.3 implementation begins | bpsai-framework / bpsai-a2a | §8 Plan 4 substrate types decision; ~5cx refactor cost either way | Plan 4 substrate decision |
| EA5: deprecate `--hooks-advisory` flag (or just delete) | paircoder | §8 EA5 decision; trivial either way | EA5 decision resolved |
| Resolve 6 in-review docs in `bpsai-framework/docs/in_review/` (DanHil cluster, enterprise integration, deployment topology) | bpsai-framework | Each routes work to other repos rather than generating framework code | Joint review session |
| Plan framework `dev → main` reconvergence merge | bpsai-framework | Housekeeping after switch trigger fires | Switch trigger fires |
| Framework shim cleanup: physically remove shimmed orchestration modules | bpsai-framework dev | Wait until consumer migration is verified via `bpsai-pair sweep`; risk if done before switch | Switch trigger fires + sweep verification |

This list is the complete post-ratification workstream. Items resolve in dependency order; nothing here is gated on something not listed.

---

## 8. Open decisions (need David + Mike resolution)

Surfaced for clarity. Resolution happens in joint review, not in this doc.

| ID | Decision | Owner | Cx swing | Blocks |
|----|----------|-------|----------|--------|
| D1 | CC ↔ project state mechanism | Mike + David | ~10cx | Track 2 Orchestration scope |
| D2 | CC ↔ Computer relationship (dashboard / cockpit) | **Mike + David — product call** | 0-80cx | Track 2 Orchestration scope; CCD design |
| D3 | Plan lifecycle (Chat / UI approval) | Mike + David | ~20cx | Track 2 Orchestration scope |
| HE | Harness adapter scope (Path A / Path B) | David + Mike | ~30cx | DanHil onboarding, AP Automation cutover, 4 developer onboardings |
| AKS | Amunet knowledge scanner: Horizon 1 or Horizon 2? | David | 26cx | Sprint composition |
| EA5 | `--hooks-advisory` deprecation: ship or delete? | David | 5cx | Trivial |
| Plan 4 substrate types | Where do belief store schemas canonically live (framework / a2a)? | David + Mike | ~5cx (refactor cost) | PL.4 design |
| Switch timing | Single sprint conservative path, or two sprints rich cockpit path? | David + Mike | 100cx scope delta | Phase C completion timeline |

---

## 9. Source docs (referenced, not superseded)

This doc is a cross-track planning index. The following docs remain canonical for their respective domains:

**Framework design canon:**
- `bpsai-framework/docs/design/epistemic-exchange-program.md` (priming, Plans 1-11)
- `bpsai-framework/docs/design/reasoning-trace-schema-decision.md` (ratified)
- `bpsai-framework/docs/design/cc-phase-c-landscape-2026-04-16.md` (research snapshot)
- `bpsai-framework/docs/agent-lounge-epistemic-exchange.md` (Lounge vision)
- `bpsai-framework/docs/belief-propagation-landscape-analysis.md` (academic comparison)
- `bpsai-framework/docs/patent-briefing.md` (IP posture, 4 candidates)

**Computer design canon:**
- `bpsai-computer/docs/design/track2-orchestration-decisions.md` (Mike's D1/D2/D3)
- `bpsai-computer/docs/design/computer-daemon-plan.md`
- `bpsai-computer/docs/design/computer-prime-recursive-dispatch.md`

**Cross-repo:**
- `bpsai-computer/docs/portfolio/execution-priorities.md` (post-Phase-C section will be rewritten as a thin index pointing here once this doc is ratified)
- `bpsai-computer/docs/portfolio/status.yaml` (machine-readable portfolio state)

---

## 10. Signals this plan is working

When executed, expected indicators:

- **Single source of truth for joint planning** (this doc, in Computer)
- **David and Mike orchestrate from Computer/CC**, not from local framework checkouts
- **Sprint planning happens via CC chat**, not via doc-drafting in editors
- **Framework dev/main reconverges** post-switch; framework PRs decline to a few per quarter
- **Computer test count crosses 1,000+** (currently 648, up from 265 on 2026-04-15)
- **Epistemic layer (PL.3)** emits reasoning traces from at least 2 pilot agents (Nayru, Metis)
- **DanHil onboarded** following harness adapter resolution

If any of these stalls, this doc gets updated in place. It is the single canonical starting point for joint Phase C and post-Phase-C planning; corrections happen here, not in new parallel artifacts.
