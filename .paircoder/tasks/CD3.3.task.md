---
id: CD3.3
title: 'Show operator ID in Command Center   | Repo: bpsai-command-center'
plan: plan-sprint-3-engage
type: feature
priority: P1
complexity: 5
status: pending
sprint: '3'
depends_on:
- CD3.2
---

# Show operator ID in Command Center   | Repo: bpsai-command-center

Display the user's operator ID in CC so they know what to configure in their daemon. Read-only display in user profile or settings area.

# Acceptance Criteria

- [ ] Operator ID displayed in user profile/settings area of CC
- [ ] Value read from portal JWT `operator` claim (already available after login)
- [ ] Copy-to-clipboard button for easy config setup
- [ ] If no operator ID (legacy user), show "Not assigned — contact admin"
