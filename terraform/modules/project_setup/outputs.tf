# Copyright 2026 Google LLC
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

# terraform/modules/project_setup/outputs.tf

output "service_account_email" {
  description = "The email address of the created service account."
  value       = google_service_account.service_account.email
}

output "api_key_secret_id" {
  description = "The Secret Manager ID storing the Gemini API key."
  value       = google_secret_manager_secret.api_key_secret.secret_id
}

output "repository_id" {
  description = "The ID of the Artifact Registry repository."
  value       = google_artifact_registry_repository.repository.repository_id
}

output "secret_ids" {
  description = "Returns a map of secret objects compatible with backend modules."
  value = {
    for k, v in google_secret_manager_secret.app_secrets : k => {
      secret_id = v.id
      version   = "latest"
    }
  }
  depends_on = [null_resource.secret_version_manager]
}
