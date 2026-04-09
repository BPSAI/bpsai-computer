---
id: DBS.1
title: Update collectors to use /signals/batch
plan: plan-sprint-0-engage
type: feature
priority: P0
complexity: 5
status: in_progress
sprint: '0'
depends_on: []
---

# Update collectors to use /signals/batch

Update SignalPusher, GitSummaryCollector, and CISummaryCollector to POST to `/signals/batch` instead of `/signals`. Generate deterministic `signal_id` client-side for idempotency. Format timestamps as canonical ISO 8601 UTC.

# Acceptance Criteria

- [x] All three collectors POST to `/signals/batch`
- [x] Payload format: `{"operator": str, "repo": str, "signals": [{"signal_type": str, "severity": str, "timestamp": str, "payload": dict, "signal_id": str}]}`
- [x] `signal_id` generated deterministically per signal for dedup
- [x] Timestamps formatted as `YYYY-MM-DDTHH:MM:SSZ` (canonical UTC, no microseconds)
- [x] Fire-and-forget preserved — batch failure logged, doesn't block daemon
- [x] Tests updated to verify new URL and payload format