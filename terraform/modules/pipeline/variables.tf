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

# terraform/modules/pipeline/variables.tf

# ------------------------------------------------------------------------------
# CORE PROJECT & ENVIRONMENT CONFIGURATION
# ------------------------------------------------------------------------------

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

variable "random_id_prefix" {
  type        = string
  description = "The random ID prefix to use."
}

# ------------------------------------------------------------------------------
# EXTERNAL INTEGRATIONS, SECRETS & CREDENTIALS
# ------------------------------------------------------------------------------

variable "merchant_id" {
  type        = string
  description = "The Merchant Center ID."
}

variable "google_ads_customer_id" {
  type        = string
  description = "The Google Ads customer ID."
  default     = null
}

variable "spreadsheet_id" {
  type        = string
  description = "The ID of the Google Sheet for manual video entry."
  default     = null
}

variable "api_key_secret_id" {
  type        = string
  description = "The ID of the secret containing the Gemini API key."
}

variable "developer_token_secret_id" {
  type        = string
  description = "The ID of the secret containing the Google Ads developer token."
  default     = null
}

# ------------------------------------------------------------------------------
# AI & MACHINE LEARNING (GEMINI MODELS & VECTOR SEARCH)
# ------------------------------------------------------------------------------

variable "generative_model_name" {
  type        = string
  description = "The name of the generative model to use."
}

variable "embedding_model_name" {
  type        = string
  description = "The name of the embedding model to use."
}

variable "vector_search_embedding_dimensions" {
  type        = number
  description = "The number of dimensions for the vector search embedding."
}

variable "embed_images" {
  type        = bool
  description = "Whether to embed images."
}

variable "num_images_to_embed" {
  type        = number
  description = "The number of images to embed."
}

# ------------------------------------------------------------------------------
# PIPELINE LIMITS & EXECUTION CONFIGURATION
# ------------------------------------------------------------------------------

variable "enable_scheduling" {
  type        = bool
  description = "Enable automated scheduling."
}

variable "product_limit" {
  type        = number
  description = "The maximum number of products to queue."
}

variable "video_limit" {
  type        = number
  description = "The maximum number of videos to queue."
}

variable "number_of_matched_products" {
  type        = number
  description = "The number of matched products to return."
}

# ------------------------------------------------------------------------------
# STORAGE, DATABASE & CONTAINER INFRASTRUCTURE
# ------------------------------------------------------------------------------

variable "bigquery_dataset_id" {
  type        = string
  description = "The BigQuery dataset ID."
}

variable "gcs_embeddings_bucket_name" {
  type        = string
  description = "The name of the GCS bucket for embeddings."
}

variable "gcs_bucket_ttl_days" {
  type        = number
  description = "The TTL for the GCS bucket."
}

variable "repository_id" {
  type        = string
  description = "The Artifact Registry repository ID."
}

variable "queue_products_image" {
  type        = string
  description = "The Docker image for queue-products job."
  default     = null
}

variable "queue_videos_image" {
  type        = string
  description = "The Docker image for queue-videos job."
  default     = null
}
