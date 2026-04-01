---
id: CDF.1
title: "Security: Input Validation + Operator Fix"
plan: plan-sprint-CD2-FIX-engage
type: bugfix
priority: P0
complexity: 10
status: pending
sprint: "CD2-FIX"
depends_on: []
---

# Objective

Fix three security findings that combine into an exploit path: operator bypass, path traversal, and session_id injection.

# Acceptance Criteria

- [ ] Operator check inverted: reject when msg_operator != self.config.operator (missing field = rejected, not bypassed)
- [ ] Path traversal guard: repo_dir.resolve() must be under workspace_root.resolve(), reject otherwise
- [ ] session_id validated against ^[a-zA-Z0-9\-_]{1,256}$ in parse_resume, reject non-matching
- [ ] target validated against ^[a-zA-Z0-9\-_.]{1,128}$ in both parse_dispatch and parse_resume
- [ ] Test: resume with missing operator field -> rejected
- [ ] Test: resume with path traversal target (../../../etc) -> rejected
- [ ] Test: resume with invalid session_id (abc --output /tmp/pwned) -> rejected
- [ ] Test: dispatch with path traversal target -> rejected
