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

# terraform/modules/webapp/outputs.tf

# ------------------------------------------------------------------------------
# GLOBAL OUTPUTS
# ------------------------------------------------------------------------------

output "load_balancer_ip" {
  description = "The global static IP address reserved for the Load Balancer."
  value       = module.networking.global_ip
}

output "frontend_bucket_url" {
  description = "The gsutil URI for the frontend bucket. Use this to upload assets."
  value       = "gs://${module.frontend.bucket_name}"
}

output "backend_service_url" {
  description = "The direct URL of the Cloud Run backend service. (Note: Direct access is restricted by IAM)."
  value       = module.backend.service_url
}
