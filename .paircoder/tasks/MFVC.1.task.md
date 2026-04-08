---
id: MFVC.1
title: Signal push in daemon
plan: plan-sprint-0-engage
type: feature
priority: P0
complexity: 15
status: in_progress
sprint: '0'
depends_on: []
---

# Signal push in daemon

Extend the daemon's poll loop to read `signals.jsonl` from each workspace repo and push new signals to the A2A `/signals` endpoint. Track a cursor (last-pushed line number per repo) in daemon state so only new signals are pushed on each cycle. Each signal message includes the `operator` field from config, the source repo name, and the original timestamp. Push is fire-and-forget — failures are logged and retried on the next cycle, never blocking dispatch polling.

# Acceptance Criteria

- [ ] Daemon discovers all repos under `workspace_root` that contain `.paircoder/telemetry/signals.jsonl`
- [ ] Cursor state persisted to `~/.bpsai-computer/signal_cursors.json` (repo path → last line number)
- [ ] New signals since cursor are POSTed to A2A `/signals` endpoint with `operator`, `repo`, and `timestamp` fields
- [ ] Push failure logs warning and continues — does not block dispatch polling
- [ ] Push runs on each poll cycle (same cadence as dispatch polling)
- [ ] Batch mode: multiple signals per repo bundled into a single POST when possible
- [ ] Tests: cursor tracking, new signal detection, push failure resilience, batch assembly