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

# terraform/modules/pipeline/tasks/variables.tf

variable "name" {
  type        = string
  description = "The name of the Cloud Task queue."
}

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

variable "function_url" {
  type        = string
  description = "The URL of the function to invoke."
}
