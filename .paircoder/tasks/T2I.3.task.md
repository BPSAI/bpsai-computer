---
id: T2I.3
title: Shared message schema definitions
plan: plan-sprint-2-engage
type: feature
priority: P0
complexity: 10
status: in_progress
sprint: '2'
depends_on: []
---

# Shared message schema definitions

Define the message schemas used between CC, daemon, and A2A as Pydantic models in a shared location. During Phase A E2E we hit 4 schema mismatches because each repo defined its own format. Phase C adds new message types (plan proposals, driver status, review results, session-resume) which multiplies the surface area (Risk R7). Options: - **Option A:** Small `bpsai-contracts` package on PyPI — all three repos depend on it - **Option B:** Schema definitions in bpsai-a2a (source of truth), snapshot tests in CC and daemon - **Option C:** JSON Schema files in bpsai-a2a, validated in each repo's test suite Decide on approach, implement it, and migrate existing message types (`dispatch`, `lifecycle`, `result`, `signal`).

# Acceptance Criteria

- [ ] All existing A2A message types have a single source-of-truth schema definition
- [ ] New Phase C message types have schema definitions before implementation
- [ ] CC, daemon, and A2A each have tests that validate against the shared schema
- [ ] Adding a new message type requires updating one place, not three
- [ ] Schema for `plan-proposal`, `driver-status`, `review-result`, `session-resume` defined (even if endpoints don't exist yet)