#!/usr/bin/env bash
# End-to-End dry run for: cluster → build → push → deploy → curl
# This script captures outputs into docs/e2e-notes.md
# Usage:
#   chmod +x scripts/e2e-dry-run.sh
#   ./scripts/e2e-dry-run.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="${REPO_ROOT}/docs"
NOTES_FILE="${DOCS_DIR}/e2e-notes.md"

# --- Config (override via env if needed) ---
CLUSTER="${CLUSTER:-nyu-devops}"
NS="${NS:-default}"
APP_LABEL="${APP_LABEL:-app=promotions}"
DEPLOYMENT="${DEPLOYMENT:-promotions-deployment}"
SERVICE="${SERVICE:-promotions-service}"
INGRESS="${INGRESS:-promotions-ingress}"
VERIFY_PORT="${VERIFY_PORT:-8080}"          # host port mapped to k3d load balancer (see Makefile cluster target)
HEALTH_PATH="${HEALTH_PATH:-/health}"
PROMO_PATH="${PROMO_PATH:-/promotions}"
TIMEOUT="${TIMEOUT:-180s}"                  # rollout/wait timeout

# Resolve ingress host from cluster (fallback to promotions.local)
INGRESS_HOST="$(kubectl get ingress "${INGRESS}" -n "${NS}" -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo '')"
if [[ -z "${INGRESS_HOST}" ]]; then
  INGRESS_HOST="promotions.local"
fi

# Pre-flight checks
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1"; exit 1; }; }
need docker
need k3d
need kubectl
need curl
need make

mkdir -p "${DOCS_DIR}"
echo "Starting E2E dry run at $(date -Is)"

# Start fresh: remove any existing cluster, prune local image (optional)
{
  make cluster-rm || true
} || true

# 1) Create cluster (with registry + load balancer on :8080)
make cluster

# 2) Clean & build image
make clean || true
make build

# 3) Push image to local registry (k3d import fallback handled in Makefile)
make push || true

# 4) Deploy manifests
make deploy

# 5) Rollout & readiness checks
kubectl -n "${NS}" rollout status deploy/"${DEPLOYMENT}" --timeout="${TIMEOUT}"
kubectl -n "${NS}" wait --for=condition=Ready pod -l "${APP_LABEL}" --timeout="${TIMEOUT}"

# Kubernetes state snapshots
PODS="$(kubectl -n "${NS}" get pods -l "${APP_LABEL}" -o wide)"
SVC="$(kubectl -n "${NS}" get svc "${SERVICE}" -o wide)"
ING="$(kubectl -n "${NS}" get ingress "${INGRESS}" -o wide || true)"
ING_DESCR="$(kubectl -n "${NS}" describe ingress "${INGRESS}" || true)"

# 6) Ingress verification (via k3d load balancer on 127.0.0.1:${VERIFY_PORT})
BASE_URL="http://127.0.0.1:${VERIFY_PORT}"
HEALTH_CODE="$(curl -sS -o /dev/null -w "%{http_code}" -H "Host: ${INGRESS_HOST}" "${BASE_URL}${HEALTH_PATH}")"
PROMO_CODE="$(curl -sS -o /dev/null -w "%{http_code}" -H "Host: ${INGRESS_HOST}" "${BASE_URL}${PROMO_PATH}")"

HEALTH_RAW="$(curl -sS -i -H "Host: ${INGRESS_HOST}" "${BASE_URL}${HEALTH_PATH}" || true)"
PROMO_RAW="$(curl -sS -i -H "Host: ${INGRESS_HOST}" "${BASE_URL}${PROMO_PATH}" || true)"

# Export variables so Python heredoc can read them from the environment
export CLUSTER NS APP_LABEL DEPLOYMENT SERVICE INGRESS VERIFY_PORT HEALTH_PATH PROMO_PATH INGRESS_HOST
export PODS SVC ING ING_DESCR HEALTH_CODE PROMO_CODE HEALTH_RAW PROMO_RAW

