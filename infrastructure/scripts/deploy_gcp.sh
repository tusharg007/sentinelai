#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  AuricVision — GCP Cloud Run Deploy Script
#
#  Usage:
#    ./deploy_gcp.sh <GCP_PROJECT_ID> [IMAGE_TAG]
#
#  Prerequisites:
#    gcloud CLI authenticated  (gcloud auth login)
#    Docker running            (docker ps)
#    Terraform installed       (terraform --version)
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

PROJECT_ID="${1:-}"
TAG="${2:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"
REGION="us-central1"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <GCP_PROJECT_ID> [TAG]"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
API_IMAGE="gcr.io/${PROJECT_ID}/auricvision-api:${TAG}"
UI_IMAGE="gcr.io/${PROJECT_ID}/auricvision-frontend:${TAG}"

echo "════════════════════════════════════════"
echo "  AuricVision — GCP Deploy"
echo "  Project : $PROJECT_ID"
echo "  Tag     : $TAG"
echo "  Region  : $REGION"
echo "════════════════════════════════════════"

# ── 1. Configure gcloud ───────────────────────────────────────
echo "[1/5] Configuring gcloud project…"
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com

# ── 2. Authenticate Docker ────────────────────────────────────
echo "[2/5] Authenticating Docker with GCR…"
gcloud auth configure-docker gcr.io --quiet

# ── 3. Build and push images ──────────────────────────────────
echo "[3/5] Building and pushing API image…"
docker build \
  --platform linux/amd64 \
  -t "$API_IMAGE" \
  "$REPO_ROOT/backend"
docker push "$API_IMAGE"

echo "       Building and pushing Frontend image…"
docker build \
  --platform linux/amd64 \
  -t "$UI_IMAGE" \
  "$REPO_ROOT/frontend"
docker push "$UI_IMAGE"

# ── 4. Terraform apply ────────────────────────────────────────
echo "[4/5] Running Terraform…"
cd "$REPO_ROOT/infrastructure/terraform"
terraform init -input=false
terraform apply \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="image_tag=${TAG}" \
  -auto-approve

# ── 5. Outputs ────────────────────────────────────────────────
echo "[5/5] Retrieving service URLs…"
API_URL=$(terraform output -raw api_url)
UI_URL=$(terraform output -raw frontend_url)

echo ""
echo "════════════════════════════════════════"
echo "  ✅  DEPLOYMENT COMPLETE"
echo "  API : $API_URL"
echo "  UI  : $UI_URL"
echo "  Docs: ${API_URL}/docs"
echo "════════════════════════════════════════"
