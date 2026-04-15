---
id: T2I.8
title: Daemon multi-message-type support
plan: plan-sprint-2-engage
type: feature
priority: P0
complexity: 5
status: pending
sprint: '2'
depends_on: []
---

# Daemon multi-message-type support

The daemon currently handles `dispatch` and `resume` message types. Track 2 adds `plan-proposal`, `permission-request`, `permission-response`, and potentially `review-request`. The dispatcher's `_parse_dispatch` method needs to be a proper message type router rather than a conditional chain.

# Acceptance Criteria

- [ ] Dispatcher has a registry of message type handlers
- [ ] Adding a new message type is: define handler function + register it
- [ ] Unknown message types are logged and acked (not silently dropped, not crashed)
- [ ] Existing dispatch and resume flows unchanged
- [ ] Tests cover each registered message type
