---
id: T2I.2
title: Session-resume message type
plan: plan-sprint-2-engage
type: feature
priority: P0
complexity: 8
status: pending
sprint: '2'
depends_on: []
---

# Session-resume message type

New A2A message type so CC (and future Navigator) can request the daemon resume a paused or interrupted session. Shared dependency for CCH.5 (session drill-down) and Track 2 (Navigator resume flow). Risk R3 mitigation. The daemon already has `ResumeMessage` dataclass (`dispatcher.py` line ~35) with `session_id` and `target`. The A2A side needs: - Message type `session-resume` accepted by `POST /messages` - Routing: `to_project` + `operator` + `workspace` targeting (same as dispatch) - Daemon poll picks it up, constructs `ResumeMessage`, calls `claude --resume <session_id>`

# Acceptance Criteria

- [ ] `POST /messages` accepts `type: "session-resume"` with `session_id` in metadata
- [ ] Daemon polls receive session-resume messages
- [ ] Daemon correctly constructs `ResumeMessage` and resumes the Claude Code session
- [ ] Lifecycle events posted for resumed sessions (session-resumed, session-complete/failed)
- [ ] If session_id is invalid or expired, daemon posts error lifecycle event
- [ ] Contract test validates schema between CC, A2A, and daemon
