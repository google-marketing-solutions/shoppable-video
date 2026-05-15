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

# terraform/modules/pipeline/pubsub/variables.tf

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "location" {
  description = "The Google Cloud region/location."
  type        = string
}

variable "service_account_email" {
  description = "The service account email for OIDC authentication."
  type        = string
}

variable "latest_products_topic_id" {
  description = "The Pub/Sub topic ID for latest products completion."
  type        = string
}

variable "queue_products_job_name" {
  description = "The name of the Cloud Run job to trigger."
  type        = string
}
