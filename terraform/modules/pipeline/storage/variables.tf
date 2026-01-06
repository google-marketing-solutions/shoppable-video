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

# terraform/modules/pipeline/storage/variables.tf

variable "project_id" {
  description = "The ID of the project in which to provision resources."
  type        = string
}

variable "bucket_location" {
  description = "The location of the GCS bucket."
  type        = string
}

variable "bucket_name" {
  description = "The name of the GCS bucket to create."
  type        = string
}

variable "service_account_email" {
  description = "The email of the service account to grant access to the bucket."
  type        = string
}

variable "bucket_ttl_days" {
  description = "The number of days after which to delete objects in the bucket."
  type        = number
}
