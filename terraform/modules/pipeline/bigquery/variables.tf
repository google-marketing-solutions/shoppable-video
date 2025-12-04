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

# modules/bigquery/variables.tf

variable "project_id" {
  type        = string
  description = "The project ID to deploy to."
}

variable "service_account_email" {
  type        = string
  description = "The service account email to use."
}

variable "bigquery_dataset_id" {
  type        = string
  description = "The BigQuery dataset ID."
}

variable "merchant_id" {
  type        = string
  description = "The Merchant Center ID."
}

variable "ads_customer_id" {
  type        = string
  description = "The Google Ads customer ID."
}

variable "refresh_window_days" {
  type        = number
  description = "The number of days to look back for new products."
}

variable "vector_search_embedding_dimensions" {
  type        = number
  description = "The number of dimensions for the vector search embedding."
}

variable "number_of_matched_products" {
  type        = number
  description = "The number of matched products to return."
}