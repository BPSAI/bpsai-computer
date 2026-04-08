# Metis Fleet Visibility — Signal Push + Git/CI Summary

> **Budget:** ~25cx
> **Repo:** bpsai-computer
> **Sprint ID:** MFV-C
> **Depends on:** CD3 (daemon JWT auth)
> **Design ref:** bpsai-framework/docs/design/metis-fleet-visibility.md

---

## Context

Metis runs on GitHub Actions every 6 hours but can only see the bot repo. She has zero visibility into sibling repo signals, git activity, or CI results across the portfolio. The Computer daemon already runs locally with full workspace access — this sprint extends it to push local signals and git/CI summaries to A2A, making them available to Metis and the rest of the fleet.

Signal push is fire-and-forget: failure must not block the daemon's dispatch polling loop.

---

### Phase 1: Signal Aggregation + Push

### MFVC.1 — Signal push in daemon | Cx: 15 | P0

**Description:** Extend the daemon's poll loop to read `signals.jsonl` from each workspace repo and push new signals to the A2A `/signals` endpoint. Track a cursor (last-pushed line number per repo) in daemon state so only new signals are pushed on each cycle. Each signal message includes the `operator` field from config, the source repo name, and the original timestamp. Push is fire-and-forget — failures are logged and retried on the next cycle, never blocking dispatch polling.

**AC:**
- [ ] Daemon discovers all repos under `workspace_root` that contain `.paircoder/telemetry/signals.jsonl`
- [ ] Cursor state persisted to `~/.bpsai-computer/signal_cursors.json` (repo path → last line number)
- [ ] New signals since cursor are POSTed to A2A `/signals` endpoint with `operator`, `repo`, and `timestamp` fields
- [ ] Push failure logs warning and continues — does not block dispatch polling
- [ ] Push runs on each poll cycle (same cadence as dispatch polling)
- [ ] Batch mode: multiple signals per repo bundled into a single POST when possible
- [ ] Tests: cursor tracking, new signal detection, push failure resilience, batch assembly

### Phase 2: Git + CI Summary

### MFVC.2 — Git + CI summary push | Cx: 10 | P0

**Description:** Push a lightweight git and CI summary for each workspace repo on each daemon cycle. This replaces Metis's `git_evidence.py` and `ci_evidence.py` filesystem reads with structured A2A messages. The summary includes commits since last push (count, authors, repos touched), test results from the most recent local run (pass/fail/skip counts), open PRs and their status, and branch state (ahead/behind for dev/main).

**Depends on:** MFVC.1

**AC:**
- [ ] Git summary collected per repo: commit count since last push, author list, branch ahead/behind counts
- [ ] CI/test summary collected per repo: last pytest result (pass/fail/skip counts) from `.paircoder/telemetry/` or local cache
- [ ] Open PR count and status collected via `git log --remotes` or local branch tracking (no GitHub API dependency from daemon)
- [ ] Summary POSTed to A2A `/signals` endpoint with `signal_type: "git_summary"` and `signal_type: "ci_summary"`
- [ ] Cursor state tracks last-pushed git commit SHA per repo to avoid re-sending
- [ ] Fire-and-forget: push failure does not block daemon
- [ ] Tests: git summary collection, CI result parsing, cursor tracking, push resilience

---

## Summary

| Task | Title | Cx | Priority |
|------|-------|----|----------|
| MFVC.1 | Signal push in daemon | 15 | P0 |
| MFVC.2 | Git + CI summary push | 10 | P0 |
| **Total** | | **25** | |

## Execution Order

```
MFVC.1 (signal push) → MFVC.2 (git/CI summary)
```

## Priority Order

1. MFVC.1 — Signal push (foundation for all fleet visibility)
2. MFVC.2 — Git/CI summary (extends signal push with structured summaries)
