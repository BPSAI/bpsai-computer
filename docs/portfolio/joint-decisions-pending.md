# Joint Decisions Pending — David + Mike

> **Drafted:** 2026-04-30 evening (David on travel prep)
> **For:** Mike (overnight or morning) and David (morning return)
> **Companion to:** `docs/portfolio/phase-c-completion-and-next.md` (the full unified plan)
> **Purpose:** Decision-forward summary. Each item is something to resolve before the next sprint kicks off.

---

## TL;DR

The Phase C migration is ~90% shipped. We are one focused sprint away from David switching off framework-orchestration onto Computer/CC. Eight decisions gate that sprint's scope and sequencing. Three are loaded enough to deserve a real conversation; the rest are quick yes/no calls.

---

## The three loaded decisions

### D2 — CC ↔ Computer relationship: dashboard or cockpit?

**The question:** Is Command Center primarily an **org-wide visibility surface that dispatches via A2A messages** (Model A — leaner, faster to ship), or a **cockpit with direct daemon sessions and rich interactivity** (Model D — heavier, more capability)?

**Why it's loaded:** This is the product call, not just an architecture call. Mike already reframed it that way in commit `2d3c6c5`. The cx swing is 0-80cx for Track 2 Orchestration alone, and it shapes CCD dispatch UI scope (~20cx more or less).

**Options on the table:**
- **Model A (dashboard):** CC issues A2A dispatch messages; daemon does the work; CC observes via feeds. ~90cx Track 2 Orchestration.
- **Model B (direct frontend):** CC connects directly to daemons. ~150cx.
- **Model C (MCP bridge):** CC → MCP → daemon. Indirect, more flexible. ~140cx.
- **Model D (hybrid A+direct):** A2A for org-wide observability, direct sessions for active work. ~170-200cx.

**Recommendation:** Pick Model A for Phase C completion. Ship the dispatch loop, validate the switch trigger, revisit Model D in Horizon 2 once usage shows whether richer interactivity is genuinely worth the cost. Premature Model D risks dragging Phase C across multiple sprints.

**Unblocks if resolved:** Track 2 Orchestration backlog can be drafted at `bpsai-computer/plans/backlogs/track-2-orchestration.md`. CCD dispatch UI scope locks in.

---

### HE — Harness adapter scope: Path A or Path B?

**The question:** Do we ship **Path A** (~5cx of env-var docs + a convenience CLI command, leveraging the fact that Claude Code already supports all providers via `ANTHROPIC_BASE_URL`) or **Path B** (~35cx Protocol + ClaudeCodeAdapter extraction, scaffolding for future Codex/local-model adapters)?

**Why it's loaded:** This is **revenue-blocking**. DanHil + AP Automation + four developer onboardings are waiting. The question has been open for 2 weeks across three docs that contradict each other (`phase-c-overview.md` says Path A, `harness-adapter-extraction.md` says Path B, `sprint-next-high-impact.md` carries Path B forward).

**Source docs to read:**
- `bpsai-framework/docs/in_review/harness-adapter-design.md`
- `bpsai-framework/docs/in_review/harness-adapter-extraction.md`
- `bpsai-framework/docs/in_review/proposal-danhil-commercial-api.md`

**Recommendation framing (not a recommendation):** This is yours. The technical question is "does DanHil need a different harness or just a different model behind the same harness?" If the latter, Path A solves it tomorrow. If the former, Path B is the right architecture but should be scoped against revenue impact, not architectural elegance.

**Unblocks if resolved:** DanHil onboarding, AP Automation key migration, four developer activations.

---

### Switch timing — single conservative sprint or two-sprint rich path?

**The question:** Do we ship Track 2 Orchestration at the conservative scope (~90cx, one sprint) and switch to Computer/CC orchestration immediately, then layer richer capabilities in Horizon 2? Or do we commit to the rich-cockpit scope (~200cx, two sprints) and switch later with more capability already in place?

**Why it's loaded:** A 100cx scope delta. The conservative path gets us off framework-orchestration faster and validates the loop before we invest in richer surfaces. The rich path means a single longer commitment but lands with more product surface from day one.

**Recommendation:** Conservative path, then layer. Validate that "orchestrate from Computer/CC" works at all before deepening it. Mistakes are cheaper to find at 90cx than at 200cx.

