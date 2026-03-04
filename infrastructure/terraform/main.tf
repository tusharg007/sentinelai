# ═══════════════════════════════════════════════════════════════
#  AuricVision — GCP Cloud Run Deployment (Terraform)
#  Deploys both API backend and frontend UI as Cloud Run services
# ═══════════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "image_tag" {
  description = "Container image tag to deploy"
  type        = string
  default     = "latest"
}

locals {
  api_image      = "gcr.io/${var.project_id}/auricvision-api:${var.image_tag}"
  frontend_image = "gcr.io/${var.project_id}/auricvision-frontend:${var.image_tag}"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable required APIs ──────────────────────────────────────────────────────
resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# ── Artifact Registry repo ────────────────────────────────────────────────────
resource "google_artifact_registry_repository" "auricvision" {
  location      = var.region
  repository_id = "auricvision"
  format        = "DOCKER"
  description   = "AuricVision container images"
  depends_on    = [google_project_service.artifact_registry]
}

# ── Service Account ───────────────────────────────────────────────────────────
resource "google_service_account" "auricvision" {
  account_id   = "auricvision-run"
  display_name = "AuricVision Cloud Run SA"
}

# ── Backend API — Cloud Run Service ──────────────────────────────────────────
resource "google_cloud_run_v2_service" "api" {
  name     = "auricvision-api"
  location = var.region
  depends_on = [google_project_service.run]

  template {
    service_account = google_service_account.auricvision.email

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = local.api_image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
        }
        startup_cpu_boost = true
      }

      env {
        name  = "ENV"
        value = "production"
      }
      env {
        name  = "DEVICE"
        value = "cpu"
      }
      env {
        name  = "ENABLE_MODELS"
        value = "detector,change_backbone"
      }

      startup_probe {
        http_get { path = "/health" port = 8000 }
        initial_delay_seconds = 30
        timeout_seconds       = 10
        period_seconds        = 15
        failure_threshold     = 5
      }

      liveness_probe {
        http_get { path = "/health" port = 8000 }
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    max_instance_request_concurrency = 4
    timeout                          = "120s"
  }
}

# ── Frontend — Cloud Run Service ──────────────────────────────────────────────
resource "google_cloud_run_v2_service" "frontend" {
  name     = "auricvision-ui"
  location = var.region
  depends_on = [google_project_service.run]

  template {
    service_account = google_service_account.auricvision.email

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = local.frontend_image
      ports { container_port = 80 }
      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }
    }
  }
}

# ── Public IAM — allow unauthenticated access ─────────────────────────────────
resource "google_cloud_run_service_iam_member" "api_public" {
  location = var.region
  project  = var.project_id
  service  = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "frontend_public" {
  location = var.region
  project  = var.project_id
  service  = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "api_url" {
  description = "AuricVision API endpoint"
  value       = google_cloud_run_v2_service.api.uri
}

output "frontend_url" {
  description = "AuricVision Operator UI"
  value       = google_cloud_run_v2_service.frontend.uri
}
