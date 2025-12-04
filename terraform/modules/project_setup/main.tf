# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ------------------------------------------------------------------------------
# IAM & SERVICE ACCOUNT
# ------------------------------------------------------------------------------

resource "google_project_service" "enable_apis" {
  for_each = toset([
    "aiplatform.googleapis.com",
    "apikeys.googleapis.com",
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "bigquerydatatransfer.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudtasks.googleapis.com",
    "generativelanguage.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sheets.googleapis.com",
    "storage.googleapis.com",
    "youtube.googleapis.com"
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_service_account" "service_account" {
  account_id   = var.service_account_id
  display_name = "Shoppable Video Service Account"
  depends_on   = [google_project_service.enable_apis]
}

resource "google_project_iam_member" "project" {
  for_each = toset([
    "roles/bigquery.dataOwner",
    "roles/bigquery.jobUser",
    "roles/cloudtasks.enqueuer",
    "roles/cloudtasks.viewer",
    "roles/iam.serviceAccountOpenIdTokenCreator",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/run.invoker",
    "roles/secretmanager.viewer",
    "roles/storage.objectViewer",
    "roles/aiplatform.user"
  ])
  project = var.project_number
  role    = each.key
  member  = google_service_account.service_account.member
}

# ------------------------------------------------------------------------------
# ARTIFACT REGISTRY
# ------------------------------------------------------------------------------

resource "google_artifact_registry_repository" "repository" {
  project       = var.project_id
  location      = var.location
  repository_id = var.repository_id
  format        = "DOCKER"
  depends_on = [
    google_project_service.enable_apis
  ]
}

# ------------------------------------------------------------------------------
# APIS & SECRETS
# ------------------------------------------------------------------------------

resource "google_apikeys_key" "api_key" {
  name         = "shoppable-video-generative-language-api-key-prod"
  display_name = "Shoppable Video Generative Language API key"
  project      = var.project_number
  restrictions {
    api_targets {
      service = "generativelanguage.googleapis.com"
    }
  }
  depends_on = [google_project_service.enable_apis]

  lifecycle {
    ignore_changes = [project]
  }
}

resource "google_secret_manager_secret" "api_key_secret" {
  secret_id = "shoppable_video_api_key"
  replication {
    auto {}
  }
  depends_on = [
    google_project_service.enable_apis
  ]
}

resource "google_secret_manager_secret_iam_member" "member" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.api_key_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.service_account.member
}

resource "google_secret_manager_secret_version" "api_key_secret" {
  secret      = google_secret_manager_secret.api_key_secret.name
  secret_data = google_apikeys_key.api_key.key_string
}
