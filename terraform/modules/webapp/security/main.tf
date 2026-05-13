# Copyright 2026 Google LLC
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

# terraform/modules/webapp/security/main.tf

# ------------------------------------------------------------------------------
# SECRET CONTAINERS (Terraform State Aware)
# ------------------------------------------------------------------------------
# Terraform manages the existence of the secret, labels, and replication.
# ------------------------------------------------------------------------------

resource "google_service_account" "backend_sa" {
  count        = var.service_account_email == null ? 1 : 0
  account_id   = "${var.app_name}-backend-sa"
  display_name = "Cloud Run Backend Identity"
  project      = var.project_id
}

locals {
  service_account_email = var.service_account_email != null ? var.service_account_email : google_service_account.backend_sa[0].email
}

resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each  = var.secret_ids
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.service_account_email}"
}
