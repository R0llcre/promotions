# CHANGELOG.md

## 2025-10-17 Unify Promotion Query Interfaces and Clarify Product ID Semantics

### Added
- Introduced `find_by_product_id(product_id)` method in the Promotion model.
- Added consistent return types for query methods:
  - Single-item queries (`find(id)`) return a single object or `None`.
  - Multiple-item queries (`find_by_name`, `find_by_product_id`, `find_by_promotion_type`) return lists.
- Added support for multiple query filters in the `GET /promotions` endpoint (`?id`, `?name`, `?product_id`, `?promotion_type`).
  - Applied query priority order: `id` > `name` > `product_id` > `promotion_type`.
- Added backward compatibility: `find_by_category` alias method now internally calls `find_by_product_id`.
- Added stricter validation for update operations (`PUT /promotions/<id>`): returns HTTP 400 if payload `id` does not match URL path.
- Improved error handling, allowing `Content-Type` header validation to accept charset parameters (e.g., `application/json; charset=utf-8`).

### Changed
- Renamed ambiguous query parameter `category` to explicit `product_id`.
- Updated `find_by_name` method to return a list instead of a query object.

### Removed
- Removed `find_by_id` method (previously returned a single-element list or empty list). Use `find(id)` instead.

### Fixed
- Ensured robust handling of non-integer and invalid inputs in query methods; invalid inputs now return empty lists or `None` instead of errors.
- Unified database transaction handling in `create`, `update`, and `delete` methods; rollback and raise clear business exceptions if errors occur.

### Example Usage

#### Model queries
```python
# Retrieve by ID (single object or None)
promotion = Promotion.find(42)
if promotion:
    print(promotion.name)

# Retrieve by name (list)
promotions_by_name = Promotion.find_by_name("NYU Demo")
for promo in promotions_by_name:
    print(promo.id)

# Retrieve by product_id (list)
promotions_by_product = Promotion.find_by_product_id("123")
print(len(promotions_by_product))

# Retrieve by promotion_type (list)
promotions_bogo = Promotion.find_by_promotion_type("Buy One Get One")
````

#### HTTP API examples

```bash
# Filter promotions by promotion_type
curl "http://localhost:8080/promotions?promotion_type=Buy%20One%20Get%20One"

# Filter promotions by product_id
curl "http://localhost:8080/promotions?product_id=123"

# Filter promotions by name
curl "http://localhost:8080/promotions?name=OnlyMe"

# Filter promotions by id (single item in array or empty array)
curl "http://localhost:8080/promotions?id=42"

# Create a promotion (charset in Content-Type is accepted)
curl -X POST "http://localhost:8080/promotions" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{"name":"NYU Demo","promotion_type":"AMOUNT_OFF","value":10,"product_id":123,"start_date":"2025-10-01","end_date":"2025-10-31"}'

# Update a promotion (HTTP 400 if URL and payload IDs mismatch)
curl -X PUT "http://localhost:8080/promotions/10" \
  -H "Content-Type: application/json" \
  -d '{"id":11,"name":"Mismatch","promotion_type":"AMOUNT_OFF","value":10,"product_id":123,"start_date":"2025-10-01","end_date":"2025-10-31"}'

