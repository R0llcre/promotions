# NYU DevOps - Promotion Team

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Language-Python-blue.svg)](https://python.org/)
[![Build Status](https://github.com/CSCI-GA-2820-FA25-003/promotions/actions/workflows/workflow.yml/badge.svg)](https://github.com/CSCI-GA-2820-FA25-003/promotions/actions)
[![codecov](https://codecov.io/gh/CSCI-GA-2820-FA25-003/promotions/graph/badge.svg?token=FS7IXVUIWI)](https://codecov.io/gh/CSCI-GA-2820-FA25-003/promotions)


# Promotions Service

A small, production‑style REST API for creating, reading, updating, deleting, and querying **promotions**.

This version unifies the model query contract and clarifies ambiguous terminology:

* **Single‑item lookup** returns a **model instance or `None`**.
* **Multi‑item lookups** return a **`list` of model instances**.
* The legacy concept of *category* has been replaced with the explicit **`product_id`** filter.
* For backward compatibility, a deprecated alias `find_by_category()` still delegates to `find_by_product_id()`.


---

## Table of Contents

* [Overview](#overview)
* [Deploy to Kubernetes](#Deploy-to-Kubernetes)
* [Architecture](#architecture)
* [Requirements](#requirements)
* [Quick Start](#quick-start)
* [Configuration](#configuration)
* [Data Model](#data-model)
* [API Reference](#api-reference)

  * [Service Root](#service-root)
  * [List Promotions (Filters & Priority)](#list-promotions-filters--priority)
  * [Get by ID](#get-by-id)
  * [Create](#create)
  * [Update (Full Replace)](#update-full-replace)
  * [Delete](#delete)
  * [Error Responses](#error-responses)
* [Behavioral Guarantees & Validation](#behavioral-guarantees--validation)
* [Design Rationale (Why These Changes)](#design-rationale-why-these-changes)
* [Testing & Quality](#testing--quality)
* [CLI Commands](#cli-commands)
* [Project Structure](#project-structure)
* [Compatibility Notes](#compatibility-notes)
* [Kubernetes Smoke Check](#Kubernetes-Smoke-Check)
* [Appendix: Minikube Compatibility Notes](#Appendix-Minikube-Compatibility-Notes)
* [License](#license)

---

## Overview

The Promotions Service exposes CRUD and query endpoints for promotion records. It is implemented with **Flask** and **Flask‑SQLAlchemy**, uses **PostgreSQL** by default, and returns JSON responses.

Key features:

* **Unified query contract**: consistent return types across model methods.
* **Explicit field naming**: uses `product_id` (not “category”) for product filters.
* **Multiple list filters** with deterministic **priority** when multiple query parameters are supplied.
* **Robust validation** and **uniform error responses** for common failure scenarios.
* **High test coverage** (threshold ≥ 95%) across success and error paths.

---

## Deploy to Kubernetes

**Scope.** Deploy the Promotions microservice with PostgreSQL to a local K3D/K3S cluster and expose it via an Ingress.
**Defaults.** App listens on `8080`. `make cluster` maps the cluster LB `:80` → host `:8080`.

### Architecture (at a glance)

* **App**: Flask + Gunicorn (`wsgi:app`), `/health` for probes
* **DB**: PostgreSQL (StatefulSet + PVC)
* **Networking**: `promotions-service` (ClusterIP, `80 → 8080`), `promotions-ingress` (host routing)
* **Config**: `DATABASE_URI` injected from a Kubernetes Secret

---

### Prerequisites

* Docker, kubectl, k3d (or use this repo’s DevContainer)
* Repo contains:

  * `Dockerfile` (root; production image with Gunicorn on `8080`)
  * `Makefile` with `IMAGE_NAME ?= promotions`
  * `/health` endpoint in `service/routes.py`
  * K8s manifests:

    * `k8s/deployment.yaml` (app + probes + initContainer + Secret env)
    * `k8s/service.yaml` (`promotions-service`)
    * `k8s/ingress.yaml` (host `promotions.local`, Traefik)
    * `k8s/postgres/statefulset.yaml` (with `PGDATA` subfolder + `fsGroup`)
    * `k8s/postgres/service.yaml` (`postgres` ClusterIP)
    * `k8s/secrets/promotions-db.yaml` (Secret with `DATABASE_URI`)

---

### Make Targets (cheat-sheet)

```bash
make cluster   # Create/ensure local K3D cluster (LB:80 → host:8080) + local registry
make build     # Build image from Dockerfile → cluster-registry:5000/promotions:1.0
# (Tip) Prefer direct import instead of pushing:
k3d image import cluster-registry:5000/promotions:1.0 -c nyu-devops
```

> Why “import”? Inside DevContainers, the name `cluster-registry` may not resolve. Importing the local image straight into k3d nodes avoids DNS/registry setup entirely.

---

### Quick Start (copy & paste)

```bash
make cluster
make build
make push
kubectl apply -f k8s/postgres/statefulset.yaml
kubectl apply -f k8s/postgres/service.yaml
kubectl apply -f k8s/secrets/promotions-db.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
curl -i -H "Host: promotions.local" http://localhost:8080/health
```

**Expected:** `HTTP/1.1 200 OK` and `{"status":"OK"}`.

---

### Step-by-Step (with intent)

1. **Create/ensure cluster & LB mapping**

   ```bash
   make cluster
   ```
2. **Build the app image**

   ```bash
   make build
   ```
3. **Load the image into k3d nodes (skip registry)**

   ```bash
    make push
   ```
4. **Bring up PostgreSQL (StatefulSet + Headless Service)**

   ```bash
   kubectl apply -f k8s/postgres/statefulset.yaml
   ```
5. **Expose DB via ClusterIP `postgres:5432`**

   ```bash
   kubectl apply -f k8s/postgres/service.yaml
   ```
6. **Wait until DB is Ready**

   ```bash
   kubectl get pods -l app=postgres -w
   ```
7. **Create app DB Secret (`DATABASE_URI`)**

   ```bash
   kubectl apply -f k8s/secrets/promotions-db.yaml
   ```
8. **Deploy app (initContainer waits for DB, probes on `/health`)**

   ```bash
   kubectl apply -f k8s/deployment.yaml
   ```
9. **Create app Service (`80 → 8080`)**

   ```bash
   kubectl apply -f k8s/service.yaml
   ```
10. **Create Ingress (host `promotions.local`)**

    ```bash
    kubectl apply -f k8s/ingress.yaml
    ```
11. **Verify app pod is Ready**

    ```bash
    kubectl get pods -l app=promotions -w
    ```

---

### Validate

**Option A (no `/etc/hosts` edit):**

```bash
curl -i -H "Host: promotions.local" http://localhost:8080/health
```

**Option B (edit hosts once):**

```bash
echo "127.0.0.1 promotions.local" | sudo tee -a /etc/hosts
curl -i http://promotions.local:8080/health
```

---

### Troubleshooting

**Postgres CrashLoopBackOff (initdb fails)**
Symptoms: `directory ... exists but is not empty (lost+found)` or permission errors.

* Already mitigated in `statefulset.yaml`:

  * `PGDATA=/var/lib/postgresql/data/pgdata` (subfolder avoids `lost+found`)
  * `securityContext.fsGroup=999` (write access for `postgres`)
* If half-initialized PVC persists (demo only):

  ```bash
  kubectl scale statefulset postgres --replicas=0
  kubectl delete pvc pgdata-postgres-0
  kubectl scale statefulset postgres --replicas=1
  ```

**Ingress 404**

* Use Host header or add `/etc/hosts` for `promotions.local`.
* Ensure `ingressClassName: traefik` matches your controller.
* Bypass Ingress to isolate:

  ```bash
  kubectl port-forward svc/promotions-service 8088:80
  curl -i http://127.0.0.1:8088/health
  ```

**App cannot reach DB**

* Check DB Service & pod readiness: `kubectl get svc postgres`, `kubectl get pods -l app=postgres`.
* Verify Secret: `kubectl get secret promotions-db -o yaml` (has `DATABASE_URI`).
* App logs: `kubectl logs deploy/promotions-deployment`.
* Nudge rollout:

  ```bash
  kubectl rollout restart deploy/promotions-deployment
  ```

---

### Cleanup

```bash
kubectl delete -f k8s/ingress.yaml
kubectl delete -f k8s/service.yaml
kubectl delete -f k8s/deployment.yaml
kubectl delete -f k8s/postgres/service.yaml
kubectl delete -f k8s/postgres/statefulset.yaml
kubectl delete -f k8s/secrets/promotions-db.yaml
# (Optional) delete data:
# kubectl delete pvc pgdata-postgres-0
```

---

### File Inventory (for reviewers)

* `Dockerfile` (root)
* `Makefile` (`IMAGE_NAME ?= promotions`)
* `service/routes.py` (`/health`)
* `k8s/postgres/statefulset.yaml` (PGDATA subfolder + fsGroup + probes)
* `k8s/postgres/service.yaml` (`postgres` ClusterIP)
* `k8s/secrets/promotions-db.yaml` (Secret with `DATABASE_URI`)
* `k8s/deployment.yaml` (initContainer + probes + Secret env)
* `k8s/service.yaml` (`promotions-service`)
* `k8s/ingress.yaml` (`promotions.local` → `promotions-service:80`)

---

## Architecture

* **Framework:** Flask
* **ORM:** Flask‑SQLAlchemy
* **Database:** PostgreSQL (psycopg driver)
* **Model:** `Promotion` with auditing fields (`created_at`, `last_updated`) stored server‑side; the REST API’s JSON only exposes core business fields.

---

## Requirements

* **Python**: 3.11+
* **PostgreSQL**: 13+ (or a compatible managed instance)
* **Tools**: `pip`, `venv` or a containerized environment (DevContainer/Docker)

---

## Quick Start

```bash
# 1) (Optional) create & activate a virtualenv
python -m venv venv
source venv/bin/activate

# 2) install dependencies
pip install -r requirements.txt

# 3) configure DB (see "Configuration" below), then create tables
flask db-create

# 4) run the service (default http://127.0.0.1:5000)
flask run

# 5) run tests (with coverage gate ≥ 95%)
make test
```

---

## Configuration

The service relies on a PostgreSQL connection string:

* **`DATABASE_URI`** (env var) – e.g.
  `postgresql+psycopg://postgres:postgres@localhost:5432/dev`

**Testing defaults** to:
`postgresql+psycopg://postgres:postgres@localhost:5432/testdb`

> Ensure your DB is reachable and that you have executed `flask db-create` to create tables.

Common Flask env vars (optional):

* `FLASK_APP` – your app entrypoint (if needed)
* `FLASK_ENV` – `development` or `production`
* `FLASK_DEBUG` – `0`/`1` for debug

---

## Data Model

`Promotion` JSON shape (fields exposed by the API):

| Field            | Type             | Required | Description                             |
| ---------------- | ---------------- | -------- | --------------------------------------- |
| `id`             | integer          | auto     | Primary key                             |
| `name`           | string (≤ 63)    | yes      | Promotion name                          |
| `promotion_type` | string (≤ 63)    | yes      | Free‑form type (e.g., “Percentage off”) |
| `value`          | integer          | yes      | Discount amount/percent (integer)       |
| `product_id`     | integer          | yes      | Associated product identifier           |
| `start_date`     | ISO date (Y‑M‑D) | yes      | Start date, e.g., `"2025-10-01"`        |
| `end_date`       | ISO date (Y‑M‑D) | yes      | End date, e.g., `"2025-10-31"`          |

**Example JSON:**

```json
{
  "id": 1,
  "name": "Summer Sale",
  "promotion_type": "Percentage off",
  "value": 25,
  "product_id": 123,
  "start_date": "2025-06-01",
  "end_date": "2025-06-30"
}
```

> The model also maintains auditing fields (`created_at`, `last_updated`) that are **not** part of the REST JSON.

---

## API Reference

**Base URL**: `/`

### Service Root

`GET /` → returns service metadata:

```json
{
  "name": "Promotions Service",
  "version": "1.0.0",
  "description": "RESTful service for managing promotions",
  "paths": { "promotions": "/promotions" }
}
```

---

### List Promotions (Filters & Priority)

`GET /promotions`

You can filter by **one** of the following query parameters. If multiple are provided, the service applies **only the highest‑priority** filter and ignores the rest:

**Priority**: `id` ▶ `name` ▶ `product_id` ▶ `promotion_type`

| Parameter                  | Type   | Behavior                  | Response shape  |
| -------------------------- | ------ | ------------------------- | --------------- |
| `?id=<int>`                | int    | Exact ID match            | `[]` or `[obj]` |
| `?name=<string>`           | string | Exact name match          | `[obj, ...]`    |
| `?product_id=<int>`        | int    | Exact product match       | `[obj, ...]`    |
| `?promotion_type=<string>` | string | Exact type match          | `[obj, ...]`    |
| *(no query)*               | —      | Return **all** promotions | `[obj, ...]`    |

**Examples**

```bash
# by type
curl -s "http://127.0.0.1:5000/promotions?promotion_type=Buy%20One%20Get%20One"

# by product_id
curl -s "http://127.0.0.1:5000/promotions?product_id=123"

# by name
curl -s "http://127.0.0.1:5000/promotions?name=NYU%20Demo"

# by id (returns [] or [obj])
curl -s "http://127.0.0.1:5000/promotions?id=42"
```

Notes:

* `product_id` accepts numbers and numeric strings (e.g., `"2222"`).
* Invalid numeric filters yield an **empty list** (not a 500).

---

### Get by ID

`GET /promotions/<id:int>`

* **200 OK** with the promotion object when found
* **404 Not Found** when the ID does not exist

---

### Create

`POST /promotions`
**Content‑Type** must be `application/json` (the server **accepts** `; charset=utf-8` etc. and validates by Flask’s parsed `mimetype`).

**Required body fields**: `name`, `promotion_type`, `value` (int), `product_id` (int), `start_date` (ISO date), `end_date` (ISO date)

**Example**

```bash
curl -s -X POST "http://127.0.0.1:5000/promotions" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "NYU Demo",
        "promotion_type": "AMOUNT_OFF",
        "value": 10,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31"
      }' -i
```

* **201 Created** with JSON body and a `Location` header pointing to `GET /promotions/<id>`
* **400 Bad Request** for invalid data types/shape (e.g., non‑int `value`)
* **415 Unsupported Media Type** if `Content-Type` is not `application/json`

---

### Update (Full Replace)

`PUT /promotions/<id:int>`
Full replacement: send a complete resource representation (same required fields as *Create*). The server enforces **ID consistency**:

* If your request body includes an `id` and it **does not match** the path `<id>`, the server returns **400 Bad Request**.
* Otherwise:

  * **200 OK** with the updated resource if found
  * **404 Not Found** if the resource does not exist

**Example**

```bash
curl -s -X PUT "http://127.0.0.1:5000/promotions/1" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "NYU Demo+",
        "promotion_type": "AMOUNT_OFF",
        "value": 15,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31"
      }'
```

---

### Delete

`DELETE /promotions/<id:int>`

* **204 No Content** on successful deletion
* **404 Not Found** if the resource does not exist

---

### Error Responses

All errors are returned as **JSON**. Common cases:

| Scenario                           | Status                     |
| ---------------------------------- | -------------------------- |
| Missing/invalid fields or types    | 400 Bad Request            |
| Resource not found                 | 404 Not Found              |
| HTTP method not allowed on a route | 405 Method Not Allowed     |
| Wrong/absent `Content-Type`        | 415 Unsupported Media Type |
| Unhandled server exception         | 500 Internal Server Error  |

> The test suite verifies JSON error responses for 404/405/415 and simulates a 500 path via patched exceptions. The exact error object shape may be subject to your centralized error handler but is guaranteed to be JSON.

---

## Behavioral Guarantees & Validation

* **Unified query contract**

  * `Promotion.find(id)` → returns a **Promotion** or **`None`** (invalid IDs return `None`).
  * `Promotion.find_by_name(name)` / `find_by_product_id(product_id)` / `find_by_promotion_type(type)` → each returns a **`list`** (empty list if no matches or invalid filter).
* **Type rigor in deserialization**

  * `value` and `product_id` must be integers; invalid types produce **400**.
  * `start_date` and `end_date` must be ISO date strings (`YYYY‑MM‑DD`).
* **Transactional safety**

  * `create`, `update`, `delete` all wrap DB operations in try/except; on errors they roll back and emit a model‑level `DataValidationError` that the route layer translates into a 4xx error.
* **Content type check**

  * Based on Flask’s parsed `request.mimetype` rather than raw header string, so `application/json; charset=utf-8` is accepted.

---

## Design Rationale (Why These Changes)

* **Consistency & usability**: Historically, some multi‑item queries returned a SQLAlchemy `Query`, others returned a `list`, and one path (`find_by_id`) even returned a single‑element list. This inconsistency caused confusion (e.g., when to call `.count()` vs. `len()`). We standardized: **single‑item → object/None, multi‑item → list**.
* **Clarity of domain terms**: The legacy `category` name did not clearly communicate “product ID” and led to misinterpretation. We now expose **`product_id`** explicitly (with `find_by_category` kept as a deprecated alias).
* **Robustness**: Filters now tolerate numeric strings and handle invalid input by returning empty lists instead of raising exceptions.
* **Predictability**: The list endpoint defines a clear **filter priority** to avoid surprising results when multiple filters are provided.
* **Correctness & integrity**: The update route enforces **ID consistency** between the URL path and the body.

These changes reduce maintenance burden and make it safer and more intuitive to build features on top of the API.

---

## Testing & Quality

Run the full suite (unit + integration):

```bash
make test
```

Coverage gate is **≥ 95%**. The suite includes:

* Model CRUD, serialization/deserialization, and transaction rollback tests
* Query tests for `find`, `find_by_name`, `find_by_product_id`, `find_by_promotion_type`
* Route tests for all filters (`id`, `name`, `product_id`, `promotion_type`) and “no filter”
* Error‑path tests for 400/404/405/415 and a simulated 500 path (with temporary disabling of exception propagation to hit the JSON 500 handler)

---

## CLI Commands

* `flask db-create` – initialize database tables

> Ensure `DATABASE_URI` is set and reachable before running this command.

---

## Project Structure

```
service/
  __init__.py
  routes.py          # REST endpoints and filter priority
  models.py          # Promotion model + unified query contract
  common/
    status.py        # HTTP status codes
    error_handlers.py
    log_handlers.py
    cli_commands.py
tests/
  test_models.py     # Model behavior, queries, validation, exceptions
  test_routes.py     # Routes, filters, errors, 500 simulation
  test_cli_commands.py
wsgi.py              # App entry (Flask)
Makefile
requirements.txt
README.md            # This file
```

---

## Compatibility Notes

* **Deprecated**: `find_by_id(...)` (single‑element list semantics). Use `find(id)` instead.
* **Deprecated alias**: `find_by_category(...)` is kept for backward compatibility and forwards to `find_by_product_id(...)`. Prefer `find_by_product_id(...)`.
* **Legacy documentation**: Earlier docs referenced `GET /promotions?product={id}`. The correct and current form is **`GET /promotions?product_id={id}`**. This README supersedes that older reference. 

---


## Kubernetes Smoke Check
**Requirement 3 – Deploy to Kubernetes · K8S-11 (P2)**

A one-command smoke test to confirm a healthy deployment.

### What it checks
- **Pods Ready** — all Pods with `app=promotions` in the target namespace are `Ready`.
- **Service exists** — `promotions-service`.
- **Ingress exists** — `promotions-ingress`.
- **HTTP endpoints (200 OK)** — `GET /health` and `GET /promotions`.  
  The command uses a temporary `kubectl port-forward` to the Service and, if needed, adds the Ingress **Host** header automatically so host-based routing succeeds.

---

### Prerequisites
- A running Kubernetes cluster (e.g., **k3d**) and working `kubectl` context.
- The application already deployed to the cluster.
- `curl` available in your shell environment.

Quick connectivity test:
```bash
kubectl config current-context
kubectl cluster-info
kubectl get pods -n default -l app=promotions
````

---

### Quick start

```bash
make verify
```

**Success output (exit code = 0)**

```
• Using KUBECONFIG=/app/kubeconfig
k3d-nyu-devops
• Checking kubectl connectivity...
• Verifying pods are Ready (label=app=promotions, ns=default)...
✓ Pods are Ready
✓ Service exists
✓ Ingress exists
• Port-forwarding promotions-service:8080->80 and curling endpoints...
• Using Host header (if needed): promotions.local
✓ GET /health -> 200
✓ GET /promotions -> 200

✓ All smoke checks passed. ✔
```

---

### Configuration (env vars)

You can override defaults at runtime:

| Variable         | Default              | Description                                                            |
| ---------------- | -------------------- | ---------------------------------------------------------------------- |
| `KUBECONFIG`     | `/app/kubeconfig`    | Path to kubeconfig for `kubectl`.                                      |
| `NS`             | `default`            | Kubernetes namespace to check.                                         |
| `LABEL_SELECTOR` | `app=promotions`     | Label selector for Pods ready check.                                   |
| `SERVICE`        | `promotions-service` | Service name to port-forward.                                          |
| `INGRESS`        | `promotions-ingress` | Ingress name used to auto-detect host.                                 |
| `INGRESS_HOST`   | *(auto-detect)*      | Override Ingress host (falls back to `promotions.local` if not found). |
| `VERIFY_PORT`    | `8080`               | Local port for `kubectl port-forward`.                                 |
| `HEALTH_PATH`    | `/health`            | Health endpoint path.                                                  |
| `PROMO_PATH`     | `/promotions`        | Listing endpoint path.                                                 |

**Examples**

```bash
# Different namespace + label
NS=staging LABEL_SELECTOR="app=promotions" make verify

# Explicit host (bypass auto-detect)
INGRESS_HOST=promotions.local make verify

# Non-default service name / port
SERVICE=promotions-svc VERIFY_PORT=9090 make verify
```

---

### Troubleshooting

* **`kubectl cannot reach the API server`**
  Your kube context isn’t set in this shell. For k3d:

  ```bash
  k3d kubeconfig get nyu-devops > /app/kubeconfig
  export KUBECONFIG=/app/kubeconfig
  kubectl config use-context k3d-nyu-devops
  ```
* **`GET /health -> 404`**
  Your routing is **host-based**. The verify script auto-detects the Ingress host; if detection fails, set it manually:
  `INGRESS_HOST=promotions.local make verify`
* **Port-forward fails or hangs**
  Ensure the Service exists and the Pod is Running; also check if local port `8080` is already in use.
* **Pods not Ready / timeout**
  Inspect events and logs:
  `kubectl describe pod -n $NS -l $LABEL_SELECTOR`
  `kubectl logs -n $NS -l $LABEL_SELECTOR --tail=200`

**Exit codes**
`0` = all checks passed; non-zero = the first failing check’s stage will be printed.

---

### Make Targets (excerpt)

|   Target | Description                                                           |
| -------: | --------------------------------------------------------------------- |
| `verify` | Smoke check the Kubernetes deployment (pods, service, ingress, HTTP). |

---


# Appendix: Minikube Compatibility Notes

This appendix describes how to run the Promotions Service on **Minikube** instead of K3D. It covers image visibility, ingress differences, and fallback access methods.

> Target audience: developers using Minikube locally
> Goal: build an image discoverable by the cluster and access the app via **Ingress** (recommended) or **NodePort/port-forward**.

---

## Prerequisites

* Minikube v1.30+ with a Kubernetes version compatible with your manifests
* `kubectl` installed and pointed at your Minikube context
* (Optional) GNU Make if you use provided `make` targets
* Docker (or container runtime supported by Minikube)

---

## Quick Start (TL;DR)

```bash
# 0) Start Minikube and enable NGINX Ingress
minikube start
minikube addons enable ingress
kubectl wait -n ingress-nginx --for=condition=Ready pods \
  -l app.kubernetes.io/component=controller --timeout=120s

# 1) Make your image visible to Minikube (choose ONE approach below)
#    A) Build inside Minikube’s Docker
eval $(minikube -p minikube docker-env)
# If you have a Makefile build target:
make build
# Or plain Docker (example):
# docker build -t promotions:local .
# (Optional) Restore your shell environment after building:
unset DOCKER_TLS_VERIFY DOCKER_HOST DOCKER_CERT_PATH MINIKUBE_ACTIVE_DOCKERD

#    B) OR: Load an already-built local image into Minikube
# minikube image load promotions:local
# minikube image load cluster-registry:5000/promotions:1.0

#    C) OR: Retag and patch Deployment to use a tag you control (see details below)

# 2) Deploy manifests (same manifests as K3D)
kubectl apply -f k8s/postgres/statefulset.yaml
kubectl apply -f k8s/postgres/service.yaml
kubectl apply -f k8s/secrets/promotions-db.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 3) Ingress for Minikube uses NGINX (not Traefik)
kubectl apply -f k8s/ingress.yaml
# Ensure ingress class is "nginx":
kubectl patch ingress promotions-ingress --type=merge -p '{"spec":{"ingressClassName":"nginx"}}'
# (If your manifest uses the legacy annotation instead, overwrite it:)
kubectl annotate ingress promotions-ingress kubernetes.io/ingress.class=nginx --overwrite

# 4) Add local DNS entry for host routing
echo "$(minikube ip) promotions.local" | sudo tee -a /etc/hosts

# 5) Verify
kubectl rollout status deploy/promotions-deployment
curl -i http://promotions.local/health      # Expect: HTTP/1.1 200 OK
```

---

## Differences vs K3D

| Topic                 | K3D (Course Default)         | Minikube (This Appendix)                           |
| --------------------- | ---------------------------- | -------------------------------------------------- |
| Ingress controller    | Traefik                      | NGINX (via `minikube addons enable ingress`)       |
| Ingress class         | `traefik`                    | `nginx` (patch/annotation may be required)         |
| Registry/image flow   | Push to K3D’s local registry | Build inside Minikube **or** `minikube image load` |
| Hostname resolution   | `/etc/hosts` → K3D LB IP     | `/etc/hosts` → `minikube ip`                       |
| LoadBalancer behavior | Real LB via K3D              | Requires `minikube tunnel` if you use LB services  |

---

## Making Images Visible to Minikube

Choose one of the following:

### A) Build inside Minikube’s Docker (recommended for simplicity)

```bash
eval $(minikube -p minikube docker-env)
# If Makefile exists:
make build
# Or:
# docker build -t promotions:local .
unset DOCKER_TLS_VERIFY DOCKER_HOST DOCKER_CERT_PATH MINIKUBE_ACTIVE_DOCKERD
```

**If you built as `promotions:local`,** ensure your Deployment uses that name:

```bash
kubectl set image deploy/promotions-deployment promotions=promotions:local
```

> Tip: Ensure `imagePullPolicy: IfNotPresent` in your Deployment to avoid unnecessary pulls.

### B) Load a prebuilt image into Minikube

```bash
# Example tags accepted (with or without registry prefixes)
minikube image load promotions:local
minikube image load cluster-registry:5000/promotions:1.0
```

### C) Retag and patch your Deployment image

```bash
# Retag locally (if needed)
# docker tag your/source:tag promotions:local

# Patch the running Deployment to your tag
kubectl set image deploy/promotions-deployment promotions=promotions:local
```

---

## Ingress on Minikube (NGINX)

Enable and wait for the controller:

```bash
minikube addons enable ingress
kubectl wait -n ingress-nginx --for=condition=Ready pods \
  -l app.kubernetes.io/component=controller --timeout=120s
```

Ensure your Ingress resource targets the **nginx** class:

```bash
kubectl patch ingress promotions-ingress --type=merge -p '{"spec":{"ingressClassName":"nginx"}}'
# or (legacy annotation)
kubectl annotate ingress promotions-ingress kubernetes.io/ingress.class=nginx --overwrite
```

Add an `/etc/hosts` entry mapping your Minikube IP to the host used in `ingress.yaml` (e.g., `promotions.local`):

```bash
echo "$(minikube ip) promotions.local" | sudo tee -a /etc/hosts
```

Verify:

```bash
curl -i http://promotions.local/health
curl -i http://promotions.local/promotions
```

> **Note:** You usually do **not** need `minikube tunnel` for NGINX Ingress. Run the tunnel only if you rely on `Service.type=LoadBalancer` elsewhere.

---

## Fallback Access Methods

### Fallback A: NodePort

```bash
kubectl patch svc promotions-service -p '{"spec":{"type":"NodePort"}}'
export NODE_PORT=$(kubectl get svc promotions-service -o jsonpath='{.spec.ports[0].nodePort}')
export NODE_IP=$(minikube ip)
curl -i "http://${NODE_IP}:${NODE_PORT}/health"
```

Or let Minikube print the URL:

```bash
minikube service promotions-service --url
```

### Fallback B: Local port-forward

```bash
kubectl port-forward svc/promotions-service 8080:80
curl -i http://127.0.0.1:8080/health
```

---

## Troubleshooting

* **`ImagePullBackOff` / `ErrImagePull`**

  * Confirm the image tag in the Deployment matches what you built/loaded.
  * Use `kubectl describe pod <pod>` to see which image is being requested.
  * Re-run **A** or **B** above and ensure `imagePullPolicy: IfNotPresent`.

* **Ingress returns 404 (default backend)**

  * Check that the **host** in your Ingress matches `/etc/hosts` (e.g., `promotions.local`).
  * Ensure the **ingress class** is `nginx` (patch/annotate as shown).
  * Verify the `Service` name/port in Ingress backend matches `promotions-service:80`.

* **Database not ready / app CrashLoop**

  * Confirm Postgres StatefulSet is Ready:

    ```bash
    kubectl get pods -l app=postgres
    kubectl logs statefulset/postgres
    ```
  * Ensure DB Secret (`k8s/secrets/promotions-db.yaml`) is applied and env vars match the app.

* **Cannot reach via host name**

  * Re-add hosts mapping: `echo "$(minikube ip) promotions.local" | sudo tee -a /etc/hosts`
  * Test by IP + NodePort to isolate DNS/hosts issues.

---

## Acceptance Checklist (copy/paste)

```bash
# Image is visible to the cluster
kubectl get pods -l app=promotions
kubectl describe pod -l app=promotions | egrep -i 'image:|reason|message'

# Ingress reachable (preferred)
curl -i http://promotions.local/health | head -n 1  # expect 200

# OR NodePort fallback
NODE_IP=$(minikube ip)
NODE_PORT=$(kubectl get svc promotions-service -o jsonpath='{.spec.ports[0].nodePort}')
curl -i "http://${NODE_IP}:${NODE_PORT}/health" | head -n 1  # expect 200

# OR port-forward fallback
kubectl port-forward svc/promotions-service 8080:80 &
sleep 2
curl -i http://127.0.0.1:8080/health | head -n 1      # expect 200
```

---

## Cleanup

```bash
kubectl delete -f k8s/ingress.yaml --ignore-not-found
kubectl delete -f k8s/service.yaml --ignore-not-found
kubectl delete -f k8s/deployment.yaml --ignore-not-found
kubectl delete -f k8s/secrets/promotions-db.yaml --ignore-not-found
kubectl delete -f k8s/postgres/statefulset.yaml --ignore-not-found
kubectl delete -f k8s/postgres/service.yaml --ignore-not-found

# Optional: stop/remove Minikube
minikube stop
# minikube delete
```

---

### Notes

* If your manifests explicitly set `ingressClassName: traefik`, change it to `nginx` for Minikube or use the `kubectl patch` shown above.
* If your K3D flow expects an internal registry (e.g., `cluster-registry:5000/...`), it still works on Minikube as long as you **build inside Minikube** or **load the image** with `minikube image load` using the same tag. Alternatively, retag to `promotions:local` and update the Deployment image.


## License

Copyright (c) 2016, 2025 [John Rofrano](https://www.linkedin.com/in/JohnRofrano/). All rights reserved.


Licensed under the Apache License. See [LICENSE](LICENSE)

This repository is part of the New York University (NYU) masters class: **CSCI-GA.2820-001 DevOps and Agile Methodologies** created and taught by [John Rofrano](https://cs.nyu.edu/~rofrano/), Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.


