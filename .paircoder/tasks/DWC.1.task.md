---
id: DWC.1
title: Per-workspace config file resolution
plan: plan-sprint-0-engage
type: feature
priority: P0
complexity: 5
status: in_progress
sprint: '0'
depends_on: []
---

# Per-workspace config file resolution

Update `load_config()` in `config.py` to resolve config path from workspace name. When `--workspace` is provided, look for `~/.bpsai-computer/{workspace}.yaml` first, then fall back to `~/.bpsai-computer/config.yaml` for backwards compatibility. If neither exists, require all fields via CLI flags.

# Acceptance Criteria

- [ ] `load_config()` accepts optional `workspace` parameter
- [ ] When workspace provided: first try `~/.bpsai-computer/{workspace}.yaml`, then `config.yaml`
- [ ] When no workspace provided: use `config.yaml` (existing behavior)
- [ ] CLI `--workspace` flag passes workspace to `load_config()`
- [ ] Clear error message if config file not found: "No config found. Create ~/.bpsai-computer/{workspace}.yaml"
- [ ] Tests: workspace-specific config loaded, fallback to config.yaml, missing config error