# Delete a promotion (204 if exists, 404 if not)
curl -i -X DELETE "http://localhost:8080/promotions/42"
```



## 2025-10-18 Query for Active Promotions

### Added

* **New Query Parameter:** `active=true` for `/promotions` endpoint.

  * Allows marketing managers to retrieve all **currently active promotions** based on the server’s current date.
  * Active promotions are defined as those where `start_date <= today <= end_date`.
  * Returns only promotions active on the current day with `200 OK` response.

* **New Model Method:**

  * `Promotion.find_active(on_date=None)` — retrieves all active promotions as a list.
  * Supports optional `on_date` parameter for testing or future scheduling logic.

### Updated

* **Routes (`list_promotions`)**

  * Added new branch to handle `?active=true` query parameter.
  * Defined clear query priority: `id > active > name > product_id > promotion_type > all`.

* **Tests**

  * Added unit and integration tests covering:

    * Active promotions retrieval.

## 2025-10-18 Deactivate a Promotion

### Added

* **Action endpoint:** `PUT /promotions/{id}/deactivate` to **immediately** stop a running promotion while preserving history.

  * Sets `end_date` to **yesterday** (`today - 1 day`, server date) so, under the inclusive active-window rule (`start_date <= today <= end_date`), the promo is **excluded from “today’s” active list** right away.
  * **Idempotent & safe:** uses `end_date = min(current_end_date, yesterday)` so repeated calls don’t push the date forward, and already expired promos are **not** extended.
  * **No request body** required; returns **200 OK** with the updated resource.
  * Returns **404 Not Found** if the promotion doesn’t exist.

### Rationale

* Managers need to halt flawed or harmful campaigns **immediately** without deleting records.
* Using `yesterday` avoids changing global “active” semantics and achieves instant-effect deactivation with **minimal blast radius**.

### API Contract

* **Request:**
  `PUT /promotions/{id}/deactivate`
* **Success (200):**

  ```json
  {
    "id": 123,
    "name": "Promo X",
    "promotion_type": "Percentage off",
    "value": 10,
    "product_id": 456,
    "start_date": "2025-10-10",
    "end_date": "2025-10-17"   // yesterday (server date - 1)
  }
  ```
* **Errors:**

  * `404 Not Found` – promotion id does not exist
  * `400 Bad Request` – validation/update failure (unlikely in normal use)

### Related Behavior

* `GET /promotions?active=true` uses **server date** and inclusive bounds; after deactivation, the promotion **no longer appears** in the active list **today**.

### Tests

* Added:

  * `test_deactivate_promotion_sets_end_date_to_yesterday_and_excludes_from_active`
  * `test_deactivate_is_idempotent_and_never_extends`
  * `test_deactivate_promotion_not_found`

    
## 2025-10-18 Syntax & Lint Checker

### Added

* **Root script:** `check_syntax.py` to run **Python syntax compilation** and **strict pylint** checks locally and in CI.

  * **Syntax**: concurrently compiles all discovered `*.py` with `py_compile`.
  * **Pylint (strict)**: enabled by default; supports `--pylint-errors-only` for E/F-only mode (pre-commit friendly).
  * **Staged-only mode**: `--staged` analyzes only staged files (`git diff --cached`).
  * **Config auto-detect**: uses project `.pylintrc` or `pyproject.toml` if present.
  * **Robust invocation**: prefers `pylint` binary; falls back to `python -m pylint` if not on PATH.
  * **Exit codes**: non-zero on syntax errors or pylint failures.

### Notes

* Designed to catch issues **before** push/PR; reduces CI churn and review loops.
* No runtime or schema impact (tooling only).
* Ruff is intentionally **not used** by default in this change.

### Usage

```bash
# full repo (strict)
python3 check_syntax.py

# staged only (pre-commit friendly)
python3 check_syntax.py --staged --pylint-errors-only
```

### CI

Ensure `pylint` is installed (e.g., `pip install pylint`) before running the script in CI.

## 2025-10-18 Clarify error semantics & unify API error responses

### ⚠️ Breaking Changes

* **DB commit/constraint/connection failures now result in HTTP 500** instead of 400.
  These server‑side failures are surfaced via a new internal exception `DatabaseError` and handled by the global 500 error handler with a fixed public message. Clients that previously treated these responses as `400 Bad Request` must update their logic to treat them as `500 Internal Server Error`.

### Added

* **`DatabaseError`** (in `service/models.py`) to represent DB operation failures (commit/connection/constraints).
* **Unified error response builder** `_error(status_code, title, message)` (in `service/common/error_handlers.py`) so every handler returns the same JSON shape:

  ```json
  {"status": <int>, "error": "<Title Case>", "message": "<human-readable>"}
  ```
* **405 `Allow` header**: the *Method Not Allowed* handler now includes an `Allow` response header listing permitted methods (detected via `werkzeug.exceptions.MethodNotAllowed`).

### Changed

* **Consistent error titles (Title Case)** across the board:
  *Bad Request*, *Not Found*, *Method Not Allowed*, *Unsupported Media Type*, *Internal Server Error*.
* **415 message improved**: `check_content_type()` now includes the **received** content type (e.g., `"Content-Type must be application/json; received text/plain; charset=utf-8"`).
* **Human‑friendly validation messages** in `deserialize()` (no Python type leakage). Examples:
  `Field 'value' must be an integer`, `Field 'start_date' must be an ISO date (YYYY-MM-DD)`.
* **`create()` now calls `db.session.flush()` before `commit()`** so a primary key `id` is assigned even when `commit()` is mocked (stabilizes tests and aligns runtime behavior).

### Fixed

* **Pylint W0718** in the 405 handler: replaced broad exception catch with explicit `isinstance(error, MethodNotAllowed)` + safe attribute access.

### Security

* **No internal details are leaked on 500** responses anymore. The 500 handlers return a fixed, generic message (`"Internal Server Error" / "An unexpected error occurred."`) while detailed errors are logged server‑side.

### Tests

* Updated model exception tests to expect **`DatabaseError`** (instead of `DataValidationError`) for `create/update/delete` commit failures.
* Overall test coverage remains high; behavior is aligned with the new error semantics.

### Migration Notes

* **Client applications**

  * Treat DB failure responses as **500** (server error) rather than 400.
  * Avoid matching exact error text; rely on the stable JSON shape `{status, error, message}` and HTTP status codes.
  * For 405 responses, you can now use the **`Allow`** header to guide retries.
  * For 415 responses, error messages now include the **actual received** content type to speed up diagnosis.
* **Internal contributors**

  * Use `DatabaseError` only for server‑side DB failures; continue to use `DataValidationError` for request validation errors (400).
  * Keep new error titles in Title Case and construct responses via `_error()` for consistency.


## 2025-10-19 Fix `?active=false` filter

### Fixed

* **`GET /promotions?active=false` now correctly returns the “inactive” set** — promotions that are **not** active today (`today < start_date` **or** `today > end_date`). Previously, `active=false` was ignored or returned all results, causing ambiguity. Implemented in `service/routes.py::list_promotions()`. 

### Added

* **Strict parsing for `?active=`** in `list_promotions()`: accepts only `true/false/1/0/yes/no` (case-insensitive, trims spaces). Any other value returns **400 Bad Request** with a helpful message. 
* **API tests** covering:

  * `active=false` returns only inactive promotions (expired + not-yet-started),
  * invalid values (e.g., `maybe`) produce **400**,
  * truthy/falsy synonyms (`true/false/1/0/yes/no`) behave correctly.
    Added to the REST test suite in `tests/test_routes.py`. 

### Changed

* **Active-window definition remains inclusive** (`start_date <= today <= end_date`) and continues to rely on `Promotion.find_active()`, ensuring route-layer behavior matches model-layer semantics. 

### Notes for Integrators

* Clients relying on permissive/ambiguous `?active=` values (e.g., `maybe`, `t`, `2`) will now receive **400**. Update callers to use one of: `true`, `false`, `1`, `0`, `yes`, `no`. 
* No changes to other query priorities: `id > active > name > product_id > promotion_type > all`. Behavior is unchanged outside the `active` filter. 


## 2025-10-20 — [K8S-01] Add application Dockerfile

### Added

* **Dockerfile (root)**: Production-grade image for the Flask service using `python:3.11-slim`, Pipenv (`--system --deploy`), and **Gunicorn** (`wsgi:app`) on port **8080**.
* **`.dockerignore`**: Reduce build context (ignores VCS, caches, tests, etc.).

### Changed

* *None.* (Packaging only; no app or test code changes.)


### Notes / How to verify

```bash
# Build
docker build -t cluster-registry:5000/promotions:1.0 .

