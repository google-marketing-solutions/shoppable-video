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

# terraform/modules/webapp/backend/outputs.tf

# ------------------------------------------------------------------------------
# MODULE OUTPUTS
# ------------------------------------------------------------------------------
# Exposes service details for the Load Balancer module.
# ------------------------------------------------------------------------------

output "service_name" {
  description = "The name of the created Cloud Run service."
  value       = google_cloud_run_v2_service.default.name
}

output "service_url" {
  description = "The direct URL of the Cloud Run service."
  value       = google_cloud_run_v2_service.default.uri
}
