# CD3: Daemon JWT + Operator Identity

> **Budget:** ~25cx
> **Primary repo:** bpsai-computer
> **Cross-repo:** bpsai-support (Function App + FastAPI), bpsai-command-center
> **Sprint ID:** CD3
> **Depends on:** Unified Auth (shipped), CD1+CD2 (shipped)
> **Design ref:** bpsai-framework/docs/design/computer-daemon-plan.md

---

## Context

The dispatch daemon (CD1+CD2) is built and can execute dispatches, stream output, and manage session lifecycle. But it authenticates with test credentials — no real JWT, no operator routing.

This sprint wires real identity into the daemon:
- A new `operator_id` field on user profiles provides a stable, human-readable routing key
- The portal JWT carries it as the `operator` claim
- The daemon polls A2A for dispatches tagged with its operator
- CC displays the operator ID so users know their routing identity

**Operator ID format:** `{first_name_lower}-{random_8_chars}` (e.g., `mike-a3k9x2m1`). Auto-generated on first login, unique, passes A2A regex `^[a-zA-Z0-9_-]{1,64}$`.

---

### Phase 1: Operator Identity (bpsai-support)

### CD3.1 — Add operator_id column to user profile | Cx: 5 | P0 | Repo: bpsai-support (Function App)

**Description:** Add `operator_id` column to the user model in the Function App. Auto-generate on user creation as `{first_name_lower}-{random_8_chars}`. Must be unique.

**AC:**
- [ ] `operator_id` column added to user model (String, unique, nullable=True initially)
- [ ] Auto-generation logic: `first_name.lower() + "-" + secrets.token_hex(4)` (8 hex chars)
- [ ] Migration adds column
- [ ] If user has no first name, fall back to `user-{random_8_chars}`
- [ ] Unique constraint prevents collisions (regenerate on conflict)
- [ ] GET user endpoint returns `operator_id`
- [ ] Tests: generation format, uniqueness, fallback

### CD3.2 — Include operator claim in portal JWT | Cx: 5 | P0 | Repo: bpsai-support (FastAPI)

**Description:** When minting portal access tokens, include the `operator` claim from the user's `operator_id`. A2A already reads `payload.get("operator")` with fallback to `sub`.

**Depends on:** CD3.1

**AC:**
- [ ] `mint_access_token` in `portal_session.py` adds `"operator": user_data["operator_id"]` to JWT claims
- [ ] Claim only included when `operator_id` is not None (backward compat for users without one)
- [ ] `validate_portal_token` extracts and returns `operator` claim
- [ ] Tests: JWT contains operator claim, round-trip validation

---

### Phase 2: Visibility (bpsai-command-center)

### CD3.3 — Show operator ID in Command Center | Cx: 5 | P1 | Repo: bpsai-command-center

**Description:** Display the user's operator ID in CC so they know what to configure in their daemon. Read-only display in user profile or settings area.

**Depends on:** CD3.2

**AC:**
- [ ] Operator ID displayed in user profile/settings area of CC
- [ ] Value read from portal JWT `operator` claim (already available after login)
- [ ] Copy-to-clipboard button for easy config setup
- [ ] If no operator ID (legacy user), show "Not assigned — contact admin"

---

### Phase 3: Daemon Auth (bpsai-computer)

### CD3.4 — Auto-discover license_id from license.json | Cx: 5 | P0 | Repo: bpsai-computer

**Description:** Remove `license_id` as a required config field. Instead, find and read `~/.paircoder/license.json` (same search order as PairCoder CLI). Extract `payload.license_id` for use in `TokenManager`.

**Search order (matches CLI):**
1. `PAIRCODER_LICENSE` env var (if set)
2. `~/.paircoder/license.json`
3. `./.paircoder/license.json` (cwd)

**AC:**
- [ ] `config.py`: `license_id` field defaults to None (no longer required)
- [ ] New `license_discovery.py` module: finds license.json, reads payload, returns license_id
- [ ] `daemon.py` startup: if `license_id` not in config, auto-discover from license file
- [ ] Clear error message if no license found: "No license found. Run: bpsai-pair license install <file>"
- [ ] Config file `license_id` overrides auto-discovery (for cloud VMs with no CLI installed)
- [ ] Tests: discovery from home dir, env var override, config override, missing file error

### CD3.5 — End-to-end JWT auth verification | Cx: 5 | P0 | Repo: bpsai-computer

**Description:** Start the daemon with real credentials and verify the full dispatch loop: JWT auth → poll A2A → receive dispatch → execute → post result.

**Depends on:** CD3.1, CD3.2, CD3.4

**AC:**
- [ ] Daemon starts with `operator` from config + auto-discovered `license_id`
- [ ] `TokenManager` successfully obtains JWT from `api.paircoder.ai/api/v1/auth/operator-token`
- [ ] A2A accepts the JWT (200 on poll, not 401)
- [ ] Test dispatch from CC reaches daemon (operator routing matches)
- [ ] Dispatch result posted back to A2A with valid JWT
- [ ] Integration test: mock A2A verifies JWT is present and valid on all requests
- [ ] Document setup in README: install license, create config with operator + workspace, run daemon

---

## Summary

| Task | Title | Cx | Priority | Repo |
|------|-------|----|----------|------|
| CD3.1 | Add operator_id to user profile | 5 | P0 | bpsai-support (Function App) |
| CD3.2 | Operator claim in portal JWT | 5 | P0 | bpsai-support (FastAPI) |
| CD3.3 | Show operator ID in CC | 5 | P1 | bpsai-command-center |
| CD3.4 | Auto-discover license_id | 5 | P0 | bpsai-computer |
| CD3.5 | End-to-end JWT verification | 5 | P0 | bpsai-computer |
| **Total** | | **25** | | 4 repos |

## Execution Order

```
Phase 1 (Identity — bpsai-support):
  CD3.1 (operator_id column) → CD3.2 (JWT claim)

Phase 2 (Visibility — CC, can parallel with Phase 3):
  CD3.3 (show operator ID in CC)

Phase 3 (Daemon — bpsai-computer):
  CD3.4 (license auto-discovery) → CD3.5 (end-to-end verification)

CD3.5 depends on CD3.1 + CD3.2 + CD3.4 (all must be done before e2e test)
```

## Onboarding Checklist (after CD3 ships)

For each developer running a daemon:

1. Install PairCoder license: `bpsai-pair license install <file>`
2. Log into Command Center — note your **operator ID** (e.g., `mike-a3k9x2m1`)
3. Create `~/.bpsai-computer/config.yaml`:
   ```yaml
   operator: mike-a3k9x2m1
   workspace: bpsai
   workspace_root: /path/to/BPSAIWorkspace
   ```
4. Start daemon: `bpsai-computer daemon`
