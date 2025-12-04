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

variable "project_id" {
  type        = string
  description = "The project ID to deploy to."
}

variable "location" {
  type        = string
  description = "The location to deploy to."
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
  default     = null
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

variable "gcs_embeddings_bucket_name" {
  type        = string
  description = "The name of the GCS bucket for embeddings."
}

variable "gcs_bucket_ttl_days" {
  type        = number
  description = "The TTL for the GCS bucket."
}

variable "random_id_prefix" {
  type        = string
  description = "The random ID prefix to use."
}

variable "embedding_model_name" {
  type        = string
  description = "The name of the embedding model to use."
}

variable "product_limit" {
  type        = number
  description = "The maximum number of products to queue."
}

variable "generative_model_name" {
  type        = string
  description = "The name of the generative model to use."
}

variable "repository_id" {
  type        = string
  description = "The Artifact Registry repository ID."
}

variable "video_limit" {
  type        = number
  description = "The maximum number of videos to queue."
}

variable "spreadsheet_id" {
  type        = string
  description = "The ID of the Google Sheet for manual video entry."
  default     = null
}

variable "secret_id" {
  type        = string
  description = "The ID of the secret containing the Gemini API key."
}
