---
id: T2I.7
title: Workspace listing endpoint
plan: plan-sprint-2-engage
type: feature
priority: P1
complexity: 5
status: pending
sprint: '2'
depends_on: []
---

# Workspace listing endpoint

CCH.9 (workspace selector in CC header) needs a list of workspaces accessible to the current operator/org. This endpoint belongs in paircoder-api since it owns the license/org/workspace relationship.

# Acceptance Criteria

- [ ] `GET /workspaces` returns workspaces for the authenticated operator
- [ ] Response includes `workspace_id`, `name`, `workspace_root` (optional), `status`
- [ ] Scoped by org_id from JWT claims
- [ ] CC can call this to populate the workspace dropdown
- [ ] Works with both portal JWT and operator JWT auth
