## NAGP 2026 Kubernetes / DevOps / FinOps Assignment

### Deliverables (as per assignment)

- **Code repository URL**: `https://github.com/RahulSharma161996/nagp.git`
- **Docker image URL (Docker Hub)**: `https://hub.docker.com/r/rahul10nagarro/nagp-api`
- **Service API URL to view records**: `http://<INGRESS_EXTERNAL_IP>/records` (example used in demo: `http://34.128.181.83/records`)
- **Screen recording video**:
  - Show all Kubernetes objects deployed and running
  - Show `/records` API call retrieving records from DB
  - Delete an API pod and show it regenerates (self-healing)
  - Delete the DB pod and show it regenerates and **keeps old data** (persistence)
  - Show rolling update behavior for API
  - Show HPA configuration and scaling evidence

### Repo contents

- **API source**: `app.py`
- **Dockerfile**: `Dockerfile`
- **Kubernetes manifests**: `k8s/`

### Requirement Understanding

The goal is to design, containerize, and deploy a **2-tier Kubernetes application**:

- **Service API tier** (microservice): exposed externally, fetches data from DB via a service endpoint
- **Database tier**: internal-only, persistent storage, auto-recovers after pod deletion

Mandatory requirements covered:

- **API tier**
  - Externally accessible: **Ingress**
  - Pods: **4 replicas**
  - Rolling updates: **Deployment RollingUpdate**
  - Self-healing: **Deployment controller + probes**
  - HPA: **HorizontalPodAutoscaler**
  - DB config externalized: **ConfigMap**
  - DB password not in YAML: **Secret**
- **DB tier**
  - 1 table + 5–10 records: created via init SQL (7 records)
  - Persistence: **PVC**
  - Internal-only access: **ClusterIP Service**
  - Auto-recovery: **Deployment**
  - No Pod IP usage: API uses **Service DNS** (`postgres`)

### Assumptions

- Using **GKE + Cloud Shell** for “no-admin-rights” environment.
- Ingress controller is available (GKE default ingress works with the provided `k8s/ingress.yaml`).
- Metrics are available (required for HPA); otherwise metrics-server must be installed/enabled.
- Docker image is built/pushed via **GitHub Actions** (no local Docker install).

### Solution Overview

- **API**: FastAPI + psycopg connection pool.
  - Endpoint: `GET /records` returns rows from Postgres table `records`.
  - Health: `GET /healthz` used for readiness/liveness.
- **DB**: Postgres 16 on PVC.
  - Seed data via `k8s/postgres-init-configmap.yaml` mounted into `/docker-entrypoint-initdb.d`.
  - Uses `PGDATA=/var/lib/postgresql/data/pgdata` to avoid `lost+found` issues on some PVCs.
- **Kubernetes objects**
  - Namespace: `k8s/namespace.yaml`
  - ConfigMap: `k8s/db-configmap.yaml`
  - Secret: `db-secret` (recommended created from CLI)
  - Postgres: `k8s/postgres-deployment.yaml`, `k8s/postgres-service.yaml`, `k8s/postgres-pvc.yaml`
  - API: `k8s/api-deployment.yaml`, `k8s/api-service.yaml`
  - Ingress: `k8s/ingress.yaml`
  - HPA: `k8s/api-hpa.yaml`
  - NetworkPolicy (optional hardening): `k8s/networkpolicy.yaml`

### Justification for Resources Utilized

- **API requests/limits** (`k8s/api-deployment.yaml`)
  - Requests set to ensure predictable scheduling and enable HPA based on CPU.
  - Limits set to prevent runaway resource usage.
- **DB PVC** (`k8s/postgres-pvc.yaml`)
  - Ensures DB data survives pod rescheduling/restarts and meets persistence requirement.
- **4 replicas for API**
  - Meets assignment requirement and demonstrates rolling updates + self-healing behavior.

### Docker images (Docker Hub)

