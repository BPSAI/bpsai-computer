# Computer₀ Dispatch Daemon — Plan

> **Status:** Approved (2026-03-29, Mike)
> **Budget:** ~30cx
> **Repo:** bpsai-computer (BPSAI org)
> **Depends on:** A2A operator field (CC-S1 T1.3), Command Center Phase 0

---

## Purpose

The dispatch daemon is Computer₀'s runtime. It bridges the Command Center (cloud) and local execution (Claude Code on developer machines or VMs). When a user issues a dispatch command through the Command Center, the daemon picks it up and executes it locally.

This is the first concrete deliverable of the bpsai-computer repo, which was scoped in D-023 as the workspace orchestrator.

## Architecture

```
Command Center (cloud)
    → User types "dispatch Bellona to audit bpsai-a2a"
    → Computer (Claude API) POSTs to A2A:
        {type: "dispatch", operator: "mike", workspace: "bpsai",
         agent: "bellona", target: "bpsai-a2a", ...}

A2A Backend (a2a.paircoder.ai)
    → Stores message with operator + workspace fields

Dispatch Daemon (local machine or VM)
    → Polls GET /messages?type=dispatch&operator=mike&workspace=bpsai&unacknowledged_only=true
    → Receives dispatch command
    → Launches: claude -p "audit bpsai-a2a" --agent security-auditor
    → Acks the message: POST /messages/ack {message_id, response: "dispatched"}
    → Monitors Claude Code process
    → On completion, POSTs result to A2A:
        {type: "dispatch-result", operator: "mike", workspace: "bpsai", content: "...", ...}

Command Center Activity Feed
    → Shows the dispatch-result in real-time
```

## Key Design Constraints

### Operator + Workspace Routing
- Each daemon runs with an `operator` identity AND a `workspace` identity
- Daemon ONLY consumes messages matching BOTH its operator AND workspace
- This enables one user running multiple Computer instances across workspaces:

```
Mike's BPS daemon:    operator=mike, workspace=bpsai
Mike's DanHil daemon: operator=mike, workspace=danhil
David's BPS daemon:   operator=david, workspace=bpsai
Cloud VM:             operator=mike-vm, workspace=bpsai
```

- Multiple daemons can run simultaneously (Mike's laptop, David's desktop, a cloud VM)
- A cloud VM can run as operator "mike-vm" for 24/7 execution
- Command Center includes a workspace selector to scope activity feed, agent grid, and dispatch commands

### Repo Access
- Daemon needs all portfolio repos cloned locally
- Configurable workspace root (e.g., `C:/Users/56bad/PycharmProjects/BPSAI_Workspace/`)
- Target repo in dispatch message must exist under workspace root

### Execution
- Uses Claude Code CLI: `claude -p "<prompt>" --agent <agent-type>`
- Inherits the framework's dispatch engine patterns (engine/dispatch.py)
- PairCoder repos get contained-auto enforcement
- Non-PairCoder repos get --allowedTools enforcement
- Process timeout configurable (default: 30 minutes)

### Security
- Credential scrubbing on output before posting results to A2A
- No unrestricted mode — all dispatches go through enforcement
- Daemon runs as the local user — inherits their git credentials, API keys, etc.

## Sprint Backlog (~30cx)

### CD1.1: Daemon scaffold + config (10cx)
- CLI entry point: `bpsai-computer daemon --operator mike --workspace bpsai`
- Config file: `~/.bpsai-computer/config.yaml`:
  ```yaml
  operator: mike
  workspace: bpsai
  workspace_root: C:/Users/56bad/PycharmProjects/BPSAI_Workspace
  a2a_url: https://a2a.paircoder.ai
  poll_interval: 5
  process_timeout: 1800  # 30 minutes
  ```
- Graceful shutdown on SIGINT/SIGTERM

