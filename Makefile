# These can be overidden with env vars.
REGISTRY ?= cluster-registry:5000
IMAGE_NAME ?= promotions
IMAGE_TAG ?= 1.0
IMAGE ?= $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
PLATFORM ?= "linux/amd64,linux/arm64"
CLUSTER ?= nyu-devops
LOCAL_IMAGE       ?= $(IMAGE_NAME):$(IMAGE_TAG)
REGISTRY_HOST     ?= cluster-registry
REGISTRY_PORT     ?= 5000
REGISTRY_IMAGE     = $(REGISTRY_HOST):$(REGISTRY_PORT)/$(IMAGE_NAME):$(IMAGE_TAG)
.SILENT:

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: all
all: help

##@ Development

.PHONY: clean
clean:	## Removes all dangling build cache
	$(info Removing all dangling build cache..)
	-docker rmi $(IMAGE)
	docker image prune -f
	docker buildx prune -f

.PHONY: install
install: ## Install Python dependencies
	$(info Installing dependencies...)
	sudo pipenv install --system --dev

.PHONY: lint
lint: ## Run the linter
	$(info Running linting...)
	-flake8 service tests --count --select=E9,F63,F7,F82 --show-source --statistics
	-flake8 service tests --count --max-complexity=10 --max-line-length=127 --statistics
	-pylint service tests --max-line-length=127

.PHONY: test
test: ## Run the unit tests
	$(info Running tests...)
	export RETRY_COUNT=1; pytest --pspec --cov=service --cov-fail-under=95 --disable-warnings

.PHONY: run
run: ## Run the service
	$(info Starting service...)
	honcho start

.PHONY: secret
secret: ## Generate a secret hex key
	$(info Generating a new secret key...)
	python3 -c 'import secrets; print(secrets.token_hex())'

##@ Kubernetes

.PHONY: cluster
cluster: ## Create a K3D Kubernetes cluster with load balancer and registry
	$(info Creating Kubernetes cluster $(CLUSTER) with a registry and 2 worker nodes...)
	k3d cluster create $(CLUSTER) --agents 2 --registry-create cluster-registry:0.0.0.0:5000 --port '8080:80@loadbalancer'

.PHONY: cluster-rm
cluster-rm: ## Remove a K3D Kubernetes cluster
	$(info Removing Kubernetes cluster...)
	k3d cluster delete nyu-devops

.PHONY: deploy
deploy: ## Deploy the service on local Kubernetes
	$(info Deploying service locally...)
	kubectl apply -R -f k8s/

############################################################
# COMMANDS FOR BUILDING THE IMAGE
############################################################

##@ Image Build and Push

.PHONY: init
init: export DOCKER_BUILDKIT=1
init:	## Creates the buildx instance
	$(info Initializing Builder...)
	-docker buildx create --use --name=qemu
	docker buildx inspect --bootstrap

.PHONY: build
build:	## Build the project container image for local platform
	$(info Building $(IMAGE)...)
	docker build --rm --pull --tag $(IMAGE) .


.PHONY: push
push: ## Push to registry; on failure, fall back to k3d image import
	@set -eu; \
	echo "Tagging $(LOCAL_IMAGE) -> $(REGISTRY_IMAGE)"; \
	docker tag "$(LOCAL_IMAGE)" "$(REGISTRY_IMAGE)" || true; \
	echo "Pushing $(REGISTRY_IMAGE)..."; \
	if docker push "$(REGISTRY_IMAGE)"; then \
	  echo "Pushed to registry OK."; \
	else \
	  echo "Registry not reachable; falling back to k3d image import…"; \
	  k3d image import -c "$(CLUSTER)" "$(REGISTRY_IMAGE)"; \
	  echo "Imported $(REGISTRY_IMAGE) into cluster $(CLUSTER)."; \
	fi

.PHONY: push-import
push-import: ## Force k3d image import (skip registry entirely)
	@set -eu; \
	docker tag "$(LOCAL_IMAGE)" "$(REGISTRY_IMAGE)" || true; \
	k3d image import -c "$(CLUSTER)" "$(REGISTRY_IMAGE)"

.PHONY: buildx
buildx:	## Build multi-platform image with buildx
	$(info Building multi-platform image $(IMAGE) for $(PLATFORM)...)
	docker buildx build --file Dockerfile --pull --platform=$(PLATFORM) --tag $(IMAGE) --push .

.PHONY: remove
remove:	## Stop and remove the buildx builder
	$(info Stopping and removing the builder image...)
	docker buildx stop
	docker buildx rm

# R4 BDD
PORT ?= 8080
BASE_URL ?= http://localhost:$(PORT)
LOCAL_PORT ?= 8088
.PHONY: bdd-setup run stop bdd pf
bdd-setup: ## Install Chromium & chromedriver for headless BDD
	@echo "Installing Chromium + chromedriver..."
	sudo apt-get update
	sudo apt-get install -y chromium chromium-driver fonts-liberation
	-which chromium || which chromium-browser || true
	-which chromedriver || true
run: ## Run the app locally on PORT (default 8080)
	@echo "Starting app on http://localhost:$(PORT)"
	pipenv run gunicorn --bind 0.0.0.0:$(PORT) wsgi:app
stop: ## Stop any process listening on PORT (default 8080)
	@echo "Stopping process on :$(PORT) (if any) ..."
	-ss -ltnp | awk '/:$(PORT)\b/{print $$7}' | cut -d',' -f1 | sed 's/[^0-9]//g' | xargs -r kill
