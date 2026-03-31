---
id: CD2.3
title: Resume command handler
plan: plan-2026-03-cd2
type: feature
priority: P1
complexity: 5
status: pending
sprint: "CD2"
tags: [resume]
depends_on: [CD2.2]
trello_card_id: "30"
---

# Objective

Handle `type=resume` messages from the A2A dispatch channel. When received, run `claude --resume {session_id}` instead of a fresh `claude -p` session. Enables operators to resume failed or interrupted sessions from Command Center.

# Implementation Plan

- Recognize `type=resume` messages in poll loop (alongside existing `type=dispatch`)
- Extract `session_id` from resume message payload
- Launch `claude --resume {session_id}` with same enforcement as regular dispatch
- Operator scoping enforced — resume message must match daemon's configured operator

# Acceptance Criteria

- [ ] Recognize `type=resume` messages in the poll loop (alongside existing `type=dispatch`)
- [ ] Extract `session_id` from resume message payload
- [ ] Launch `claude --resume {session_id}` subprocess with same enforcement as regular dispatch
- [ ] Operator scoping enforced — resume message must match daemon's configured operator
- [ ] Post lifecycle messages (session-started with `resumed=true`, session-complete) same as fresh sessions
- [ ] Error handling: invalid session_id, session not resumable, Claude Code rejects resume
- [ ] Tests: resume command parsing, subprocess launch with --resume flag, operator scoping, error cases

# Verification

- Send `type=resume` message via A2A → daemon launches `claude --resume`
- Lifecycle messages posted same as fresh session
- Resume message from wrong operator → ignored
