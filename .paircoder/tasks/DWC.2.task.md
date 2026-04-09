---
id: DWC.2
title: Concurrent daemon isolation
plan: plan-sprint-0-engage
type: feature
priority: P0
complexity: 5
status: done
sprint: '0'
depends_on:
- DWC.1
completed_at: '2026-04-08T20:02:41.664545'
---

# Concurrent daemon isolation

Ensure multiple daemon instances can run simultaneously for different workspaces without conflicts. Each daemon should use workspace-scoped cursor files, PID files, and log prefixes so state doesn't collide.

# Acceptance Criteria

- [x] Cursor files scoped by workspace: `~/.bpsai-computer/{workspace}/signal_cursors.json` (not shared)
- [x] Log messages prefixed with `[{workspace}]` for clarity when multiple daemons run
- [x] PID file per workspace: `~/.bpsai-computer/{workspace}.pid` to detect if a daemon is already running
- [x] `bpsai-computer daemon --workspace bpsai` and `bpsai-computer daemon --workspace aurora` can run concurrently
- [x] Tests: two configs loaded independently, cursor files don't collide