bdd: ## Run behave against BASE_URL (default http://localhost:$(PORT))
	@echo "Running BDD against $(BASE_URL)"
	BASE_URL=$(BASE_URL) behave
pf: ## kubectl port-forward svc/promotions-service -> localhost:LOCAL_PORT
	@echo "Port-forwarding svc/promotions-service 80 -> localhost:$(LOCAL_PORT)"
	kubectl port-forward svc/promotions-service $(LOCAL_PORT):80

.PHONY: verify
verify: ## Smoke check the Kubernetes deployment (pods, service, ingress, HTTP)
	@bash -eu -o pipefail -c '\
	: "$${KUBECONFIG:=/app/kubeconfig}"; \
	NS="$${NS:-default}"; \
	LABEL_SELECTOR="$${LABEL_SELECTOR:-app=promotions}"; \
	SERVICE="$${SERVICE:-promotions-service}"; \
	INGRESS="$${INGRESS:-promotions-ingress}"; \
	VERIFY_PORT="$${VERIFY_PORT:-8080}"; \
	HEALTH_PATH="$${HEALTH_PATH:-/health}"; \
	PROMO_PATH="$${PROMO_PATH:-/promotions}"; \
	printf "• Using KUBECONFIG=%s\n" "$$KUBECONFIG"; \
	kubectl config current-context || true; \
	printf "• Checking kubectl connectivity...\n"; \
	kubectl cluster-info >/dev/null 2>&1 || kubectl get --raw=/version >/dev/null 2>&1 || { printf "✗ kubectl cannot reach the API server\n"; exit 1; }; \
	printf "• Verifying pods are Ready (label=%s, ns=%s)...\n" "$$LABEL_SELECTOR" "$$NS"; \
	kubectl get pods -n "$$NS" -l "$$LABEL_SELECTOR" --no-headers || true; \
	kubectl wait --for=condition=Ready --timeout=60s -n "$$NS" pod -l "$$LABEL_SELECTOR" >/dev/null; \
	printf "✓ Pods are Ready\n"; \
	printf "• Checking Service %s in namespace %s...\n" "$$SERVICE" "$$NS"; \
	kubectl get svc "$$SERVICE" -n "$$NS" >/dev/null; \
	printf "✓ Service exists\n"; \
	printf "• Checking Ingress %s in namespace %s...\n" "$$INGRESS" "$$NS"; \
	kubectl get ingress "$$INGRESS" -n "$$NS" >/dev/null; \
	printf "✓ Ingress exists\n"; \
	printf "• Port-forwarding %s:%s->80 and curling endpoints...\n" "$$SERVICE" "$$VERIFY_PORT"; \
	KPF_LOG="$$(mktemp)"; \
	kubectl port-forward -n "$$NS" svc/"$$SERVICE" "$$VERIFY_PORT":80 >"$$KPF_LOG" 2>&1 & \
	PF_PID=$$!; \
	\
	INGRESS_HOST="$${INGRESS_HOST:-$$(kubectl get ingress "$$INGRESS" -n "$$NS" -o jsonpath="{.spec.rules[0].host}" 2>/dev/null || true)}"; \
	if [ -z "$$INGRESS_HOST" ]; then INGRESS_HOST="promotions.local"; fi; \
	printf "• Using Host header (if needed): %s\n" "$$INGRESS_HOST"; \
	\
	for i in $$(seq 1 30); do \
	  curl -sS -o /dev/null -H "Host: $$INGRESS_HOST" "http://127.0.0.1:$$VERIFY_PORT/" && break; \
	  sleep 1; \
	done; \
	trap "kill $$PF_PID >/dev/null 2>&1 || true" EXIT; \
	\
	code="$$(curl -sS -o /dev/null -w "%{http_code}" "http://127.0.0.1:$$VERIFY_PORT$$HEALTH_PATH")"; \
	if [ "$$code" != 200 ]; then \
	  code="$$(curl -sS -H "Host: $$INGRESS_HOST" -o /dev/null -w "%{http_code}" "http://127.0.0.1:$$VERIFY_PORT$$HEALTH_PATH")"; \
	fi; \
	[ "$$code" = 200 ] || { printf "✗ GET %s -> %s (Host: %s)\n" "$$HEALTH_PATH" "$$code" "$$INGRESS_HOST"; exit 1; }; \
	printf "✓ GET %s -> 200\n" "$$HEALTH_PATH"; \
	\
	code="$$(curl -sS -o /dev/null -w "%{http_code}" "http://127.0.0.1:$$VERIFY_PORT$$PROMO_PATH")"; \
	if [ "$$code" != 200 ]; then \
	  code="$$(curl -sS -H "Host: $$INGRESS_HOST" -o /dev/null -w "%{http_code}" "http://127.0.0.1:$$VERIFY_PORT$$PROMO_PATH")"; \
	fi; \
	[ "$$code" = 200 ] || { printf "✗ GET %s -> %s (Host: %s)\n" "$$PROMO_PATH" "$$code" "$$INGRESS_HOST"; exit 1; }; \
	printf "✓ GET %s -> 200\n" "$$PROMO_PATH"; \
	\
	kill $$PF_PID >/dev/null 2>&1 || true; \
	trap - EXIT; \
	printf "\n✓ All smoke checks passed. ✔\n"; \
	'
