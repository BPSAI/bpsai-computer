---
id: CDF.2
title: "Security: Credential Scrubbing Gaps"
plan: plan-sprint-CD2-FIX-engage
type: bugfix
priority: P0
complexity: 5
status: pending
sprint: "CD2-FIX"
depends_on: []
---

# Objective

Fix raw stdout buffer leak and expand scrubber patterns for missed credential types.

# Acceptance Criteria

- [ ] _stdout_lines stores scrubbed content (or clear buffer after extract_session_id)
- [ ] Scrubber patterns added: GitHub PATs (ghp_, github_pat_), GCP OAuth (ya29.), OpenAI keys (sk-), URL-embedded credentials (://user:pass@)
- [ ] extract_session_id regex capped at 256 chars
- [ ] Test: stdout_lines does not contain raw credentials
- [ ] Test: each new scrubber pattern catches its target