### CD1.2: A2A polling + dispatch execution (15cx)
- Poll loop: GET /messages?type=dispatch&operator=<id>&workspace=<id>&unacknowledged_only=true
- Parse dispatch message: extract agent, target repo, prompt
- Launch Claude Code subprocess
- Ack message on dispatch start
- Post dispatch-result on completion (stdout/stderr captured, credential-scrubbed)
- Error handling: process timeout, non-zero exit, missing repo

### CD1.3: Integration test + docs (5cx)
- Test: mock A2A server, verify poll → dispatch → ack → result flow
- Test: operator filtering (daemon ignores messages for other operators)
- README with setup instructions
- Example config file

## Relationship to Computer₀ Full Vision

The daemon is Computer₀ Phase 1 — the EXECUTE phase only. The full Computer₀ vision (D-023) includes:

| Phase | What | Status |
|-------|------|--------|
| SENSE | Observe channels, git activity, telemetry | Framework hooks shipped (G2.7) |
| PLAN | Autonomous sprint planning | Backlog parser + deliverer shipped (G3) |
| EXECUTE | **Dispatch daemon (this plan)** | **This deliverable** |
| ENFORCE | Contained-auto enforcement | Framework shipped (G2.5) |
| LEARN | Update decision journal, hypothesis confidence | Framework hooks shipped (G2.7) |

The daemon is the minimum viable Computer₀ — it executes dispatched work. The autonomous loop (Computer₀ decides what to dispatch on its own) comes after the Command Center validates the human-directed dispatch flow.

## Migration Roadmap: Framework → Computer

Computer consumes the framework as a library. Orchestration *behavior* migrates incrementally from framework to Computer. Orchestration *abstractions* stay in framework.

### What Stays in Framework (abstractions)
- `engine/orchestration/models.py` — Phase, TickResult, PhaseResult, TickContext
- `engine/orchestration/loop_runner.py` — reusable loop primitive
- `engine/orchestration/phase_registry.py` — PhaseHook protocol
- `engine/dispatch.py` — dispatch abstraction
- `engine/enforcement.py` — enforcement ABCs
- `engine/llm_adapters.py` — LLM call protocols

### What Migrates to Computer (behavior)
- `engine/navigator_orchestrator.py` — plan+dispatch flow (IS Computer's main loop)
- `engine/backlog_parser.py` — sprint planning
- `engine/next_sprint_author.py` — sprint authoring
- `engine/status_updater.py` — portfolio state management
- `engine/review_automation.py` — dispatch decisions
- `docs/portfolio/*` — portfolio docs belong where Computer runs

### Migration Phases
1. **Phase 1 (now, 30cx):** Daemon only. No migration. Framework untouched.
2. **Phase 2 (~50cx):** Portfolio docs move to Computer repo. Computer reads/updates its own `portfolio/status.yaml`.
3. **Phase 3 (~80cx):** Orchestration behavior moves. Computer imports framework abstractions but owns the planning/dispatch/review logic.
4. **Phase 4:** Computer becomes workspace-portable. `pip install bpsai-computer`, configure workspace root, run daemon. Any portfolio, not just BPS.

### Multi-Workspace Portability

Computer is not BPS-specific. It's a workspace orchestrator deployable to any portfolio:

```
BPS AI Workspace/
├── paircoder/, paircoder_api/, bpsai-framework/, ...
├── bpsai-computer/          ← Computer₀ for BPS
│   ├── portfolio/           ← BPS status.yaml, decisions, priorities
│   └── config.yaml          ← workspace=bpsai, repos list

DanHil AP Workspace/
├── ap-frontend/, ap-api/, ap-functions/
├── bpsai-computer/          ← Computer₀ for DanHil
│   ├── portfolio/           ← DanHil status.yaml, decisions
│   └── config.yaml          ← workspace=danhil, repos list
```

Same code, different config. Portfolio docs are workspace-specific, not framework-specific. Customer repos don't need the framework installed — Computer observes using PairCoder's existing `.paircoder/context/` files.
