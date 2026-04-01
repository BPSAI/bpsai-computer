---
id: CDF.3
title: "Quality: Lifecycle Error Handling + Streamer Session ID"
plan: plan-sprint-CD2-FIX-engage
type: bugfix
priority: P0
complexity: 5
status: pending
sprint: "CD2-FIX"
depends_on: []
---

# Objective

Fix OutputStreamer session_id mismatch and lifecycle error handling crash path.

# Acceptance Criteria

- [ ] OutputStreamer initialized with session_id (not message_id) in daemon.py
- [ ] _execute_with_lifecycle wrapped in try/except so post_started failure does not crash dispatch pipeline, returns failure DispatchResult instead
- [ ] Return type annotation added: -> tuple[str, DispatchResult]
- [ ] Test: lifecycle posting failure during startup does not crash daemon
- [ ] Test: streamer session_id matches lifecycle session_id
