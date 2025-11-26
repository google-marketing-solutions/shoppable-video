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
  type = string
}

variable "service_account_email" {
  type = string
}

variable "bigquery_dataset_id" {
  type = string
}

variable "merchant_id" {
  type = string
}

variable "ads_customer_id" {
  type = string
}

variable "refresh_window_days" {
  type = string
}

variable "vector_search_embedding_dimensions" {
  type = string
}

variable "number_of_matched_products" {
  type = number
}
