---
id: T2I.5
title: Channel escalation routing (D-024)
plan: plan-sprint-2-engage
type: feature
priority: P1
complexity: 8
status: in_progress
sprint: '2'
depends_on: []
---

# Channel escalation routing (D-024)

When a driver hits a permission wall on non-`.claude/` paths, it sends an A2A channel message requesting escalation. A2A needs to route this to the appropriate approval authority (Navigator or human operator). D-024 Hybrid E+F — this is the "F" part (channel escalation at runtime). New message flow: 1. Driver posts `type: "permission-request"` to A2A with `path`, `operation`, `reason` 2. A2A routes to operator's approval queue (filterable in CC) 3. Operator (or Navigator) approves/denies via `type: "permission-response"` 4. Driver polls for response, updates local containment config, retries

# Acceptance Criteria

- [ ] `permission-request` message type accepted by `POST /messages`
- [ ] `permission-response` message type accepted by `POST /messages`
- [ ] Request includes: `path`, `operation` (read/write/execute), `reason`, `task_id`
- [ ] Response includes: `approved` (bool), `scope` (file/directory/glob), `ttl` (seconds)
- [ ] CC can filter messages by `type: "permission-request"` for approval UI
- [ ] Schema defined in shared contracts (T2I.3)