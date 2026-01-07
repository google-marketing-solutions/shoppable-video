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

# terraform/modules/webapp/security/outputs.tf

# ------------------------------------------------------------------------------
# MODULE OUTPUTS
# ------------------------------------------------------------------------------
# Exposes identity and secret details for the Backend module.
# ------------------------------------------------------------------------------

output "secret_ids" {
  description = "Returns a map of secret objects compatible with the backend module."
  value = {
    for k, v in google_secret_manager_secret.app_secrets : k => {
      secret_id = v.id
      version   = "latest" # Security module creates them, so default is latest.
    }
  }
  # Ensure that the side-loaded versions exist.
  depends_on = [null_resource.secret_version_manager]
}

output "service_account_email" {
  value = var.service_account_email != null ? var.service_account_email : google_service_account.backend_sa[0].email
}
