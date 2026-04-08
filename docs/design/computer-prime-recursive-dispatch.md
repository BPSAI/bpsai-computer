# Computer Prime: Recursive Dispatch Architecture

> **Status:** Design capture -- David + Computer session, 2026-04-01
> **Context:** Emerged from engage branch creation debate, organizational knowledge gap, and operator lane isolation
> **Related:** D-013 (recursive consumption), D-023 (Computer as standalone package), recursive-enforcement-architecture.md

---

## Core Principle

Computer Prime is not a repo. It is the observation layer from which the founders (David, Mike) direct Computer 1-3, Metis, and the fleet. The framework repo is the proving ground where the CNS machinery (SENSE/LEARN/signals/ideas/hypotheses/dispatch) is built and tested. Computer Prime consumes this framework but does not live inside it.

Computer Prime's output is **backlogs**, not code. It writes backlogs for operators to consume. Operators run engage. Engage spawns navigators. Navigators dispatch drivers. The pattern is identical at every scale.

---

## The Hierarchy

Computer Prime does not manage repos. It manages **domain Computers**. Each domain Computer manages a bounded set of repos within its domain. This keeps context load bounded at every level -- Prime holds the dependency graph and domain-level status, not every file in every repo.

```
Computer Prime (David + Mike + framework observation layer)
  │
  │ sees: domain Computers, dependency graph, portfolio status
  │ does: writes backlogs FOR domain Computers, sequences cross-domain work
  │ does NOT: manage repos directly, create branches, dispatch drivers
  │ interface: conversation (today), Command Center (tomorrow)
  │
  ├── Computer-Foundry (agents, lounge, mythology)
  │     │ sees: its repos, agent lifecycle, foundry state
  │     │ does: receives backlogs from Prime, delivers to repo navigators,
  │     │       reviews domain PRs, passes signal back to Prime
  │     │ repos:
  │     │   ├── bpsai-agents
  │     │   ├── agentlounge.ai
  │     │   └── (future agent repos)
  │     │
  │     └── Project Navigators (per repo)
  │           │ does: /pc-plan, branch creation, engage, dispatch drivers
  │           └── Drivers (per task)
  │
  ├── Computer-Command (orchestration, visualization, signal)
  │     │ sees: its repos, dispatch state, signal flow
  │     │ repos:
  │     │   ├── bpsai-command-center
  │     │   ├── bpsai-computer (the daemon)
  │     │   └── bpsai-a2a
  │     │
  │     └── Project Navigators → Drivers
  │
  ├── Computer-Enforce (enforcement, CLI, framework)
  │     │ sees: its repos, enforcement state, CLI telemetry
  │     │ repos:
  │     │   ├── paircoder (CLI)
  │     │   ├── bpsai-framework
  │     │   ├── paircoder_api
  │     │   └── paircoder_bot
  │     │
  │     └── Project Navigators → Drivers
  │
  └── (future domain Computers as product grows)
```

### Three Tiers, Not Two

The critical insight: Prime → domain Computers → navigators. Not Prime → navigators. Each tier has bounded context:

| Tier | Manages | Context Load | Example |
|------|---------|-------------|---------|
| **Prime** | 3 domain Computers | Domain status, dependency graph, portfolio | "UA sprint blocks Metis fleet visibility" |
| **Domain Computer** | 3-5 repos | Repo state, PRs, signals within domain | "bpsai-agents needs AF2, agent-core is stable" |
| **Navigator** | 1 repo | Files, tests, branches, tasks | "scanner.py needs refactor, 42 tests" |

Prime doesn't need to know what's in `scanner.py`. Computer-Foundry does. Computer-Foundry doesn't need to know about the CLI's intent gate. Computer-Enforce does. Context stays bounded at each level.

### The Flow

```
Prime writes backlog → delivers to Computer-Foundry
Computer-Foundry delivers to bpsai-agents Navigator
Navigator creates branch, runs /pc-plan, dispatches engage
Drivers write code, commit
Navigator creates PR, dispatches review
Computer-Foundry reviews, merges to dev
Computer-Foundry passes signal to Prime (sprint complete, N tests, M findings)
Prime updates dependency graph, plans next move
```

### Who Does What

