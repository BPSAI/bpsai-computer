# Sprint Computer-1 — A2A Discussion #741 Stake-Out + Heimdall Issue Tracking

> **Status:** Ready (drafted 2026-04-29)
> **Repo:** bpsai-computer
> **Scope:** Plant our flag in Discussion #741 (A2A registry federation) without disclosing patent material; track Heimdall extraction as a Computer-Prime-overseen initiative.
> **Velocity:** PairCoder-paced — small, mostly drafting.

## Context

Two cross-cutting items belong to bpsai-computer's orchestration scope rather than to a single repo:

1. **A2A Discussion #741** ([github.com/a2aproject/A2A/discussions/741](https://github.com/a2aproject/A2A/discussions/741)) — the A2A registry/federation architecture is being debated and the spec is open. Two proposals: federation-of-catalogs (xRegistry-style sync) vs. federation-of-peers (cryptographic P2P). Generic search, hierarchical namespaces, and entitlement filtering are unresolved. There's a window to influence the standard. We'd want to comment in a way that positions us as a stakeholder without pre-disclosing patent material.

2. **Heimdall extraction tracking** — Heimdall Track A is a `bpsai-framework`/`bpsai-heimdall` sprint, but Computer Prime owns the orchestration view. The two open issues filed in `bpsai-computer` ([#9](https://github.com/BPSAI/bpsai-computer/issues/9) for SDK pin hardening, [#10](https://github.com/BPSAI/bpsai-computer/issues/10) for Heimdall seed list) need to be linked to the actual Heimdall sprints once those land.

## Dependencies

**Blocks:** Nothing critical.

**Blocked by:**
- D10 (attorney consultation) — limits how detailed our #741 comment can be on the attestation model. Comment must stay above the IP-relevant line.
- Heimdall Track A start (separate sprint) — gates the link-up in C1.2.

**Cross-repo coordination:** Loose ties to all of bpsai-a2a, bpsai-framework, bpsai-heimdall (when it exists), agentlounge.ai.

## Tasks

### C1.1 — Draft A2A Discussion #741 comment | Cx: 2 | P1

**Description:** Write a comment that positions us as a stakeholder in the A2A registry federation discussion. Cover what we'd implement and what we'd want from a federated standard, without disclosing the specific attestation tier mechanism or hash-chained provenance specifics that are patent candidates.

**Safe to mention:**
- We're building a registry frontend (agentlounge.ai)
- Interest in §8.4 signed Agent Cards as foundation
- Domain-match verification as a baseline anti-impersonation tier
- Interest in standard discovery / search endpoints
- Lifecycle-stage-based attestation as a concept (graduated → binary by stage)
- Cross-base-model considerations for adversarial validation

**Do NOT mention:**
- Specific hash-chain mechanism details
- Surprisal-weighted propagation specifics
- Belief-store-as-attestable artifact mechanics
- ProbLog vs. binary truth model specifics tied to our actual implementation
- Anything from `bpsai-framework/docs/patent-briefing.md`

**AC:**
- [ ] Draft saved to `bpsai-computer/.paircoder/drafts/discussion-741-comment.md`
- [ ] Reviewed against patent briefing doc — no overlap with named candidates
- [ ] Comment posted to discussion (after David approval)
- [ ] Discussion thread linked in this sprint completion

---

### C1.2 — Link bpsai-computer #9 and #10 to actual sprints | Cx: 1 | P2

**Description:** Issues #9 (SDK pin hardening) and #10 (Heimdall seed list) currently exist as cross-cutting trackers. Link them to the actual sprint backlogs once those land:
- #9 → `bpsai-a2a/.paircoder/plans/backlogs/sprint-45-a2a-sdk-1.0-migration.md` + `paircoder_api/.paircoder/plans/backlogs/sprint-45-a2a-sdk-1.0-migration.md`
- #10 → Heimdall Track B (when it exists; currently only Track A is shaped at `bpsai-framework/plans/backlogs/heimdall-track-a-extraction.md`)

**AC:**
- [ ] Both issues updated with sprint links
- [ ] Closing criteria documented on each (e.g., #9 closes when both pin sprints complete)

---

### C1.3 — Heimdall portfolio status update | Cx: 1 | P2

**Description:** `bpsai-computer/docs/portfolio/status.yaml` already references "Heimdall platform sentinel". Add explicit pointer to the new `bpsai-heimdall` repo (when created in Heimdall Track A) and Track-by-Track status.

**AC:**
- [ ] portfolio/status.yaml updated with new repo URL + Track A/B/C/D/E/F status fields
- [ ] portfolio/execution-priorities.md cross-references this backlog

## Out of scope

- Building Heimdall itself — `bpsai-framework/plans/backlogs/heimdall-track-a-extraction.md` and the rest of `heimdall-extraction.md`
- Operating the registry — agentlounge.ai work
- Drafting the patent — separate workstream entirely

## Definition of done

- Discussion #741 comment drafted, reviewed, posted (with David approval)
- Issues #9 and #10 linked to their sprint backlogs
- Portfolio status reflects Heimdall extraction state
