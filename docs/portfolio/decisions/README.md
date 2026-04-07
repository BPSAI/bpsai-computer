# Portfolio Decisions

Structured records of strategic and architectural decisions. Each file captures the decision, reasoning, alternatives considered, and date.

These are extracted from the "What NOT to Lose" section of the portfolio plan. The plan retains the items as brief pointers; the full context lives here.

## Index

| ID | Decision | Date | Source |
|----|----------|------|--------|
| D-001 | 80% base agent is the product | 2026-03-08 | David/Mike |
| D-002 | A2A server migrates to standalone repo | 2026-03-08, revised 2026-03-17 | David/Mike |
| D-003 | PM abstraction stops at Trello | 2026-03-08 | David/Mike |
| D-004 | Framework is portfolio-level SoT | 2026-03-08 | David/Mike |
| D-005 | Signal -> route -> dispatch -> compose | 2026-03-08 | Architecture |
| D-006 | Enforcement runs locally, API is opt-in telemetry | 2026-03-09 | Architecture |
| D-007 | Two hats are recursive, not competing | 2026-03-09 | David/Mike |
| D-008 | Computer hierarchy is L3 recursive | 2026-03-12 | Mike/David |
| D-009 | Remote Control integration (Framework #5) | 2026-03-18 | David/Mike |
| D-010 | Enterprise data tier security contract | 2026-03-20 | Issue #10 |
| D-011 | Sprint naming convention (repo prefix) | 2026-03-25 | Convention |
| D-012 | Skill discovery via telemetry, not static libraries | 2026-03-12 | Competitive analysis |
| D-013 | CNS consumes PairCoder recursively — one enforcement track, two scales | 2026-03-25 | David/Computer |
| D-014 | PM Architecture: A2A over embedding | 2026-03-25 | CLI backlog.md |
| D-015 | Gate hooks in observation mode — data collection before thresholds | 2026-03-25 | CLI autonomy self-review |
| D-016 | Content safety two-tier model | 2026-03-25 | API content_safety.md |
| D-017 | Engagement-first cognitive loop precedent | 2026-03-25 | Bot S32 |
| D-018 | A2A service topology — framework, transport, consumers | 2026-03-25 | A2A project.md |
| D-019 | Effort values: S/M/L only (no XS or XL) | 2026-03-25 | CLI board conventions |
| D-020 | PairCoder Bot → Lounge Resident #1 and framework learning layer | 2026-03-25 | David/Computer |
| D-021 | Twins serve three roles: content, Lounge perspective, intent preservation | 2026-03-26 | David/Computer |
| D-022 | Computer must consume PairCoder's planning enforcement — no vibes-based planning | 2026-03-26 | David/Computer |
| D-023 | Agent foundry: layered packages (core/lounge/enforce), extract+refactor, LLM-agnostic | 2026-03-29 | Mike |
| D-024 | Dispatch enforcement: PairCoder repos → contained-auto, non-PairCoder → allowedTools | 2026-03-27 | David/Computer |
| D-025 | Intelligence scoring: SQLite profiles, agents don't see own scores, centralized now | 2026-03-29 | Mike |
| D-026 | Lounge deploys as A2A module, extract to separate service later | 2026-03-29 | Mike |
| D-027 | First foundry agent: IT Operations (Vaivora), not Unity specialist | 2026-03-29 | Mike |
| D-028 | Multi-plan exploration: hybrid novelty + complexity thresholds, both configurable | 2026-03-29 | Mike |
| D-029 | Bridge: Unity engine, separate ships per operator (NCC-1701/1701-D), shared universe via A2A | 2026-03-29 | Mike |
| D-030 | Command Center: separate project, progressive build (web → tablet → stations → Vision Pro) | 2026-03-29 | Mike |
| D-031 | Agent degradation: autonomous prompt tweaks, HITL for authority changes | 2026-03-29 | Mike |
| D-032 | Tenant isolation: database-level separation per D-025 pattern | 2026-03-29 | Mike |
| D-033 | Transport/intelligence separation in A2A: src/channels/ vs src/lounge/ — extraction readiness | 2026-03-29 | Mike |