| Actor | Writes backlogs | Delivers to | Creates branches | Dispatches drivers | Reviews PRs | Sees |
|-------|----------------|-------------|------------------|--------------------|-------------|------|
| Prime | For domain Computers | Domain Computers | No | No | Final (cross-domain) | All domains |
| Domain Computer | For repo navigators | Navigators | No | No | Domain PRs | Its repos |
| Navigator | No (receives) | Drivers | Yes (/pc-plan) | Yes (engage) | Automated | Single repo |
| Driver | No | N/A | No | No | No | Task scope |

### Why This Matters Now

This session proved the context ceiling is real. 24+ hours, 17 repos, 4 sprints, 8 audit cycles. Prime (this session) is losing details from 6 hours ago. That's not a bug -- it's the signal that domain Computers need to own their context. Computer-Foundry should track what happened in bpsai-agents so Prime doesn't have to.

---

## The CLI Trust Gradient

CLI commands exist on a spectrum from maximum constraint to maximum autonomy. Each level adds freedom while maintaining enforcement.

```
Most constrained ─────────────────────────────────── Most autonomous

/start-task     /pc-plan      engage (repo)      engage (cross-repo)
    │               │              │                     │
 single task    sprint plan    full sprint          multi-repo
 max enforce    with gates     autonomous           orchestrated
 per-task AC    estimation     within one repo      per-repo backlogs
 verification   model select                        sequential engage
                branch create
```

### /start-task and /pc-plan: Training Wheels

These commands are the most constrained, most enforced, most grounded. They operate within a single repo with maximum guardrails:

- Task-level acceptance criteria verification
- Architecture gate checks
- Budget enforcement
- Model routing by complexity
- Per-task telemetry emission

They are training wheels for the system AND for operators learning the workflow. Kevin uses engage (one level up) because he's past the training wheel stage for his repos but stays in single-repo isolation by design.

### engage: The Universal Dispatch Mechanism

Engage is the dispatch command at every level. It doesn't matter who initiates it:

- **Human types it:** `bpsai-pair engage backlog.md` in terminal
- **Navigator runs it headlessly:** spawned by Computer Prime's backlog delivery
- **Daemon triggers it:** Computer₀ receives dispatch message from A2A, runs engage locally
- **CI/CD invokes it:** GitHub Actions runs engage on schedule or trigger

Same command. Same enforcement. Same branch/PR/review pipeline. The trust gradient is **who initiates**, not **what runs**.

### The Engage Contract

When engage runs in any context:

1. Must be on a feature branch (branch guard enforces)
2. Navigator parses backlog, creates plan, estimates complexity
3. Drivers dispatched per task with appropriate model routing
4. Each task committed after completion (commit verification signal if empty)
5. PR created targeting dev (or configured base)
6. Review agents dispatched (reviewer + security-auditor)
7. Signals emitted throughout (task outcomes, duration, gate blocks)

This contract holds whether Kevin runs it manually in bpsai-amunet or Computer₀ triggers it via A2A message in bpsai-computer.

---

## Computer Prime's Role

### Today (HITL -- Human In The Loop)

David and Mike are Computer Prime. They:

1. **Observe** via framework signals, hypotheses, ideas, Metis briefings
2. **Plan** by writing backlogs (manually or via /draft-backlog)
3. **Assign** by delivering backlogs to target repos
4. **Sequence** by knowing dependency order (UA sprint before Metis fleet visibility)
5. **Isolate** by keeping operators in their lane (Kevin stays in Amunet/Iris, Mike handles auth/CC/computer, David handles framework/CLI)
6. **Review** final PRs before merge to dev/main

### Tomorrow (Command Center approval)

Computer Prime proposes backlogs in Command Center. David and Mike approve or redirect. The approval rate becomes the trust metric:

- High approval rate → Computer Prime's judgment is calibrated
- Low approval rate → backlogs need more context or different priorities
- Override rate drops → more autonomy granted (trust slider)

### Eventually (autonomous routine, human strategy)

Computer Prime dispatches routine work autonomously. Humans handle:

- Strategy and architecture decisions
- PR review (the one gate that never moves)
- Priority changes and course corrections
- Novel work that hasn't been done before

---

## The Framework's Role

The framework repo (`bpsai-framework`) is the **proving ground** for Computer Prime's brain. It contains:

- **Orchestration loop:** SENSE → PLAN → DISPATCH → ENFORCE → LEARN
- **Data stores:** SignalStore, HypothesisBacklog, IdeaStore, DecisionJournal
- **Pattern detectors:** Failure concentration, blind spots, stale hypotheses
- **Dispatch infrastructure:** LoopRunner, PhaseHooks, EventQueue, CadenceResolver
- **Enforcement:** Intent gate, approval gate, capability gate

