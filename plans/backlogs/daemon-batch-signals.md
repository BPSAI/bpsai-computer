# Daemon Batch Signal Push — DIF.3

> **Budget:** ~5cx
> **Repo:** bpsai-computer
> **Sprint ID:** DBS
> **Depends on:** DIF.2 (batch endpoint deployed on A2A)

---

## Context

The A2A signals endpoint now supports `POST /signals/batch` accepting `{"operator": str, "repo": str, "signals": [...]}`. The daemon collectors currently POST to `/signals` (single signal endpoint) with the batch format, causing 422. Update all collectors to use `/signals/batch`.

---

### Phase 1: Collector Update

### DBS.1 — Update collectors to use /signals/batch | Cx: 5 | P0

**Description:** Update SignalPusher, GitSummaryCollector, and CISummaryCollector to POST to `/signals/batch` instead of `/signals`. Generate deterministic `signal_id` client-side for idempotency. Format timestamps as canonical ISO 8601 UTC.

**Files:**
- `src/computer/signal_pusher.py` — change URL to `/signals/batch`, ensure batch payload matches endpoint schema
- `src/computer/git_collector.py` — change URL to `/signals/batch`, generate `signal_id` as `git_summary_{repo}_{head_sha}`
- `src/computer/ci_collector.py` — change URL to `/signals/batch`, generate `signal_id` as `ci_summary_{repo}_{timestamp_hash}`

**AC:**
- [ ] All three collectors POST to `/signals/batch`
- [ ] Payload format: `{"operator": str, "repo": str, "signals": [{"signal_type": str, "severity": str, "timestamp": str, "payload": dict, "signal_id": str}]}`
- [ ] `signal_id` generated deterministically per signal for dedup
- [ ] Timestamps formatted as `YYYY-MM-DDTHH:MM:SSZ` (canonical UTC, no microseconds)
- [ ] Fire-and-forget preserved — batch failure logged, doesn't block daemon
- [ ] Tests updated to verify new URL and payload format

---

## Summary

| Task | Title | Cx | Priority |
|------|-------|----|----------|
| DBS.1 | Update collectors to /signals/batch | 5 | P0 |
| **Total** | | **5** | |
