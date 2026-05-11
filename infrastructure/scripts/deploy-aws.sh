#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  AuricVision — AWS ECS Fargate Deployment Script
#  Builds, pushes to ECR, and deploys to ECS via Terraform
#
#  Usage: ./deploy-aws.sh --region=us-east-1 [--gpu]
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"
USE_GPU=false

for arg in "$@"; do
  case $arg in
    --region=*) AWS_REGION="${arg#*=}" ;;
    --tag=*)    IMAGE_TAG="${arg#*=}"  ;;
    --gpu)      USE_GPU=true           ;;
  esac
done

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   AuricVision — AWS ECS Fargate Deployment              ║"
echo "╚══════════════════════════════════════════════════════════╝"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# ── ECR login ─────────────────────────────────────────────────────────────
echo "Authenticating with ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${ECR_REGISTRY}"

# ── Create ECR repos if not exist ─────────────────────────────────────────
for repo in "auricvision/backend" "auricvision/frontend"; do
  aws ecr describe-repositories --repository-names "${repo}" --region "${AWS_REGION}" 2>/dev/null || \
    aws ecr create-repository --repository-name "${repo}" --region "${AWS_REGION}" \
      --image-scanning-configuration scanOnPush=true
done

BACKEND_IMAGE="${ECR_REGISTRY}/auricvision/backend:${IMAGE_TAG}"
FRONTEND_IMAGE="${ECR_REGISTRY}/auricvision/frontend:${IMAGE_TAG}"

# ── Build & push ──────────────────────────────────────────────────────────
echo "Building & pushing backend..."
CUDA_ARG="cpu"
[ "${USE_GPU}" = "true" ] && CUDA_ARG="cu121"

docker build --platform linux/amd64 \
  --build-arg CUDA="${CUDA_ARG}" \
  -t "${BACKEND_IMAGE}" \
  -f backend/Dockerfile backend/
docker push "${BACKEND_IMAGE}"

echo "Building & pushing frontend..."
docker build --platform linux/amd64 \
  -t "${FRONTEND_IMAGE}" \
  -f frontend/Dockerfile frontend/
docker push "${FRONTEND_IMAGE}"

# ── Terraform deploy ──────────────────────────────────────────────────────
echo "Applying Terraform..."
cd infrastructure/terraform
terraform init -input=false
terraform apply -auto-approve \
  -var="aws_region=${AWS_REGION}" \
  -var="backend_image=${BACKEND_IMAGE}" \
  -var="frontend_image=${FRONTEND_IMAGE}"

ALB_DNS=$(terraform output -raw alb_dns_name)

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   DEPLOYMENT COMPLETE                                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "  Load Balancer : https://${ALB_DNS}"
echo "  API Docs      : https://${ALB_DNS}/docs"
echo "  Health        : https://${ALB_DNS}/health"
echo ""
echo "  Note: DNS propagation may take 2-5 minutes"
