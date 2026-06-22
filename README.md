## NAGP 2026 Kubernetes / DevOps / FinOps Assignment

### What this is
- **Service API tier**: FastAPI microservice exposing `/records` (fetches rows from Postgres).
- **Database tier**: Postgres with a `records` table pre-populated with sample data.

### Repo contents
- **API source**: `app.py`
- **Dockerfile**: `dockerfile`
- **Kubernetes manifests**: `k8s/`

### Docker images (Docker Hub: `rahul10nagarro`)
- **API image**: `rahul10nagarro/nagp-api:1.0.0`

Build + push:

```bash
docker build -t rahul10nagarro/nagp-api:1.0.0 .
docker push rahul10nagarro/nagp-api:1.0.0
```

### Kubernetes deployment (Ingress + HPA)
#### Prereqs
- A Kubernetes cluster (kind/minikube/AKS/EKS/GKE)
- NGINX Ingress Controller installed (Ingress class `nginx`)
- Metrics Server installed (required for HPA)

#### Apply manifests
1) Create namespace + config:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/db-configmap.yaml
kubectl apply -f k8s/postgres-init-configmap.yaml
kubectl apply -f k8s/postgres-pvc.yaml
```

2) Create DB password secret (recommended; keeps password out of YAML):

```bash
kubectl -n nagp-2026 create secret generic db-secret --from-literal=DB_PASSWORD='YourStrongPassword'
```

If you must use YAML, edit `k8s/db-secret.yaml` and set a base64 value, then apply:

```bash
kubectl apply -f k8s/db-secret.yaml
```

3) Deploy DB + API + Ingress + HPA:

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
This Ingress uses host `nagp.local`.

- **Records endpoint**: `http://nagp.local/records`

If you’re on minikube, you can also test without editing `/etc/hosts` by using:

```bash
minikube tunnel
curl -H "Host: nagp.local" http://127.0.0.1/records
```

### Demo checklist for screen recording
- Show objects: `kubectl -n nagp-2026 get all,cm,secret,pvc,ingress,hpa`
- Show API call: open `/records` in browser or `curl`
- Self-healing:
  - Kill one API pod: `kubectl -n nagp-2026 delete pod -l app=api --force --grace-period=0`
  - Show it recreates: `kubectl -n nagp-2026 get pods -w`
- DB recovery + persistence:
  - Kill DB pod: `kubectl -n nagp-2026 delete pod -l app=postgres --force --grace-period=0`
  - Show pod recreates and `/records` still returns old data
- Rolling update:
  - Update API image tag in `k8s/api-deployment.yaml` (e.g. `1.0.1`) and apply
  - Show rollout: `kubectl -n nagp-2026 rollout status deploy/api`
- HPA:
  - Show HPA: `kubectl -n nagp-2026 get hpa`
  - Generate load (any load tool) and show replicas scale beyond 4

### FinOps: 3+ cost optimization opportunities (examples)
- **Right-size requests/limits** using observed CPU/memory from `kubectl top pod` / monitoring.
- **HPA + fewer baseline replicas** for non-prod/off-peak (here baseline is fixed to 4 per assignment).
- **Cluster autoscaler / node autoscaling** so nodes scale down when pods scale down.
- **Use smaller nodes / bin-packing** with requests set realistically to reduce wasted capacity.
- **Scheduled scaling** (e.g., reduce replicas off-hours) for environments where it’s allowed.

### Requirement understanding (mapping)
- **API**: externally accessible via Ingress, rolling updates via Deployment strategy, self-healing via Deployment, HPA via `k8s/api-hpa.yaml`, ConfigMap + Secret for DB config.
- **DB**: 1 pod, ClusterIP only, PVC-backed storage, init SQL creates 1 table and inserts 7 records, self-heals after pod deletion and retains data.