**Unblocks if resolved:** Sprint composition for the next sprint becomes definitive.

---

## The five lighter decisions

| ID | Question | Recommended answer | Cx | Unblocks |
|----|----------|---------------------|----|----------|
| **D1** | How does CC see project state? | Hybrid (GitHub for plans/state.md, A2A for live signals) | ~10 | Track 2 Orchestration scope |
| **D3** | Plan lifecycle: chat-trigger + chat-approval, or UI approval? | Chat trigger + chat approval (conservative) | ~20 | Track 2 Orchestration scope |
| **AKS** | Amunet knowledge scanner: Horizon 1 or Horizon 2? | Horizon 2 — let migration finish first | 26 | Sprint composition |
| **EA5** | Deprecate `--hooks-advisory` flag, or just delete? | Delete (no users; trivial) | 5 | Closes engage lifecycle |
| **Plan 4 substrate types** | Does `ReasoningTrace` schema live in `bpsai-framework` or `bpsai-a2a`? | bpsai-framework (cross-repo schema authority); a2a re-exports | 5 | PL.3 implementation kickoff |

---

## What's ready to start the moment decisions land

Independent of the decisions above, two pieces of work can start tonight or first thing tomorrow:

### Mike (anytime, no blockers)
- **T2I.2** — Session-resume A2A message type (8cx). Backlog defined; ready to implement.
- **T2I.4** — License → org_id lookup (12cx). Cross-repo with paircoder-api; can be started in parallel with T2I.2.

### David (after the harness decision)
- If Path A: write the env-var docs and ship the convenience command (~5cx). DanHil unblocked.
- If Path B: kick off HE0.1 (DispatchAdapter Protocol, 5cx).

### Either operator (after D1/D2/D3 resolved)
- Draft `bpsai-computer/plans/backlogs/track-2-orchestration.md` per the resolved path.
- Draft `bpsai-a2a/plans/backlogs/belief-store-v1.md` (PL.4 substrate per Mike's §9.4 ratification — in-A2A, extraction-ready).

---

## Switch trigger checklist (reference)

When all of these are green, David flips off framework-orchestration:

- [ ] T2I.2 shipped and merged
- [ ] T2I.4 shipped and merged (paircoder-api endpoint included)
- [ ] D1, D2, D3 resolved and committed
- [ ] Track 2 Orchestration baseline shipped
- [ ] CCD dispatch UI shipped and tested in CC
- [ ] Validation sprint: one full sprint orchestrated end-to-end from CC → daemon → driver → review → result, David monitoring not driving
- [ ] Framework `dev → main` merge planned post-switch (housekeeping)

---

## Post-ratification follow-up pass (do not lose)

Items deliberately deferred until decisions resolve. Full consolidated list lives in `phase-c-completion-and-next.md` §7.7. Highlights:

- **Update `execution-priorities.md`** Phase C section to point to the unified plan (plan-ratified trigger)
- **Update `status.yaml`** with verified test counts and completion percentages (plan-ratified trigger)
- **Draft 3 new backlogs:** `track-2-orchestration.md` (D1/D2/D3-gated), `belief-store-v1.md` (anytime), `knowledge-scanner.md` (AKS-gated)
- **Resolve 6 in-review docs** in `bpsai-framework/docs/in_review/` (DanHil cluster, enterprise, deployment topology)
- **Framework shim cleanup** — physically remove shimmed modules (switch-trigger-gated; risky if done early)
- **Framework `dev → main` reconvergence** post-switch (housekeeping)

Don't proceed on these until the gating decision/event resolves. List exists so the pass doesn't get forgotten between decision and execution.

---

## What was done today (2026-04-30)

For context if either operator is picking this up cold:

- Verified across all repos that ~90% of Phase C migration is shipped (FW-C extraction, CCH, T2I 5/8, MLP 5/5, EA 5/6, schema ratified)
- Drafted the unified plan at `docs/portfolio/phase-c-completion-and-next.md`
- Reconciled stale backlogs: archived 10 shipped/superseded plan docs in framework `dev`, unblocked PL.3 backlog header, moved `prime-learn-command.md` out of archive
- Surfaced 8 decisions (this doc)
- Confirmed framework dev/main divergence is deliberate; switch trigger is a discrete event, not a side-effect

Full context in `phase-c-completion-and-next.md` §0-§3 and §10.