This machinery is developed and tested here. Computer Prime consumes it. Computer 1-3 consume it (via PairCoder CLI which depends on the framework). But the framework itself does not dispatch into other repos. It builds the patterns that enable dispatch.

### What Gets Extracted

Per D-023, the framework is a library. Behavior migrates to consumers:

| Stays in Framework | Migrates to Computer (bpsai-computer) | Migrates to CLI (paircoder) |
|-------------------|--------------------------------------|----------------------------|
| Phase enum, LoopRunner | Navigator orchestration | /pc-plan, /start-task |
| PhaseHook protocol | Backlog parsing, sprint authoring | engage command |
| SignalStore, IdeaStore | Status updater, review automation | Intent gate, frustration detector |
| Pattern detectors | Portfolio docs, workspace state | Telemetry, signal emitter |
| Hypothesis lifecycle | Dispatch routing, operator assignment | Task lifecycle hooks |

---

## Operator Isolation (Lane Keeping)

Computer Prime's most important job is keeping operators productive without conflicts:

### Current State

| Operator | Repos | Access Level | Why |
|----------|-------|-------------|-----|
| Kevin | bpsai-amunet, bpsai-iris | Repo-specific, no framework | Focused execution, maximum signal, no cross-repo risk |
| Mike | bpsai-support, bpsai-command-center, bpsai-a2a, bpsai-computer, bpsai-agents | Full access, auth/infra focus | Building the platform layer |
| David | bpsai-framework, paircoder, paircoder_api, paircoder_bot | Full access, framework/CLI focus | Building the brain + enforcement |

### How Prime Prevents Conflicts

1. **Backlog scoping:** Prime writes backlogs that don't overlap. Kevin's Amunet S2 touches `scanners/` only. David's CLI S45 touches `intent_gate/` only. No intersection.

2. **Dependency sequencing:** Mike's UA sprint must finish before Metis fleet visibility can start. Prime knows this and doesn't write the Metis backlog until UA ships.

3. **Branch awareness:** via daemon, Prime can see who is on which branch in which repo. If Kevin is on `engage/amunet-sprint-2` modifying `workspace.py`, Prime won't assign David work that touches the same file.

4. **Conflict detection:** if two operators DO need to touch the same repo, Prime writes non-overlapping backlogs (different files/modules) or sequences them (one finishes, then the other starts).

---

## Graduation Path

### Phase 1: Prove the Loop (current)

- Framework builds SENSE/LEARN/dispatch machinery
- Engage command handles single-repo sprints
- Operators run engage manually
- Computer Prime = David + Mike in conversation
- Signal: does the machinery work? (IdeaStore smoke test, commit verification, frustration detection)

### Phase 2: Connect the Pipes

- Daemon pushes signals to A2A (blocked on UA sprint)
- Metis reads from A2A instead of filesystem
- Ideas flow cross-repo
- Computer Prime = David + Mike in Command Center
- Signal: does cross-repo visibility work? (Metis sees all operators' signals)

### Phase 3: Prime Proposes

- Computer Prime proposes backlogs in Command Center
- Operators approve and run engage
- Trust slider: approval rate measured
- Signal: how often do operators override Prime's proposals?

### Phase 4: Autonomous Routine

- Computer Prime dispatches routine backlogs without approval
- Operators handle strategy loop only
- PR review remains human (the gate that never moves)
- Signal: anomaly rate, override rate, quality metrics

Each phase is self-contained. Each phase proves the trust required for the next. No phase is skipped.

---

## Open Questions

1. **Kevin's graduation:** When does Kevin get framework access? When his repos are stable and the engage pipeline is validated. Not before.

2. **Multi-operator engage:** When two operators need to work in the same repo simultaneously, how does Prime coordinate? Branch isolation per operator? Sequential scheduling?

3. **Prime's memory:** Today, Prime's memory is David's `.claude/` memory + Mike's `.claude/` memory + the IdeaStore. When Prime moves to Command Center, where does institutional memory live? A2A signals? A dedicated knowledge store?

4. **Backlog format evolution:** Today backlogs are markdown files. Should they become structured YAML (machine-parseable by engage) with a markdown rendering? This would let Prime generate backlogs programmatically and engage consume them without parsing heuristics.
