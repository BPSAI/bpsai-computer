---
id: CD3.4
title: 'Auto-discover license_id from license.json   | Repo: bpsai-computer'
plan: plan-sprint-3-engage
type: feature
priority: P0
complexity: 5
status: done
sprint: '3'
depends_on: []
completed_at: '2026-04-07T22:34:17.738644'
---

# Auto-discover license_id from license.json   | Repo: bpsai-computer

Remove `license_id` as a required config field. Instead, find and read `~/.paircoder/license.json` (same search order as PairCoder CLI). Extract `payload.license_id` for use in `TokenManager`.

# Acceptance Criteria

- [x] `config.py`: `license_id` field defaults to None (no longer required)
- [x] New `license_discovery.py` module: finds license.json, reads payload, returns license_id
- [x] `daemon.py` startup: if `license_id` not in config, auto-discover from license file
- [x] Clear error message if no license found: "No license found. Run: bpsai-pair license install <file>"
- [x] Config file `license_id` overrides auto-discovery (for cloud VMs with no CLI installed)
- [x] Tests: discovery from home dir, env var override, config override, missing file error