- **API image**: `rahul10nagarro/nagp-api:1.0.0`

Build + push (if Docker is available locally):

```bash
docker build -t rahul10nagarro/nagp-api:1.0.0 .
docker push rahul10nagarro/nagp-api:1.0.0
```

Build + push (recommended, no Docker locally):

- GitHub Actions workflow: `.github/workflows/docker-publish.yml`
- Required GitHub secrets:
  - `DOCKERHUB_USERNAME` = `rahul10nagarro`
  - `DOCKERHUB_TOKEN` = Docker Hub access token with **Read & Write**

### Kubernetes deployment (Ingress + HPA)

#### Prereqs

- A Kubernetes cluster (kind/minikube/AKS/EKS/GKE)
- An Ingress controller (GKE default ingress works with the provided `k8s/ingress.yaml`)
- Metrics Server installed (required for HPA)

#### Apply manifests

1. Create namespace + config:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/db-configmap.yaml
kubectl apply -f k8s/postgres-init-configmap.yaml
kubectl apply -f k8s/postgres-pvc.yaml
```

2. Create DB password secret (recommended; keeps password out of YAML):

```bash
kubectl -n nagp-2026 create secret generic db-secret --from-literal=DB_PASSWORD='YourStrongPassword'
```

If you must use YAML, edit `k8s/db-secret.yaml` and set a base64 value, then apply:

```bash
kubectl apply -f k8s/db-secret.yaml
```

3. Deploy DB + API + Ingress + HPA:

```bash
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/networkpolicy.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/api-hpa.yaml
```

### API URL (external)

- **Records endpoint**: `http://<INGRESS_EXTERNAL_IP>/records`

Example from a successful GKE run:

- `http://34.128.181.83/records`

### Demo checklist for screen recording

#### Commands used in the recording

Show objects deployed and running:

```bash
kubectl -n nagp-2026 get all,cm,secret,pvc,ingress,hpa
```

Show an API call retrieving DB records:

```bash
kubectl -n nagp-2026 get ingress
curl "http://<INGRESS_EXTERNAL_IP>/records"
```

Kill an API pod and show it regenerates (self-healing):

```bash
kubectl -n nagp-2026 delete pod -l app=api
kubectl -n nagp-2026 get pods -w
```

Kill the DB pod and show it regenerates and keeps old data:

```bash
kubectl -n nagp-2026 delete pod -l app=postgres
kubectl -n nagp-2026 get pods -w
curl "http://<INGRESS_EXTERNAL_IP>/records"
```

Rolling update demonstration:

```bash
kubectl -n nagp-2026 set image deploy/api api=rahul10nagarro/nagp-api:1.0.1
kubectl -n nagp-2026 rollout status deploy/api
```

HPA evidence:

```bash
kubectl -n nagp-2026 get hpa
kubectl top pods -n nagp-2026
```

### FinOps Requirements

#### Requests/limits (implemented)

- API tier includes CPU/memory requests and limits in `k8s/api-deployment.yaml`.

#### 3+ Kubernetes cost optimization opportunities (identified)

1. **Right-size requests/limits** using observed metrics (avoid over-requesting and wasting node capacity).
2. **Autoscaling**
   - Use **HPA** to scale pods based on demand (implemented).
   - Use **Cluster Autoscaler** (or managed node autoscaling) so nodes can scale down when load drops.
3. **Workload scheduling efficiency**
   - Choose smaller node types and right-size requests to improve bin-packing.
   - Use separate node pools for system vs workloads (optional) to avoid oversized nodes.

#### Resource optimization using observed metrics (how to demonstrate)

Capture:

```bash
kubectl top pods -n nagp-2026
kubectl top nodes
```

Then update `resources:` in `k8s/api-deployment.yaml` based on observed peak/average values and re-apply:

```bash
kubectl apply -f k8s/api-deployment.yaml
kubectl -n nagp-2026 rollout status deploy/api
```
