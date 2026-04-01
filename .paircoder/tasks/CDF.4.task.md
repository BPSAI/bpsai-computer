---
id: CDF.4
title: "Quality: A2A Client + Daemon Hardening"
plan: plan-sprint-CD2-FIX-engage
type: bugfix
priority: P1
complexity: 5
status: pending
sprint: "CD2-FIX"
depends_on: []
---

# Objective

Fix A2A client connection churn, unbounded processed_ids, and parse_dispatch fallback semantics.

# Acceptance Criteria

- [ ] A2A client uses shared httpx.AsyncClient instance with explicit timeouts (connect=5s, read=10s)
- [ ] A2A client has close() method for cleanup, called on daemon shutdown
- [ ] Startup warning if a2a_url is not HTTPS
- [ ] _processed_ids bounded: use OrderedDict or deque with max 10,000 entries
- [ ] parse_dispatch separates JSONDecodeError (plain text fallback) from KeyError (malformed, log warning)
- [ ] Remove dead required variable in config.py
- [ ] Backpressure in streamer logs warning when lines are dropped
- [ ] Test: A2A client reuses connection
- [ ] Test: processed_ids evicts old entries at limit
- [ ] Test: malformed JSON dispatch logs warning
