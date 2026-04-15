---
id: T2I.6
title: Notification severity routing
plan: plan-sprint-2-engage
type: feature
priority: P1
complexity: 5
status: pending
sprint: '2'
depends_on: []
---

# Notification severity routing

A2A needs severity-based filtering so CC can populate the Notifications panel (CCH.7) without polling all messages. Messages already have a `severity` field but A2A doesn't support filtering by it on `GET /messages/feed`.

# Acceptance Criteria

- [ ] `GET /messages/feed` accepts `severity` query parameter (info, warning, error, critical)
- [ ] `GET /messages/feed` accepts `min_severity` for threshold filtering (e.g., min_severity=warning returns warning+error+critical)
- [ ] Existing messages without severity default to `info`
- [ ] Contract test validates severity filtering
