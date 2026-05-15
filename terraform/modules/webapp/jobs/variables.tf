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

# terraform/modules/webapp/jobs/variables.tf

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "location" {
  description = "The Google Cloud region/location."
  type        = string
}

variable "app_name" {
  description = "The application name prefix."
  type        = string
}

variable "service_account_email" {
  description = "The service account email to execute the jobs."
  type        = string
}

variable "cloud_run_job_image" {
  description = "The Docker image URI for the Ads Insertion job."
  type        = string
}

variable "data_sync_image" {
  description = "The Docker image URI for the Data Sync job."
  type        = string
}

variable "merchant_id" {
  description = "The Merchant Center ID."
  type        = string
}

variable "bigquery_dataset_id" {
  description = "The BigQuery Dataset ID."
  type        = string
}

variable "google_ads_customer_id" {
  description = "The Google Ads Customer ID."
  type        = string
  default     = null
}

variable "firestore_database_id" {
  description = "The Firestore Database ID."
  type        = string
  default     = "(default)"
}

variable "secret_ids" {
  description = "Map of secret IDs and versions."
  type = map(object({
    secret_id = string
    version   = string
  }))
}

variable "pinned_secrets" {
  description = "Optional map of pinned secret versions."
  type        = map(string)
  default     = {}
}

variable "enable_scheduling" {
  description = "Enable automated scheduling."
  type        = bool
}
