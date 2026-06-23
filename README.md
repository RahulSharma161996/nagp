# NAGP 2026 — Kubernetes, DevOps & FinOps Assignment

## Deliverables

| Item                      | Link                                             |
| ------------------------- | ------------------------------------------------ |
| Code repository           | https://github.com/RahulSharma161996/nagp.git    |
| Docker image (Docker Hub) | https://hub.docker.com/r/rahul10nagarro/nagp-api |
| Service API URL           | http://34.128.181.83/records                     |
| Screen recording          | <PASTE YOUR VIDEO LINK>                          |

**Video demonstrates:** all objects running, `/records` API call, API pod self-healing, DB pod recovery with data persistence, rolling update, HPA, and FinOps considerations.

---

## Requirement Understanding

Two-tier application on Kubernetes: a **Service API tier** (FastAPI) exposed externally, and a **Database tier** (Postgres) internal-only with persistent storage.

| Requirement                 | API Tier                | DB Tier        |
| --------------------------- | ----------------------- | -------------- |
| Exposed outside cluster     | Yes (Ingress)           | No (ClusterIP) |
| Pods                        | 4                       | 1              |
| Rolling updates             | Yes                     | No             |
| Persistent storage          | No                      | Yes (PVC)      |
| ConfigMap                   | Yes                     | Optional       |
| Secrets                     | Yes                     | Yes            |
| HPA                         | Yes                     | —              |
| Self-healing                | Yes                     | Yes            |
| No Pod IP for communication | Uses Service `postgres` | —              |

---

## Assumptions

- GKE cluster deployed via GCP Cloud Shell (no local Docker/Kubernetes install).
- Docker image built and pushed via GitHub Actions.
- DB password created with `kubectl create secret` (not stored in YAML).
- Ingress external IP may change if the cluster is recreated.

---

## Solution Overview

- **API:** FastAPI microservice (`app.py`) — `GET /records` fetches rows from Postgres. Image: `rahul10nagarro/nagp-api:1.0.1`.
- **DB:** Postgres 16 with PVC, init SQL seeds `records` table (7 rows). `PGDATA` subdirectory used for PVC compatibility.
- **Kubernetes:** manifests in `k8s/` — Namespace, ConfigMap, Secret, Deployments, Services, Ingress, HPA, NetworkPolicy, PVC.
- **CI:** `.github/workflows/docker-publish.yml` builds and pushes image to Docker Hub on push to `main`.

---

## Justification for Resources Utilized

**API Deployment (`k8s/api-deployment.yaml`)**

- `replicas: 4` — meets assignment requirement.
- `RollingUpdate` — zero-downtime image updates.
- Probes on `/` — health checks for self-healing and GKE Ingress compatibility.
- Requests: `cpu 100m`, `memory 128Mi` — scheduling baseline for HPA.
- Limits: `cpu 300m`, `memory 256Mi` — caps runaway usage (FinOps).

**DB Deployment (`k8s/postgres-deployment.yaml`)**

- `replicas: 1` with `Recreate` strategy — single writer on one PVC.
- PVC `1Gi` — data survives pod deletion/restart.

**HPA (`k8s/api-hpa.yaml`)**

- `minReplicas: 4`, `maxReplicas: 10`, CPU target 60% — scales API under load.

**FinOps optimizations identified**

1. Right-size requests/limits using `kubectl top pods`.
2. HPA to scale pods with demand; delete cluster after demo to avoid cost.
3. Use appropriately sized nodes (`e2-small`) and `pd-standard` disks to stay within quota.
