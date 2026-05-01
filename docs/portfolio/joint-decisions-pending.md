# Joint Decisions — David + Mike (RESOLVED)

> **Drafted:** 2026-04-30 evening (David on travel prep)
> **Resolved:** 2026-05-01 (Mike + David walkthrough)
> **Companion to:** `docs/portfolio/phase-c-completion-and-next.md` (the full unified plan)
> **Purpose:** Decision-forward summary. All eight decisions resolved; sprint scope is now definitive.

---

## TL;DR

The Phase C migration is ~90% shipped. All eight gating decisions are now resolved. The next sprint is a conservative single sprint (~90cx) shipping Model A (dashboard) orchestration. DanHil is unblocked via Path A (env-var docs, ~5cx). Adapter extraction (Path B, 35cx) queued for a future sprint — design docs are ready.

---

## The three loaded decisions

### D2 — CC ↔ Computer relationship: dashboard or cockpit?

**RESOLVED: Model A (dashboard)**

CC issues A2A dispatch messages; daemon does the work; CC observes via feeds. ~90cx Track 2 Orchestration.

**Direct session control** (SSH vs Claude native Remote Control vs Daemon-direct) is deferred to Horizon 2 with a dedicated design pass. The method of direct session control requires its own planning round — it is not a Phase C concern.

**Rationale:** Model A gets Phase C shipped and allows us to prove the loop before adding more features. This is the intended dev flow.

---

### HE — Harness adapter scope: Path A now, Path B later

**RESOLVED: Path A (~5cx) ships now. Path B (~35cx) queued for future sprint.**

**What DanHil actually needs** (per `proposal-danhil-commercial-api.md`):
- AP Portal OCR 2.0 → API key swap to DanHil-owned Commercial API org (not a harness change)
- Four developers on PairCoder → same Claude Code harness, DanHil's Commercial API key via `ANTHROPIC_API_KEY`
- Taylor's Claude Cowork → subscription seats (nothing to do with the harness)
- Azure OpenAI fallback → Horizon 2+ (HE3.1/HE5.x per the design doc's own timeline)

**Conclusion:** DanHil needs a different API key behind the same harness, not a different harness. Path A unblocks them immediately.

**Path B status:** The design docs (`harness-adapter-design.md`, `harness-adapter-extraction.md`) are solid and ready to execute. The adapter extraction (HE0.1–HE1.2) is queued for a future sprint. It just doesn't need to block revenue.

**Immediate action:** Write env-var docs and ship the convenience command (~5cx). DanHil unblocked.

**Unblocked:** DanHil onboarding, AP Automation key migration, four developer activations.

---

### Switch timing — single conservative sprint

**RESOLVED: Conservative path (~90cx, one sprint)**

Model A inherently means the cockpit is deferred, so the rich path (~200cx) does not apply. Ship Track 2 Orchestration at conservative scope, switch to Computer/CC orchestration, then layer richer capabilities in Horizon 2.

**Rationale:** Validate that "orchestrate from Computer/CC" works at all before deepening it. Mistakes are cheaper to find at 90cx than at 200cx.

---

## The five lighter decisions

| ID | Question | **Resolution** | Cx | Unblocks |
|----|----------|----------------|-----|----------|
| **D1** | How does CC see project state? | **Hybrid — GitHub MCP tool for plans/state.md, A2A for live signals.** Give the UI Claude Chat a GitHub MCP tool or similar. | ~10 | Track 2 Orchestration scope |
| **D3** | Plan lifecycle: chat-trigger + chat-approval, or UI approval? | **Chat-trigger + chat-approval.** No special UI needed. Operator starts a plan via chat, Claude drafts it, operator approves in chat. | ~20 | Track 2 Orchestration scope |
| **AKS** | Amunet knowledge scanner: Horizon 1 or Horizon 2? | **Horizon 2.** Let migration finish first. | 26 | Sprint composition |
| **EA5** | Deprecate `--hooks-advisory` flag, or just delete? | **Delete.** No users; trivial. | 5 | Closes engage lifecycle |
| **Plan 4 substrate types** | Does `ReasoningTrace` schema live in `bpsai-framework` or `bpsai-a2a`? | **bpsai-framework** (cross-repo schema authority); a2a re-exports. | 5 | PL.3 implementation kickoff |

---

## What's ready to start now

### Mike (no blockers)
- **T2I.2** — Session-resume A2A message type (8cx). Backlog defined; ready to implement.
- **T2I.4** — License → org_id lookup (12cx). Cross-repo with paircoder-api; can be started in parallel with T2I.2.

### David (HE resolved → Path A)
- Write the env-var docs and ship the convenience command (~5cx). DanHil unblocked.

### Either operator (D1/D2/D3 resolved)
- Draft `bpsai-computer/plans/backlogs/track-2-orchestration.md` per the conservative Model A path (~90cx).
- Draft `bpsai-a2a/plans/backlogs/belief-store-v1.md` (PL.4 substrate per Mike's §9.4 ratification — in-A2A, extraction-ready).

---

## Switch trigger checklist (reference)

When all of these are green, David flips off framework-orchestration:

- [ ] T2I.2 shipped and merged
- [ ] T2I.4 shipped and merged (paircoder-api endpoint included)
- [ ] ~~D1, D2, D3 resolved and committed~~ ✓ Resolved 2026-05-01
- [ ] Track 2 Orchestration baseline shipped
- [ ] CCD dispatch UI shipped and tested in CC
- [ ] Validation sprint: one full sprint orchestrated end-to-end from CC → daemon → driver → review → result, David monitoring not driving
- [ ] Framework `dev → main` merge planned post-switch (housekeeping)

---

## Post-ratification follow-up pass (do not lose)

Items deliberately deferred until decisions resolve. Full consolidated list lives in `phase-c-completion-and-next.md` §7.7. Highlights:

- **Update `execution-priorities.md`** Phase C section to point to the unified plan (plan-ratified trigger)
- **Update `status.yaml`** with verified test counts and completion percentages (plan-ratified trigger)
- **Draft 3 new backlogs:** `track-2-orchestration.md` (✓ unblocked), `belief-store-v1.md` (anytime), `knowledge-scanner.md` (AKS → Horizon 2, not urgent)
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

---

## Decision resolution session (2026-05-01)

All 8 decisions resolved in a single walkthrough between Mike and David. Key themes:

1. **Conservative across the board** — Model A, Path A, single sprint, chat-based approval. Ship and prove before layering.
2. **DanHil is a key-swap, not an architecture change** — the three in-review docs confirmed DanHil needs the same harness with a different API key. Path B design is ready for when we genuinely need multiple adapters.
3. **Direct session control needs its own design pass** — the method (SSH vs Claude native vs Daemon-direct) is a Horizon 2 question that deserves proper planning, not a Phase C bolt-on.
