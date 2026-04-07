# A2A-S2 Deployment Handoff

> **Date:** 2026-03-27
> **From:** Framework session (desktop)
> **To:** Next session (laptop)
> **Goal:** Deploy bpsai-a2a to Azure Container Apps, mirroring the paircoder_api pattern
> **Status:** COMPLETE — deployed 2026-03-27, health check passing at https://a2a.paircoder.ai/health

---

## What's Done

- [x] bpsai-a2a code complete (A2A-S1, 109 tests, 7 skills)
- [x] Dockerfile exists and builds
- [x] docker-compose.yml for local dev (PostgreSQL 16 + FastAPI on port 8001)
- [x] CI workflow exists (lint + test + docker build)
- [x] D-025 decided: shared PostgreSQL server, separate databases, migration path defined
- [x] Deployment pattern audit complete (see `deployment-patterns.md`)
- [x] `api-removal-guide.md` documents the full consumer cutover plan
- [x] Cross-repo workspace permissions fixed (`additionalDirectories` in user settings)

## What Needs to Happen

### Step 1: Azure Resources

Provision in `rg-paircoder-cus-prod`:

```bash
# Create Container App (check Azure Portal for exact environment name)
az containerapp create \
  --name ca-bpsai-a2a-cus-prod \
  --resource-group rg-paircoder-cus-prod \
  --environment <managed-environment-name> \
  --image ghcr.io/bpsai/bpsai-a2a:latest \
  --target-port 8001 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1

# Create database on existing PostgreSQL server
# Connect to existing server, run:
# CREATE DATABASE bpsai_a2a;
```

**Find these values in Azure Portal:**
- The managed environment name (look at the existing API container app's environment)
- The PostgreSQL server hostname (check API container app's DATABASE_URL env var)

### Step 2: Environment Variables on Container App

```bash
az containerapp update \
  --name ca-bpsai-a2a-cus-prod \
  --resource-group rg-paircoder-cus-prod \
  --set-env-vars \
    DATABASE_URL="postgresql+asyncpg://<user>:<pass>@<host>:5432/bpsai_a2a" \
    API_BASE_URL="https://api.paircoder.ai" \
    A2A_BASE_URL="https://a2a.paircoder.ai"
```

### Step 3: DNS

Add CNAME record in your domain registrar:
```
a2a.paircoder.ai → <container-app-fqdn>.azurecontainerapps.io
```

Then configure custom domain on the Container App (Portal or CLI).

### Step 4: GitHub Actions Workflow

Create `bpsai-a2a/.github/workflows/deploy.yml` — adapt from the API's workflow:

```yaml
env:
  IMAGE_NAME: ghcr.io/bpsai/bpsai-a2a
  CONTAINER_APP: ca-bpsai-a2a-cus-prod
  RESOURCE_GROUP: rg-paircoder-cus-prod
```

Changes from API template:
- Image name: `bpsai-a2a` not `paircoder-api`
- Container app name: `ca-bpsai-a2a-cus-prod`
- Smoke test URL: `https://a2a.paircoder.ai/health` (or whatever health endpoint exists)
- Port: 8001 not 8000

### Step 5: GitHub Secrets

Add to bpsai-a2a repo settings → Secrets and variables → Actions:
- `CABPSAIA2ACUSPROD_AZURE_CLIENT_ID` (create new service principal or reuse API's)
- `CABPSAIA2ACUSPROD_AZURE_TENANT_ID`
- `CABPSAIA2ACUSPROD_AZURE_SUBSCRIPTION_ID`
- `GHCR_PAT` (same as API repo)

### Step 6: Key Vault Firewall

The deploy workflow syncs outbound IPs to Key Vault. Copy that step from the API workflow if A2A needs Key Vault access. If A2A only needs the PostgreSQL connection string (passed via env var), this step may not be needed.

### Step 7: Verify

```bash
curl https://a2a.paircoder.ai/health
```

### Step 8: Consumer Cutover (After 1+ Week Stable)

Per `bpsai-a2a/docs/api-removal-guide.md`:

| Consumer | Old URL | New URL |
|----------|---------|---------|
| Bot pushState | `api.paircoder.ai/a2a` | `a2a.paircoder.ai/a2a` |
| CLI platform-check | `api.paircoder.ai/a2a` | `a2a.paircoder.ai/a2a` |
| Distillation script | `api.paircoder.ai/admin/a2a/context` | `a2a.paircoder.ai/admin/a2a/context` |

## What This Unblocks

- G3.C1-C3 (channel wiring, 30cx)
- G3.P4-P6 (review automation, status updates, sprint authoring, 70cx)
- A2A Phase 4 hardening (tenant isolation, container hardening)
- API cleanup (~900 lines of duplicated A2A code removed)

## Key References

| Document | Location |
|----------|----------|
| Deployment patterns audit | `docs/portfolio/infra/deployment-patterns.md` |
| Database decision | `docs/portfolio/decisions/D-025.yaml` |
| API removal guide | `bpsai-a2a/docs/api-removal-guide.md` |
| API deploy workflow | `paircoder_api/.github/workflows/ca-paircoder-app-cus-prod-*.yml` |
| A2A CI workflow | `bpsai-a2a/.github/workflows/ci.yml` |
| A2A Dockerfile | `bpsai-a2a/Dockerfile` |
| A2A start script | `bpsai-a2a/scripts/start.sh` |
| Sprint plan (G3) | `docs/portfolio/sprint-plan.md` |
| Status blocker | `docs/portfolio/status.yaml` → blockers → a2a-cutover |

## Session Context (For the Next Claude)

This session covered a lot of ground before reaching the A2A deployment work:
- Idea log architecture discovery + alignment with Metis
- G2 sprint planning + revision based on David's feedback
- David completed G2 overnight + started G3
- Computer overview (5-phase loop, SENSE/LEARN wired, DISPATCH built)
- Metis overview (3 roles: adversary, Computer support, organization helper)
- Workspace permissions fix (additionalDirectories in user settings)
- Infra audit across all repos

The A2A deployment is the critical-path blocker. Everything else in G3 can proceed in parallel except channels (G3.C1-C3) which need a live A2A endpoint.