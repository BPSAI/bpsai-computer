# CD2 Post-Review Fixes — Security + Quality

> **Budget:** ~25cx
> **Depends on:** CD2 sprint complete (92 tests), review + security audit findings
> **Repo:** bpsai-computer
> **Sprint ID:** CD2-FIX

---

## Context

CD2 shipped streaming, lifecycle, and resume (92 tests). Review and security audit found 5 critical/P0 issues and 6 high/P1 issues. The critical concern is that SEV-003 (operator bypass) + SEV-004 (path traversal) + `--dangerously-skip-permissions` creates an end-to-end exploit path for anyone who can post to the A2A feed.

---

### CDF.1 — Security: Input Validation + Operator Fix | Cx: 10 | P0

**Description:** Fix the three security findings that combine into the exploit path, plus session_id validation.

**Findings addressed:** SEV-002, SEV-003, SEV-004

**AC:**
- [ ] Operator check inverted — reject when `msg_operator != self.config.operator` (missing field = rejected, not bypassed)
- [ ] Path traversal guard — `repo_dir.resolve()` must be under `workspace_root.resolve()`, reject otherwise
- [ ] `session_id` validated against `^[a-zA-Z0-9\-_]{1,256}$` in `parse_resume`, reject non-matching
- [ ] `target` validated against `^[a-zA-Z0-9\-_.]{1,128}$` in both `parse_dispatch` and `parse_resume`
- [ ] Test: resume with missing operator field → rejected
- [ ] Test: resume with path traversal target (`../../../etc`) → rejected
- [ ] Test: resume with invalid session_id (`abc --output /tmp/pwned`) → rejected
- [ ] Test: dispatch with path traversal target → rejected

### CDF.2 — Security: Credential Scrubbing Gaps | Cx: 5 | P0

**Description:** Fix raw stdout buffer leak and expand scrubber patterns.

**Findings addressed:** SEV-001, SEV-006

**AC:**
- [ ] `_stdout_lines` stores scrubbed content (or clear buffer after `extract_session_id`)
- [ ] Scrubber patterns added: GitHub PATs (`ghp_`, `github_pat_`), GCP OAuth (`ya29.`), OpenAI keys (`sk-`), URL-embedded credentials (`://user:pass@`)
- [ ] `extract_session_id` regex capped at 256 chars (SEV-010)
- [ ] Test: stdout_lines does not contain raw credentials
- [ ] Test: each new scrubber pattern catches its target

### CDF.3 — Quality: Lifecycle Error Handling + Streamer Session ID | Cx: 5 | P0

**Description:** Fix the two P0 code quality issues from the reviewer.

**Findings addressed:** REV-P0-1, REV-P0-2

**AC:**
- [ ] `OutputStreamer` initialized with `session_id` (not `message_id`) in `daemon.py`
- [ ] `_execute_with_lifecycle` wrapped in try/except so `post_started` failure doesn't crash the dispatch pipeline — returns a failure DispatchResult instead
- [ ] Return type annotation added: `-> tuple[str, DispatchResult]`
- [ ] Test: lifecycle posting failure during startup doesn't crash daemon
- [ ] Test: streamer session_id matches lifecycle session_id

### CDF.4 — Quality: A2A Client + Daemon Hardening | Cx: 5 | P1

**Description:** Fix the P1 quality and security issues.

**Findings addressed:** SEV-007, REV-P1-1, REV-P1-2, REV-P1-3

**AC:**
- [ ] A2A client uses shared `httpx.AsyncClient` instance with explicit timeouts (`connect=5s`, `read=10s`)
- [ ] A2A client has `close()` method for cleanup, called on daemon shutdown
- [ ] Startup warning if `a2a_url` is not HTTPS
- [ ] `_processed_ids` bounded — use `collections.OrderedDict` or deque with max 10,000 entries
- [ ] `parse_dispatch` separates `JSONDecodeError` (plain text fallback) from `KeyError` (malformed, log warning)
- [ ] Remove dead `required` variable in `config.py`
- [ ] Backpressure in streamer logs warning when lines are dropped
- [ ] Test: A2A client reuses connection
- [ ] Test: processed_ids evicts old entries at limit
- [ ] Test: malformed JSON dispatch logs warning

---

## Summary

| Task | Title | Cx | Priority | Phase |
|------|-------|----|----------|-------|
| CDF.1 | Security: Input Validation + Operator Fix | 10 | P0 | 1 |
| CDF.2 | Security: Credential Scrubbing Gaps | 5 | P0 | 1 |
| CDF.3 | Quality: Lifecycle Error Handling + Streamer Session ID | 5 | P0 | 1 |
| CDF.4 | Quality: A2A Client + Daemon Hardening | 5 | P1 | 1 |
| **Total** | | **25** | | |

### Execution Order

```
Phase 1 (all parallel — no dependencies):
  CDF.1 (input validation — highest security priority)
  CDF.2 (scrubbing gaps)
  CDF.3 (lifecycle + streamer fixes)
  CDF.4 (client + daemon hardening)
```

---

## Validation

After this sprint:
1. Resume with missing operator → rejected (not executed)
2. Dispatch/resume with `../` target → rejected
3. Resume with `session_id` containing spaces/flags → rejected
4. `_stdout_lines` contains no raw credentials after streaming
5. `post_started` failure → dispatch continues, doesn't crash
6. Streamer output messages have correct session_id (matching lifecycle)
7. Daemon runs 24h+ without unbounded memory growth
