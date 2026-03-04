#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  AuricVision — GCP Cloud Run Deployment Script
#  Deploys backend API to Google Cloud Run (GPU-enabled if available)
#
#  Requirements: gcloud CLI authenticated, Docker installed
#  Usage: ./deploy-gcp.sh --project=my-gcp-project [--gpu]
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────────
GCP_PROJECT="${GCP_PROJECT:-your-gcp-project-id}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="auricvision-backend"
FRONTEND_SERVICE="auricvision-frontend"
ARTIFACT_REPO="auricvision"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"
BACKEND_IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${ARTIFACT_REPO}/backend:${IMAGE_TAG}"
FRONTEND_IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${ARTIFACT_REPO}/frontend:${IMAGE_TAG}"
USE_GPU=false

# Parse args
for arg in "$@"; do
  case $arg in
    --project=*) GCP_PROJECT="${arg#*=}" ;;
    --region=*)  GCP_REGION="${arg#*=}"  ;;
    --gpu)       USE_GPU=true            ;;
    --tag=*)     IMAGE_TAG="${arg#*=}"   ;;
  esac
done

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   AuricVision — GCP Cloud Run Deployment                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "  Project   : ${GCP_PROJECT}"
echo "  Region    : ${GCP_REGION}"
echo "  Tag       : ${IMAGE_TAG}"
echo "  GPU       : ${USE_GPU}"

# ── Authenticate & Configure ───────────────────────────────────────────────
gcloud config set project "${GCP_PROJECT}"
gcloud config set run/region "${GCP_REGION}"
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

# ── Create Artifact Registry (idempotent) ─────────────────────────────────
gcloud artifacts repositories create "${ARTIFACT_REPO}" \
  --repository-format=docker \
  --location="${GCP_REGION}" \
  --description="AuricVision Docker images" \
  2>/dev/null || echo "Artifact repo already exists"

# ── Enable required APIs ───────────────────────────────────────────────────
echo "Enabling GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  --quiet

# ── Build & Push Backend ───────────────────────────────────────────────────
echo "Building backend image..."
docker build \
  --platform linux/amd64 \
  --build-arg CUDA=cpu \
  -t "${BACKEND_IMAGE}" \
  -f backend/Dockerfile \
  backend/

echo "Pushing backend image..."
docker push "${BACKEND_IMAGE}"

# ── Build & Push Frontend ──────────────────────────────────────────────────
echo "Building frontend image..."
docker build \
  --platform linux/amd64 \
  -t "${FRONTEND_IMAGE}" \
  -f frontend/Dockerfile \
  frontend/

echo "Pushing frontend image..."
docker push "${FRONTEND_IMAGE}"

# ── Store secrets in Secret Manager ───────────────────────────────────────
echo "Setting up secrets..."
echo -n "${SECRET_KEY:-$(openssl rand -hex 32)}" | \
  gcloud secrets create auricvision-secret-key --data-file=- 2>/dev/null || \
  echo -n "${SECRET_KEY:-$(openssl rand -hex 32)}" | \
  gcloud secrets versions add auricvision-secret-key --data-file=-

# ── Deploy Backend to Cloud Run ────────────────────────────────────────────
echo "Deploying backend to Cloud Run..."
DEPLOY_ARGS=(
  "--image=${BACKEND_IMAGE}"
  "--platform=managed"
  "--region=${GCP_REGION}"
  "--allow-unauthenticated"
  "--memory=8Gi"
  "--cpu=4"
  "--timeout=120s"
  "--max-instances=10"
  "--min-instances=1"
  "--concurrency=4"
  "--port=8000"
  "--set-env-vars=ENVIRONMENT=production,DEVICE=cpu"
  "--set-secrets=SECRET_KEY=auricvision-secret-key:latest"
)

if [ "${USE_GPU}" = "true" ]; then
  DEPLOY_ARGS+=(
    "--gpu=1"
    "--gpu-type=nvidia-l4"
    "--memory=16Gi"
    "--cpu=8"
  )
  DEPLOY_ARGS=("${DEPLOY_ARGS[@]/--set-env-vars=ENVIRONMENT=production,DEVICE=cpu/--set-env-vars=ENVIRONMENT=production,DEVICE=cuda}")
fi

gcloud run deploy "${SERVICE_NAME}" "${DEPLOY_ARGS[@]}"

# Get backend URL
BACKEND_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --platform=managed --region="${GCP_REGION}" \
  --format="value(status.url)")
echo "Backend deployed: ${BACKEND_URL}"

# ── Deploy Frontend ────────────────────────────────────────────────────────
echo "Deploying frontend to Cloud Run..."
gcloud run deploy "${FRONTEND_SERVICE}" \
  --image="${FRONTEND_IMAGE}" \
  --platform=managed \
  --region="${GCP_REGION}" \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --max-instances=5 \
  --port=80

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
  --platform=managed --region="${GCP_REGION}" \
  --format="value(status.url)")

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   DEPLOYMENT COMPLETE                                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "  Backend  : ${BACKEND_URL}"
echo "  Frontend : ${FRONTEND_URL}"
echo "  API Docs : ${BACKEND_URL}/docs"
echo "  Health   : ${BACKEND_URL}/health"