# Run
docker run --rm -p 8080:8080 cluster-registry:5000/promotions:1.0

# Verify (expect 200 + service JSON)
curl -i http://localhost:8080/
```

* CI remains green (lint/tests/coverage unchanged).
* Unblocks: **K8S-02** (Makefile image name), **K8S-04/05/06** (Deployment/Service/Ingress), **K8S-03** (/health).


## 2025-10-20 — [K8S-02] [K8S-03]

### Added
- **K8S-03:** Introduced `GET /health` endpoint for Kubernetes probes.  
  Returns `{"status":"OK"}` with HTTP 200; intentionally lightweight and independent of external dependencies (e.g., DB) to keep liveness/readiness stable.
- **K8S-03 (Tests):** Added unit tests for `/health`:
  - Verifies HTTP 200, `application/json` mimetype, and payload `{"status":"OK"}`.
  - Smoke test for idempotence/lightweight behavior (multiple quick calls).

### Changed
- **K8S-02:** Updated container image name in `Makefile`:
  - `IMAGE_NAME` default changed from `petshop` ➜ `promotions`.
  - Builds and pushes now target `cluster-registry:5000/promotions:1.0`.

### Ops Notes
- Suggested probe configuration (to be used in Deployment manifests):
  ```yaml
  readinessProbe:
    httpGet: { path: /health, port: 8080 }
    initialDelaySeconds: 5
    periodSeconds: 5
  livenessProbe:
    httpGet: { path: /health, port: 8080 }
    initialDelaySeconds: 15
    periodSeconds: 20
  ```

### Impact

* **Build/Push:** Use `make build && make push` to produce and publish `cluster-registry:5000/promotions:1.0`.
* **Runtime:** Probes can safely hit `/health` without flapping due to DB latency.

### Verification

* `pytest -q` passes with coverage unchanged (≥ existing threshold).
* `docker run --rm -p 8080:8080 cluster-registry:5000/promotions:1.0`
  `curl -i http://localhost:8080/health` → `200 OK` with `{"status":"OK"}`.


## 2025-10-20 — Kubernetes Deployment Track [K8S-04] [K8S-05] [K8S-06] [K8S-07] [K8S-08] [K8S-09]

### K8S-04 — Add Deployment for application

