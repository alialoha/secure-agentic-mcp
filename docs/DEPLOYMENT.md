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

## Google Cloud Platform (GCP)

Below are practical paths for this repo’s **three containers** + shared **`data/`** volume.

### Path 1 — Compute Engine VM + Docker Compose (recommended to start)

Closest to local dev: one Linux VM runs the same `docker-compose.yml`.

1. **Create a VM** (e.g. **e2-medium** or **e2-standard-2**, Ubuntu 22.04 LTS) in a VPC/subnet with a **static external IP** if you want stable URLs.
2. **Firewall**: add a VPC rule (or use tags) to allow **tcp:8000,7860,5000** from your IP, or **80/443** if you terminate TLS on the VM with Caddy/Nginx and proxy to the containers.
3. **Install Docker** ([Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)) and Docker Compose plugin.
4. **Clone** the repo (or copy artifacts), add **`.env`** with `OPENAI_API_KEY` (never commit it).
5. Run:

   ```bash
   docker compose up --build -d
   ```

6. **Persist `data/`**: the compose file mounts `./data` — keep it on the VM disk; for backups use **snapshots** of the boot disk or sync `data/` to a **Cloud Storage** bucket (e.g. `gsutil rsync`).

**TLS / domain:** Put **Cloud Load Balancing** + managed certificate in front, or run **Caddy** on the VM with Let’s Encrypt, proxying to `127.0.0.1:7860` and `:5000` (and optionally leave MCP on `:8000` **internal-only** via firewall).

**Cost tip:** Stop the VM when not demoing; use **e2-small** only for light traffic.

---

### Path 2 — Cloud Run (three separate services)

Each service from `docker-compose.yml` becomes a **Cloud Run** service. Images live in **Artifact Registry**.

| Step | Action |
|------|--------|
| Build | `docker build -f Dockerfile.mcp -t REGION-docker.pkg.dev/PROJECT/REPO/mcp:latest .` (repeat for `operator`, `web`) |
| Push | `docker push ...` for each image |
| Deploy | Deploy **mcp** first; note its **HTTPS URL** (e.g. `https://mcp-xxxxx-uc.a.run.app`) |
| Env | Set **`MCP_SERVER_URL`** on **operator** and **web** to that **HTTPS** base URL (no `http://mcp:8000` — that only works inside Compose). |
| Secrets | Store **`OPENAI_API_KEY`** in **Secret Manager**; reference it in Cloud Run (secret as env var). |

**Persistence:** Cloud Run instances are **ephemeral**; the default empty disk is not durable. For real `permissions.json` / workspace survival, use **Cloud Storage** (application change or sidecar), **Firestore** for policy only, or **Filestore** (NFS) — or stay on **Compute Engine** for simplicity.

**HTTP / MCP:** Streamable HTTP + SSE may need **increased request timeout** and **CPU always allocated** (min instances ≥ 1) if sessions must stay warm. Validate MCP over the public Run URL before relying on it.

---

### Path 3 — Google Kubernetes Engine (GKE)

Use when you want **Kubernetes** on GCP: **GKE Autopilot** or **Standard**.

- **Artifact Registry** for images.
- **Deployments + Services** for `mcp`, `operator`, `web`; **ClusterIP** for MCP; **Ingress** (GCE) for operator/web with managed TLS.
- **PersistentVolumeClaim** with **Filestore** (ReadWriteMany) or a single-replica StatefulSet + **Persistent Disk** if one node holds `data/`.
- **Secret Manager** + **Workload Identity** to inject `OPENAI_API_KEY` without baking it into images.

This is more moving parts than Path 1; use after Compose on a VM is stable.

---

### GCP checklist (all paths)

- [ ] **Billing** enabled; **APIs**: Compute Engine / Run / Container / Artifact Registry as needed.
- [ ] **`OPENAI_API_KEY`** in **Secret Manager** or Cloud Run/GKE secrets — not in Git.
- [ ] **`MCP_SERVER_URL`** matches how clients reach MCP (**HTTPS** on Cloud Run; **`http://mcp:8000`** only valid inside Docker Compose or internal K8s DNS).
- [ ] **Firewall / IAM**: restrict who can hit admin UIs (7860) in production.
- [ ] **Logging**: enable **Cloud Logging** for container stdout; treat **`audit.log`** as sensitive if you persist it.

### CI on GCP (optional)

- **Cloud Build** trigger on GitHub: run `pytest`, `docker build`, push to Artifact Registry, deploy to Cloud Run or GKE.
- Connect repo via **Cloud Build GitHub App** or **Workload Identity Federation**.

---

*For the smallest time-to-demo on GCP, start with **Compute Engine + docker compose**; evolve to Cloud Run or GKE once you need scale or stricter isolation.*
