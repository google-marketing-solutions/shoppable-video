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

# terraform/outputs.tf

# ------------------------------------------------------------------------------
# GLOBAL OUTPUTS
# ------------------------------------------------------------------------------

output "load_balancer_ip" {
  description = "The global static IP address reserved for the Load Balancer."
  value       = var.deploy_webapp ? module.webapp[0].load_balancer_ip : null
}

output "frontend_bucket_url" {
  description = "The gsutil URI for the frontend bucket. Use this to upload assets."
  value       = var.deploy_webapp ? module.webapp[0].frontend_bucket_url : null
}

output "backend_service_url" {
  description = "The direct URL of the Cloud Run backend service. (Note: Direct access is restricted by IAM)."
  value       = var.deploy_webapp ? module.webapp[0].backend_service_url : null
}
