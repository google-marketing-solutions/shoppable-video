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

# variables.tf

variable "project_id" {
  type = string
}

variable "service_account" {
  type = string
}

variable "merchant_id" {
  type = string
}

variable "ads_customer_id" {
  type     = string
  default  = null
  nullable = true
}

variable "spreadsheet_id" {
  type     = string
  default  = null
  nullable = true
}

variable "bigquery_dataset_id" {
  type    = string
  default = "shoppable_video"
}

variable "location" {
  type    = string
  default = "us-central1"
}

variable "product_limit" {
  type    = number
  default = 1000
}

variable "video_limit" {
  type    = number
  default = 10
}

variable "gcs_embeddings_bucket_name" {
  type        = string
  description = "The name of the GCS bucket to store embeddings."
  default     = "shoppable-video-embeddings"
}

variable "gcs_bucket_ttl_days" {
  description = "The number of days after which to delete objects in the bucket."
  type        = number
  default     = 90
}

variable "vector_search_embedding_dimensions" {
  type    = number
  default = 1536
}

variable "repository_id" {
  type    = string
  default = "shoppable-video"
}

variable "generative_model_name" {
  type    = string
  default = "gemini-2.5-flash"
}

variable "embedding_model_name" {
  type    = string
  default = "gemini-embedding-001"
}

variable "refresh_window_days" {
  type    = string
  default = "7"
}

variable "number_of_matched_products" {
  type    = number
  default = 10
}
