---
id: T2I.4
title: License-to-org lookup (retire operator workaround)
plan: plan-sprint-2-engage
type: feature
priority: P0
complexity: 12
status: pending
sprint: '2'
depends_on: []
---

# License-to-org lookup (retire operator workaround)

Currently, operator tokens can assert `org_id` via the `purpose: "operator"` exception in `jwt_validator.py`. This is a Phase A workaround — the token issuer (paircoder-api) shouldn't be trusted to assert org membership. Proper fix: A2A resolves `org_id` from `license_id` by calling paircoder-api's license lookup endpoint (or caching the mapping). This removes the security gap where any paircoder-api token with `purpose: "operator"` can claim any org_id.

# Acceptance Criteria

- [ ] A2A resolves `org_id` from `license_id` on token validation (not from JWT claims)
- [ ] `purpose: "operator"` exception removed from `jwt_validator.py`
- [ ] Lookup is cached with reasonable TTL (e.g., 5 min) to avoid per-request API calls
- [ ] If license_id has no org association, request proceeds without org scoping (backward compat)
- [ ] paircoder-api has an endpoint or the existing one returns org_id in license data
- [ ] All existing daemon auth flows continue to work
- [ ] Contract test validates the auth chain end-to-end