**Added**

* `k8s/deployment.yaml`: Application `Deployment` (`app: promotions`), container port **8080**, image `cluster-registry:5000/promotions:1.0`.
* Probes: `readinessProbe` / `livenessProbe` targeting **`/health`** (from K8S-03).

**Changed**

* Env: `FLASK_ENV=production`, `PORT=8080`.
* Temporary hard-coded `DATABASE_URI` to `postgres:5432` (superseded by Secret in K8S-09).

---

### K8S-05 — Add ClusterIP Service for application

**Added**

* `k8s/service.yaml`: `Service` (`name: promotions-service`, `type: ClusterIP`), **`port: 80 → targetPort: http`** (Pod named port maps to 8080).

**Rationale**

* Stable in-cluster endpoint for Ingress; isolates upstream from Pod changes.

---

### K8S-06 — Add Ingress (Traefik / K3D)

**Added**

* `k8s/ingress.yaml`: `Ingress` (`ingressClassName: traefik`, `host: promotions.local`, `path: /` → `promotions-service:80`).

**Docs**

* Access:

  * Quick: `curl -H "Host: promotions.local" http://localhost:8080/...`
  * Or add `127.0.0.1 promotions.local` to `/etc/hosts` (or use `*.nip.io`).

---

### K8S-07 — Add PostgreSQL StatefulSet (+ Headless Service)

**Added**

* `k8s/postgres/statefulset.yaml`:

  * **Headless Service** `postgres-hl` (`clusterIP: None`) for stable identity.
  * **StatefulSet** `postgres` (image `postgres:15-alpine`; `POSTGRES_DB=promotions`; PVC 1Gi).
* Probes: `pg_isready` for readiness/liveness.

**Fixed (CrashLoopBackOff root cause)**

* Data/permissions issues on local paths:

  * **Add** `PGDATA=/var/lib/postgresql/data/pgdata` to avoid `lost+found` at volume root.
  * **Use only** `securityContext.fsGroup: 999` (remove `runAsUser/runAsGroup`) to fix initdb permissions.
* Probe tuning: `pg_isready -h 127.0.0.1 -p 5432 -U postgres -d promotions` with forgiving delays.

**Docs**

* If partial init left bad data, **demo-only** reset: scale sts→delete PVC→scale up.

---

### K8S-08 — Add PostgreSQL ClusterIP Service (app-facing)

**Added**

* `k8s/postgres/service.yaml`: DB `Service` (`name: postgres`, `type: ClusterIP`, `port: 5432 → targetPort: postgres`).

**Rationale**

* Stable app connection endpoint, decoupled from Headless Service; matches `DATABASE_URI` host (`postgres`).

---

### K8S-09 — Harden app bootstrap & move DB URI to Secret

**Added**

* `k8s/secrets/promotions-db.yaml`: `Secret promotions-db` with `stringData.DATABASE_URI=postgresql+psycopg://postgres:postgres@postgres:5432/promotions`.

**Changed**

* `k8s/deployment.yaml`:

  * Switch `env.DATABASE_URI` to `valueFrom.secretKeyRef` (no credentials in spec).
  * **Add** `initContainers.wait-for-postgres` (loop `pg_isready` before app starts).
  * Keep `/health` probes unchanged.

**Outcome**

* Eliminates “app starts before DB” CrashLoop scenario; improves first-boot/rollout stability and credential hygiene.

---

### Impact & Compatibility

* **Runtime**: No API contract changes; `/health` already present (K8S-03).
* **Order of operations**: **DB (K8S-07/08) → Secret (K8S-09) → Deployment (K8S-04 updated) → Service (K8S-05) → Ingress (K8S-06)**.
* **DevContainer note (images)**: If `cluster-registry` isn’t resolvable, prefer `k3d image import` to load images directly into the cluster.

---

### File inventory (added/modified)

**Added**

* `k8s/deployment.yaml` (K8S-04)
* `k8s/service.yaml` (K8S-05)
* `k8s/ingress.yaml` (K8S-06)
* `k8s/postgres/statefulset.yaml` (K8S-07)
* `k8s/postgres/service.yaml` (K8S-08)
* `k8s/secrets/promotions-db.yaml` (K8S-09)

**Modified**

* `k8s/postgres/statefulset.yaml` (K8S-07: add `PGDATA`, `fsGroup`, probe tuning)
* `k8s/deployment.yaml` (K8S-09: `secretKeyRef` + `initContainer`)

**Done criteria**

* `kubectl get pods`: `postgres-0` and app Pod **READY 1/1**
* `curl -H "Host: promotions.local" http://localhost:8080/health` → **200 + {"status":"OK"}**
* App can read/write DB via `/promotions` APIs

**Breaking changes**: None.
