---
id: T2I.7
title: Workspace listing endpoint
plan: plan-sprint-2-engage
type: feature
priority: P1
complexity: 5
status: done
sprint: '2'
depends_on: []
completed_at: '2026-04-15T01:03:49.598478'
---

# Workspace listing endpoint

CCH.9 (workspace selector in CC header) needs a list of workspaces accessible to the current operator/org. This endpoint belongs in paircoder-api since it owns the license/org/workspace relationship.

# Acceptance Criteria

- [x] `GET /workspaces` returns workspaces for the authenticated operator
- [x] Response includes `workspace_id`, `name`, `workspace_root` (optional), `status`
- [x] Scoped by org_id from JWT claims
- [x] CC can call this to populate the workspace dropdown
- [x] Works with both portal JWT and operator JWT auth