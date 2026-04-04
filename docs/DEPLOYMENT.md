# Deployment planning

This document outlines options and checklists for running **secure-agentic-mcp** beyond your laptop. Adjust for your cloud provider and budget.

## What you are deploying

Three long-running processes (or three containers):

| Service | Role | Default port |
|--------|------|--------------|
| **mcp** | FastMCP HTTP server (`/mcp`) | 8000 |
| **operator** | Gradio admin UI | 7860 |
| **web** | Flask user UI | 5000 |

Shared **`data/`** volume: `permissions.json`, `workspace/`, `audit.log`.  
Secrets: **`OPENAI_API_KEY`** (Operator AI chat + Flask Live only).

## Option A — Docker Compose (simplest full stack)

Already in the repo: `docker-compose.yml`, `Dockerfile.*`.

1. Build a Linux host with Docker (VM, EC2, Lightsail, Azure VM, etc.).
2. Copy `.env` with `OPENAI_API_KEY` (and any overrides).
3. `docker compose up --build -d`
4. Open firewall/security group for **8000, 7860, 5000** (or put **Nginx/Caddy** in front with TLS and proxy to internal ports).

**Hardening:** Do not expose all three ports publicly without TLS; prefer a reverse proxy with HTTPS and auth (e.g. basic auth or OAuth in front of Gradio/Flask).

## Option B — Managed containers (AWS ECS / Azure Container Apps / GCP Cloud Run)

- **MCP server** must stay **reachable** from the operator/web containers (`MCP_SERVER_URL` like `http://mcp:8000` in Compose; in cloud, use service DNS).
- Mount **persistent storage** for `data/` so `permissions.json` and workspace survive restarts.
- Set **health checks** on HTTP (e.g. MCP port responds; Gradio/Flask return 200 on `/`).
- **Cloud Run note:** Multiple services + internal networking differs from Compose; you may need VPC connector or shared service mesh.

## Option C — Kubernetes

- One `Deployment` + `Service` per component; `PersistentVolumeClaim` for `data/`.
- `ConfigMap`/`Secret` for non-secret env; **Secrets** for `OPENAI_API_KEY`.
- **Ingress** with TLS (cert-manager) for operator and web; MCP may stay internal-only.

## Environment checklist (production)

- [ ] `OPENAI_API_KEY` set only where needed (operator + web), not in images.
- [ ] `MCP_SERVER_URL` points to the **actual** MCP service URL (not localhost unless same pod).
- [ ] `MCP_DATA_DIR` / volume mount consistent across services that share `data/`.
- [ ] `AUTHOR_NAME` / `REPO_URL` optional (branding).
- [ ] Rate limits / abuse protection on public HTTP endpoints if exposed.
- [ ] Logs: ship container stdout to your log provider; **audit.log** is on disk — include volume backup if compliance matters.

## CI/CD (optional next step)

- **Lint + test** on every push: `pytest` (no MCP server required for most tests).
- **Build** Docker images and push to GHCR / ECR / ACR.
- **Deploy** via your platform (Compose on VM, ECS task definition update, etc.).

## Pre-flight before going live

1. Run `docker compose build` locally or in CI and fix any failures.
2. Run `pytest` in CI.
3. Smoke-test: MCP `list_tools`, Operator opens, Flask Demo/Live once keys are set.

---

*Add provider-specific runbooks (e.g. “AWS ECS + ALB”) here as you lock choices.*
