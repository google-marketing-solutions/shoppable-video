# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# you may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# terraform/modules/webapp/backend/main.tf

# ------------------------------------------------------------------------------
# CLOUD RUN SERVICE
# ------------------------------------------------------------------------------
# Deploys the application as a Cloud Run v2 Service.
# This resource manages the container configuration, scaling, and networking settings.
# ------------------------------------------------------------------------------

resource "google_project_service" "project" {
  project = var.project_id
  service = "iap.googleapis.com"
}

resource "google_cloud_run_v2_service" "default" {
  name                = "${var.app_name}-api"
  location            = var.region
  project             = var.project_id
  deletion_protection = false

  # Restricts ingress to 'Internal Load Balancing' only.
  # This prevents direct public access to the Cloud Run URL, enforcing WAF usage.
  ingress = var.ingress_style

  labels = var.labels

  # --------------------------------------------------------------------------
  # AUTO-SCALING CONFIGURATION
  # --------------------------------------------------------------------------
  # Dynamic scaling logic based on variables.
  # --------------------------------------------------------------------------
  scaling {
    max_instance_count = var.scaling_config.max_instance_count
    min_instance_count = var.scaling_config.min_instance_count
  }

  template {
    service_account = var.service_account_email

    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

    containers {
      image = var.docker_image

      resources {
        limits = {
          cpu    = var.resource_limits.cpu
          memory = var.resource_limits.memory
        }
        cpu_idle          = true # "true" = cheaper (CPU only during requests).
        startup_cpu_boost = true # (Optional, often on by default in GUI but good to know).
      }

      # If var...command is null, this line is ignored -> Dockerfile ENTRYPOINT used.
      command = var.container_override.command

      # If var...args is null, this line is ignored -> Dockerfile CMD used.
      args = var.container_override.args

      # Dynamically injects secrets as environment variables.
      dynamic "env" {
        for_each = var.secret_ids
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret_id # Access the ID.
              version = env.value.version   # Access the specific version (or default 'latest').
            }
          }
        }
      }

      # Dynamically injects extra environment variables.
      dynamic "env" {
        for_each = var.extra_env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      # Sets standard non-sensitive configuration.
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "LB_DOMAIN"
        value = var.lb_domain
      }
      env {
        name  = "FRONTEND_URL"
        value = var.frontend_url
      }
      env {
        name  = "LOG_LEVEL"
        value = "debug"
      }
      env {
        name  = "ACCESS_LOG"
        value = "-"
      }
    }

    labels = var.labels
  }
}

resource "google_project_service_identity" "iap_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "iap.googleapis.com"
}

resource "google_cloud_run_v2_service_iam_member" "iap_invoker" {
  provider = google-beta
  project  = google_cloud_run_v2_service.default.project
  location = google_cloud_run_v2_service.default.location
  name     = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_project_service_identity.iap_sa.email}"
}
