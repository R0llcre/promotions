# K3D Local Cluster — One‑Pager

This is a **safe, minimal guide** to create and remove a local Kubernetes cluster using **[k3d](https://k3d.io/)** and the project's `Makefile`.

> **You’ll learn:** how to create the cluster with `make`, what registry we use, how port **8080** is mapped, and how to clean up **safely**.

---

## Prerequisites

- Docker running
- `k3d` installed
- `kubectl` installed

> Verify: `docker version`, `k3d version`, `kubectl version --client`

---

## TL;DR

```bash
# 1) Create cluster (1 server + 2 workers) + registry + LB mapping
make cluster

# 2) Deploy/verify (example commands)
kubectl get nodes
kubectl get ingress
curl -i -H "Host: promotions.local" http://127.0.0.1:8080/health

# 3) Remove the cluster (see ⚠️ cleanup risks below)
make cluster-rm
````

---

## What `make cluster` does

The `Makefile` creates a K3D cluster named by `CLUSTER` (default **nyu-devops**) with **2 agent nodes**, a local **Docker registry**, and a load‑balancer port mapping:

```make
k3d cluster create $(CLUSTER) \
  --agents 2 \
  --registry-create cluster-registry:0.0.0.0:5000 \
  --port '8080:80@loadbalancer'
```

### Load Balancer (LB) mapping

* **Host → Cluster**: `127.0.0.1:8080` → LB port `80`
* Our `k8s/ingress.yaml` uses host **promotions.local** with Traefik.
* From your host you can either:

  * use a Host header:
    `curl -H "Host: promotions.local" http://127.0.0.1:8080/`
  * *or* add `127.0.0.1 promotions.local` to your `/etc/hosts` and visit `http://promotions.local:8080/` in a browser.

> If **8080** is already in use, `make cluster` will fail to bind. Free the port or (advanced) change the mapping in the Makefile.

---

## The local registry (`cluster-registry:5000`)

`make cluster` also creates a Docker registry that the cluster can pull from.

**Defaults from the Makefile:**

| Variable         | Default                                                        | Meaning                                       |
| ---------------- | -------------------------------------------------------------- | --------------------------------------------- |
| `CLUSTER`        | `nyu-devops`                                                   | Cluster name                                  |
| `REGISTRY_HOST`  | `cluster-registry`                                             | Registry hostname (inside docker/k3d network) |
| `REGISTRY_PORT`  | `5000`                                                         | Registry port                                 |
| `REGISTRY`       | `cluster-registry:5000`                                        | Host:port pair                                |
| `IMAGE_NAME`     | `promotions`                                                   | Image repository name                         |
| `IMAGE_TAG`      | `1.0`                                                          | Image tag                                     |
| `REGISTRY_IMAGE` | `$(REGISTRY_HOST):$(REGISTRY_PORT)/$(IMAGE_NAME):$(IMAGE_TAG)` | Fully qualified image ref                     |
| `LOCAL_IMAGE`    | `$(IMAGE_NAME):$(IMAGE_TAG)`                                   | Local image ref                               |

### Build & load your image into the cluster

```bash
# Build local image (tag: ${IMAGE_NAME}:${IMAGE_TAG})
make build

# Push to registry; on failure it automatically falls back to:
#   k3d image import -c "${CLUSTER}" "${REGISTRY_IMAGE}"
make push
```

> Many hosts cannot resolve `cluster-registry` by name. That’s OK — the **`make push`** target tries a `docker push` first and **automatically falls back** to `k3d image import` so the image still lands inside the cluster.

You can override variables on the command line:

```bash
make push IMAGE_TAG=dev CLUSTER=mydev
```

---

## Cleanup (read this before running `make cluster-rm`)

```bash
make cluster-rm
```

This target **deletes the k3d cluster** and all Kubernetes state (deployments, services, PVC data stored on the k3d node volumes, etc.).

> ⚠️ **Important risk #1 — hard‑coded name**
> The current `cluster-rm` target deletes the **`nyu-devops`** cluster explicitly (it does **not** use `$(CLUSTER)`). If you created a cluster with a different name, `make cluster-rm` will **not** remove it, and it **will** remove `nyu-devops` if that exists.

> ⚠️ **Important risk #2 — data loss**
> Removing the cluster destroys **all in‑cluster state**. Any ephemeral data (e.g., emptyDir or local host‑path volumes) is lost.

> ⚠️ **Important risk #3 — registry lifecycle**
> The registry created by `--registry-create cluster-registry:0.0.0.0:5000` may **outlive the cluster**. If port 5000 remains in use or you need a clean slate, remove the registry explicitly:
>
> ```bash
> k3d registry list
> k3d registry delete cluster-registry
> # (or docker rm -f <container> as a last resort)
> ```

**Safe checklist before cleanup**

* `k3d cluster list` → confirm the exact cluster name you intend to delete
* `kubectl get pvc -A` → snapshot/migrate anything you need
* Optional: `k3d registry list` → decide whether to delete the registry

---

## Quick verify

```bash
k3d cluster list
kubectl get nodes
kubectl -n default get deploy,svc,ingress
curl -i -H "Host: promotions.local" http://127.0.0.1:8080/health
```

You should see HTTP **200** from `/health`.

---

## Appendix — Makefile snippets (for reference)

* Cluster create: `k3d cluster create $(CLUSTER) --agents 2 --registry-create cluster-registry:0.0.0.0:5000 --port '8080:80@loadbalancer'`
* Cluster remove: `k3d cluster delete nyu-devops`
* Push with fallback: tags image as `$(REGISTRY_IMAGE)`, tries `docker push`, then falls back to `k3d image import -c "$(CLUSTER)" "$(REGISTRY_IMAGE)"`.


