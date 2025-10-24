# E2E Dry Run — Cluster → Build → Push → Deploy → Curl

**Date:** 2025-10-20T16:12:06+00:00
**Cluster:** nyu-devops
**Namespace:** default

## Summary

- [x] Cluster created
- [x] Image built & pushed
- [x] Manifests deployed
- [x] Pods Ready
- [x] `GET /health` via Ingress → **200**
- [x] `GET /promotions` via Ingress → **200**

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
NAME                                    READY   STATUS    RESTARTS   AGE   IP          NODE                     NOMINATED NODE   READINESS GATES
promotions-deployment-8b467dd9b-bghpv   1/1     Running   0          25s   10.42.2.3   k3d-nyu-devops-agent-1   <none>           <none>
```

### Service
```
NAME                 TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE   SELECTOR
promotions-service   ClusterIP   10.43.152.122   <none>        80/TCP    25s   app=promotions
```

### Ingress
```
NAME                 CLASS     HOSTS              ADDRESS                            PORTS   AGE
promotions-ingress   traefik   promotions.local   172.19.0.2,172.19.0.3,172.19.0.4   80      25s
```

<details>
<summary>Describe Ingress</summary>

```
NAME                 CLASS     HOSTS              ADDRESS                            PORTS   AGE
promotions-ingress   traefik   promotions.local   172.19.0.2,172.19.0.3,172.19.0.4   80      25s_DESCR
```

</details>

## HTTP Checks (via Ingress)

### GET /health
```
HTTP/1.1 200 OK
Content-Length: 16
Content-Type: application/json
Date: Mon, 20 Oct 2025 16:12:06 GMT
Server: gunicorn

{"status":"OK"}
```

### GET /promotions
```
HTTP/1.1 200 OK
Content-Length: 3
Content-Type: application/json
Date: Mon, 20 Oct 2025 16:12:06 GMT
Server: gunicorn

[]
```

## Notes / Issues / Fixes
- REPLACE_NOTES
