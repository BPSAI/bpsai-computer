---
id: MFVC.2
title: Git + CI summary push
plan: plan-sprint-0-engage
type: feature
priority: P0
complexity: 10
status: in_progress
sprint: '0'
depends_on:
- MFVC.1
---

# Git + CI summary push

Push a lightweight git and CI summary for each workspace repo on each daemon cycle. This replaces Metis's `git_evidence.py` and `ci_evidence.py` filesystem reads with structured A2A messages. The summary includes commits since last push (count, authors, repos touched), test results from the most recent local run (pass/fail/skip counts), open PRs and their status, and branch state (ahead/behind for dev/main).

# Acceptance Criteria

- [ ] Git summary collected per repo: commit count since last push, author list, branch ahead/behind counts
- [ ] CI/test summary collected per repo: last pytest result (pass/fail/skip counts) from `.paircoder/telemetry/` or local cache
- [ ] Open PR count and status collected via `git log --remotes` or local branch tracking (no GitHub API dependency from daemon)
- [ ] Summary POSTed to A2A `/signals` endpoint with `signal_type: "git_summary"` and `signal_type: "ci_summary"`
- [ ] Cursor state tracks last-pushed git commit SHA per repo to avoid re-sending
- [ ] Fire-and-forget: push failure does not block daemon
- [ ] Tests: git summary collection, CI result parsing, cursor tracking, push resilience