# 7) Write docs/e2e-notes.md with Python (safer than sed for multi-line text)
cat > "${NOTES_FILE}" <<'MD'
# E2E Dry Run — Cluster → Build → Push → Deploy → Curl

**Date:** REPLACE_DATE
**Cluster:** REPLACE_CLUSTER
**Namespace:** REPLACE_NS

## Summary

- [x] Cluster created
- [x] Image built & pushed
- [x] Manifests deployed
- [x] Pods Ready
- [REPLACE_HEALTH_CHECK] `GET /health` via Ingress → **REPLACE_HEALTH_CODE**
- [REPLACE_PROMO_CHECK] `GET /promotions` via Ingress → **REPLACE_PROMO_CODE**

## How to reproduce

```bash
make cluster
make build
make push
make deploy
# via Ingress (k3d load balancer on localhost:8080; Host header routes to our rule)
curl -i -H "Host: promotions.local" http://127.0.0.1:8080/health
curl -i -H "Host: promotions.local" http://127.0.0.1:8080/promotions
```

> If you prefer not to set `/etc/hosts`, keep the `-H "Host: promotions.local"` header.
> Alternatively, add `127.0.0.1 promotions.local` to `/etc/hosts` and use `curl -i http://promotions.local:8080/health`.

## Kubernetes State

### Pods
```
REPLACE_PODS
```

### Service
```
REPLACE_SVC
```

### Ingress
```
REPLACE_ING
```

<details>
<summary>Describe Ingress</summary>

```
REPLACE_ING_DESCR
```

</details>

## HTTP Checks (via Ingress)

### GET /health
```
REPLACE_HEALTH_RAW
```

### GET /promotions
```
REPLACE_PROMO_RAW
```

## Notes / Issues / Fixes
- REPLACE_NOTES
MD

python3 - "$NOTES_FILE" <<'PY'
import os, sys
file = sys.argv[1]
with open(file, "r", encoding="utf-8") as f:
    s = f.read()

repls = {
  "REPLACE_DATE": os.popen("date -Is").read().strip(),
  "REPLACE_CLUSTER": os.environ.get("CLUSTER",""),
  "REPLACE_NS": os.environ.get("NS",""),
  "REPLACE_PODS": os.popen("printf \"%s\" \"$PODS\"").read(),
  "REPLACE_SVC": os.popen("printf \"%s\" \"$SVC\"").read(),
  "REPLACE_ING": os.popen("printf \"%s\" \"$ING\"").read(),
  "REPLACE_ING_DESCR": os.popen("printf \"%s\" \"$ING_DESCR\"").read(),
  "REPLACE_HEALTH_CODE": os.environ.get("HEALTH_CODE",""),
  "REPLACE_PROMO_CODE": os.environ.get("PROMO_CODE",""),
  "REPLACE_HEALTH_RAW": os.popen("printf \"%s\" \"$HEALTH_RAW\"").read(),
  "REPLACE_PROMO_RAW": os.popen("printf \"%s\" \"$PROMO_RAW\"").read(),
}

for k, v in repls.items():
    s = s.replace(k, v)

# tick the checkboxes depending on 200
if os.environ.get("HEALTH_CODE") == "200":
    s = s.replace("[REPLACE_HEALTH_CHECK]", "[x]")
else:
    s = s.replace("[REPLACE_HEALTH_CHECK]", "[ ]")
if os.environ.get("PROMO_CODE") == "200":
    s = s.replace("[REPLACE_PROMO_CHECK]", "[x]")
else:
    s = s.replace("[REPLACE_PROMO_CHECK]", "[ ]")

with open(file, "w", encoding="utf-8") as f:
    f.write(s)
PY

echo
if [[ "${HEALTH_CODE}" == "200" && "${PROMO_CODE}" == "200" ]]; then
  echo "✓ All checks passed (Ingress HTTP 200). Notes written to: ${NOTES_FILE}"
else
  echo "✗ One or more checks failed. See ${NOTES_FILE} for details."
  exit 1
fi
