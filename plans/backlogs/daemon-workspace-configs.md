# Daemon Per-Workspace Configs

> **Budget:** ~10cx
> **Repo:** bpsai-computer
> **Sprint ID:** DWC
> **Depends on:** CD3 (shipped)

---

## Context

Users run multiple workspaces (e.g., BPSAIWorkspace, AuroraWorkspace, DanHilApWorkspace) and may want a daemon per workspace. Currently the daemon reads a single `~/.bpsai-computer/config.yaml`. This sprint adds per-workspace config file support so each workspace has its own operator identity, workspace root, and A2A settings.

```
~/.bpsai-computer/
├── bpsai.yaml         # workspace=bpsai, workspace_root=G:/PycharmProjects/BPSAIWorkspace
├── aurora.yaml        # workspace=aurora, workspace_root=G:/PycharmProjects/AuroraWorkspace
├── danhil.yaml        # workspace=danhil, workspace_root=G:/PycharmProjects/DanHilApWorkspace
└── config.yaml        # legacy fallback (backwards compat)
```

Usage: `bpsai-computer daemon --workspace bpsai` loads `~/.bpsai-computer/bpsai.yaml`.

---

### Phase 1: Config Resolution

### DWC.1 — Per-workspace config file resolution | Cx: 5 | P0

**Description:** Update `load_config()` in `config.py` to resolve config path from workspace name. When `--workspace` is provided, look for `~/.bpsai-computer/{workspace}.yaml` first, then fall back to `~/.bpsai-computer/config.yaml` for backwards compatibility. If neither exists, require all fields via CLI flags.

**AC:**
- [ ] `load_config()` accepts optional `workspace` parameter
- [ ] When workspace provided: first try `~/.bpsai-computer/{workspace}.yaml`, then `config.yaml`
- [ ] When no workspace provided: use `config.yaml` (existing behavior)
- [ ] CLI `--workspace` flag passes workspace to `load_config()`
- [ ] Clear error message if config file not found: "No config found. Create ~/.bpsai-computer/{workspace}.yaml"
- [ ] Tests: workspace-specific config loaded, fallback to config.yaml, missing config error

### Phase 2: Multi-Daemon Support

### DWC.2 — Concurrent daemon isolation | Cx: 5 | P0

**Description:** Ensure multiple daemon instances can run simultaneously for different workspaces without conflicts. Each daemon should use workspace-scoped cursor files, PID files, and log prefixes so state doesn't collide.

**Depends on:** DWC.1

**AC:**
- [ ] Cursor files scoped by workspace: `~/.bpsai-computer/{workspace}/signal_cursors.json` (not shared)
- [ ] Log messages prefixed with `[{workspace}]` for clarity when multiple daemons run
- [ ] PID file per workspace: `~/.bpsai-computer/{workspace}.pid` to detect if a daemon is already running
- [ ] `bpsai-computer daemon --workspace bpsai` and `bpsai-computer daemon --workspace aurora` can run concurrently
- [ ] Tests: two configs loaded independently, cursor files don't collide

---

## Summary

| Task | Title | Cx | Priority |
|------|-------|----|----------|
| DWC.1 | Per-workspace config file resolution | 5 | P0 |
| DWC.2 | Concurrent daemon isolation | 5 | P0 |
| **Total** | | **10** | |

## Execution Order

```
DWC.1 (config resolution) → DWC.2 (isolation)
```
