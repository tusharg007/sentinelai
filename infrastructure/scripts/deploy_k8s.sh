#!/usr/bin/env bash
# Kubernetes deploy script (GKE / EKS / AKS)
set -euo pipefail

PROJECT_ID="${1:-}"
CLUSTER="${2:-auricvision-cluster}"
ZONE="${3:-us-central1-a}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <GCP_PROJECT_ID> [CLUSTER_NAME] [ZONE]"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAG="$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')"

echo "Connecting to cluster ${CLUSTER}…"
gcloud container clusters get-credentials "$CLUSTER" \
  --zone "$ZONE" --project "$PROJECT_ID"

echo "Updating image tags…"
sed -i "s|gcr.io/YOUR_PROJECT/auricvision-api:latest|gcr.io/${PROJECT_ID}/auricvision-api:${TAG}|g" \
  "$REPO_ROOT/infrastructure/k8s/api-deployment.yaml"
sed -i "s|gcr.io/YOUR_PROJECT/auricvision-frontend:latest|gcr.io/${PROJECT_ID}/auricvision-frontend:${TAG}|g" \
  "$REPO_ROOT/infrastructure/k8s/frontend-deployment.yaml"

echo "Applying manifests…"
kubectl apply -f "$REPO_ROOT/infrastructure/k8s/"

echo "Waiting for rollout…"
kubectl rollout status deployment/auricvision-api -n auricvision --timeout=300s
kubectl rollout status deployment/auricvision-frontend -n auricvision --timeout=120s

echo "✅  Kubernetes deploy complete."
kubectl get pods -n auricvision
