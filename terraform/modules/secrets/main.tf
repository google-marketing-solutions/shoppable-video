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

# modules/secrets/main.tf

resource "google_project_service" "enable_apis" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
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
  member    = var.service_account_member
}

resource "google_secret_manager_secret_version" "api_key_secret" {
  secret                 = google_secret_manager_secret.api_key_secret.name
  secret_data_wo         = var.api_key
  secret_data_wo_version = 1
  enabled                = true
}
