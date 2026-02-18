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

# terraform/modules/webapp/security/main.tf

# ------------------------------------------------------------------------------
# SECRET CONTAINERS (Terraform State Aware)
# ------------------------------------------------------------------------------
# Terraform manages the existence of the secret, labels, and replication.
# ------------------------------------------------------------------------------

resource "google_secret_manager_secret" "app_secrets" {
  for_each  = var.secret_map
  secret_id = "${var.app_name}-${each.key}"
  project   = var.project_id

  replication {
    auto {}
  }
  labels = var.labels
}

# ------------------------------------------------------------------------------
# SECRET INJECTION (Terraform State Persistance for Sensitive Values Bypassed)
# ------------------------------------------------------------------------------
# Uses local-exec to push the secret value(s) directly to GCP.
# The value NEVER enters the Terraform state file.
# ------------------------------------------------------------------------------

resource "null_resource" "secret_version_manager" {
  for_each = var.secret_map

  # Re-run this script only if the secret container ID changes.
  triggers = {
    secret_id = google_secret_manager_secret.app_secrets[each.key].id

    # Trigger on file content, not just secret ID.
    # If the text file containing the secret changes, the file checksum hash changes -> Terraform re-runs the script.
    payload_hash = filesha256("${var.secrets_dir}/${each.value}")
    force_run   = "1"  # Increment this number to force a run
  }

  provisioner "local-exec" {
    command = <<EOT
      # 1. Check if local file exists.
      if [ ! -f "${var.secrets_dir}/${each.value}" ]; then
        echo "ERROR: Secret file ${var.secrets_dir}/${each.value} not found!"
        exit 1
      fi

      # 2. Push version to Google Secret Manager (stripping newlines).
      tr -d '\n' < "${var.secrets_dir}/${each.value}" | gcloud secrets versions add ${self.triggers.secret_id} \
        --data-file=- \
        --project="${var.project_id}"
    EOT

    # Use the machine's local shell (Bash/Zsh).
    interpreter = ["/bin/bash", "-c"]
  }

  depends_on = [google_secret_manager_secret.app_secrets]
}

# ------------------------------------------------------------------------------
# SERVICE ACCOUNT IDENTITY
# ------------------------------------------------------------------------------
# Creates a dedicated GCP Service Account for the Cloud Run backend service.
# This identity allows for granular permission control (Principle of Least Privilege).
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

# ------------------------------------------------------------------------------
# SECRET ACCESS IAM BINDING
# ------------------------------------------------------------------------------
# Grants the backend GCP Service Account permission to access the secret payloads.
# ------------------------------------------------------------------------------

resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each  = google_secret_manager_secret.app_secrets
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.service_account_email}"
}
