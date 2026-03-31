---
id: CD2.1
title: Stream stdout incrementally
plan: plan-2026-03-cd2
type: feature
priority: P0
complexity: 15
status: done
sprint: CD2
tags:
- streaming
depends_on: []
trello_card_id: '28'
completed_at: '2026-03-30T20:14:11.093126'
---

# Objective

Read Claude Code subprocess output line-by-line and post incremental `session-output` messages to A2A. Currently the daemon waits for process completion then posts the full result. This adds real-time streaming so operators can watch sessions in progress.

# Implementation Plan

- Async non-blocking readline on subprocess stdout/stderr
- Configurable batch interval — buffer lines and post every N seconds (default 2s)
- Credential scrubber runs on each line before posting (reuse CD1 scrubber)
- Backpressure: drop oldest if buffer exceeds limit
- Final result message still posted on completion (backwards compatible)

# Acceptance Criteria

- [x] Read subprocess stdout/stderr line-by-line (async, non-blocking)
- [x] Post `session-output` messages to A2A with: session_id, line_number, content, stream (stdout/stderr), timestamp
- [x] Configurable batch interval — buffer lines and post every N seconds (default 2s) to avoid flooding
- [x] Credential scrubber runs on each line before posting (reuse existing scrubber from CD1)
- [x] Graceful handling of rapid output (backpressure: drop oldest if buffer exceeds limit)
- [x] Final result message still posted on process completion (backwards compatible with CD1 behavior)
- [x] Tests: line-by-line reading, batched posting, credential scrubbing on stream, buffer overflow handling

# Verification

- Dispatch a task → see incremental output lines appearing in A2A messages
- Output contains no credentials (scrubber working)
- Rapid output doesn't crash daemon (backpressure working)
- Final result still posted on completion