---
id: CD3.5
title: 'End-to-end JWT auth verification   | Repo: bpsai-computer'
plan: plan-sprint-3-engage
type: feature
priority: P0
complexity: 5
status: in_progress
sprint: '3'
depends_on:
- CD3.1
- CD3.2
- CD3.4
---

# End-to-end JWT auth verification   | Repo: bpsai-computer

Start the daemon with real credentials and verify the full dispatch loop: JWT auth → poll A2A → receive dispatch → execute → post result.

# Acceptance Criteria

- [ ] Daemon starts with `operator` from config + auto-discovered `license_id`
- [ ] `TokenManager` successfully obtains JWT from `api.paircoder.ai/api/v1/auth/operator-token`
- [ ] A2A accepts the JWT (200 on poll, not 401)
- [ ] Test dispatch from CC reaches daemon (operator routing matches)
- [ ] Dispatch result posted back to A2A with valid JWT
- [ ] Integration test: mock A2A verifies JWT is present and valid on all requests
- [ ] Document setup in README: install license, create config with operator + workspace, run daemon