# Deployment Patterns — Portfolio Infrastructure Audit

> **Date:** 2026-03-27
> **Purpose:** Reference for consistent deployment across the portfolio

---

## Current State

| Service | Hosting | CI/CD | Database | DNS | Port | Registry |
|---------|---------|-------|----------|-----|------|----------|
| **paircoder_api** | Azure Container Apps | GitHub Actions (auto on push to main) | Azure PostgreSQL | `api.paircoder.ai` | 8000 | GHCR |
| **paircoder.ai** | GitHub Pages | Git push | None | `paircoder.ai` (CNAME) | N/A | N/A |
| **paircoder_bot (Metis)** | Linux VM (systemd timers) | Manual (`scripts/deploy.sh`) | SQLite (local) | None | N/A | N/A |
| **bpsai-a2a** | Azure Container Apps | GitHub Actions (auto on push to main) | Azure PostgreSQL (shared server, separate DB) | `a2a.paircoder.ai` (CNAME + managed TLS) | 8001 | GHCR |
| **bpsai-support** | Unknown | None visible | Unknown | Unknown | Unknown | N/A |
| **agentlounge.ai** | Cloudflare Pages | Push to main | None | `agentlounge.ai` | N/A | N/A |

## Azure Resources (Production)

- **Resource Group:** `rg-paircoder-cus-prod`
- **Container App (API):** `ca-paircoder-app-cus-prod`
- **Key Vault:** `kv-paircoder-cus-prod`
- **PostgreSQL:** Existing server (name TBD — check Azure Portal)
- **Auth:** OIDC via GitHub Actions (client ID, tenant ID, subscription ID in repo secrets)

## The API Pattern (Template for New Services)

Source: `paircoder_api/.github/workflows/ca-paircoder-app-cus-prod-AutoDeployTrigger-*.yml`

```
Push to main
  → Azure Login (OIDC)
  → Build + push Docker image to GHCR (SHA tag + latest)
  → Configure GHCR registry on Container App
  → Update Container App with new image
  → Sync outbound IPs to Key Vault firewall
  → Smoke test (curl health endpoint, 5 retries)
```

### GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `*_AZURE_CLIENT_ID` | OIDC service principal |
| `*_AZURE_TENANT_ID` | Azure AD tenant |
| `*_AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `GHCR_PAT` | Pull images from GHCR on Container App |

### Naming Convention

- Container App: `ca-{service}-cus-prod`
- Resource Group: `rg-paircoder-cus-prod` (shared)
- Key Vault: `kv-paircoder-cus-prod` (shared)
- GHCR Image: `ghcr.io/bpsai/{service}`

## IaC Status

**None exists.** All Azure resources were provisioned manually (Portal or CLI). IaC (Bicep or Terraform) would be a new initiative across all services if desired.

## No Shared Database Pattern

Per D-025: services share the PostgreSQL **server** but use separate **databases**. No cross-database queries or foreign keys. Each service owns its Alembic migration history independently. Migration path to separate servers is documented in D-025.