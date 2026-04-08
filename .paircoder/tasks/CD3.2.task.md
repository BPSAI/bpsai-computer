---
id: CD3.2
title: 'Include operator claim in portal JWT   | Repo: bpsai-support (FastAPI)'
plan: plan-sprint-3-engage
type: feature
priority: P0
complexity: 5
status: pending
sprint: '3'
depends_on:
- CD3.1
---

# Include operator claim in portal JWT   | Repo: bpsai-support (FastAPI)

When minting portal access tokens, include the `operator` claim from the user's `operator_id`. A2A already reads `payload.get("operator")` with fallback to `sub`.

# Acceptance Criteria

- [ ] `mint_access_token` in `portal_session.py` adds `"operator": user_data["operator_id"]` to JWT claims
- [ ] Claim only included when `operator_id` is not None (backward compat for users without one)
- [ ] `validate_portal_token` extracts and returns `operator` claim
- [ ] Tests: JWT contains operator claim, round-trip validation
