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

# terraform/modules/pipeline/scheduler/variables.tf

variable "name" {
  type        = string
  description = "The name of the scheduler job."
}

variable "project_id" {
  type        = string
  description = "The project ID to deploy to."
}

variable "location" {
  type        = string
  description = "The location to deploy to."
}

variable "function_url" {
  description = "The URL of the function to invoke."
  type        = string
  default     = null
}

variable "job_name" {
  description = "The name of the job to invoke."
  type        = string
  default     = null
}

variable "body" {
  type        = string
  description = "The body of the request to send to the target."
  default     = null
}

variable "service_account_email" {
  type        = string
  description = "The service account email to use."
}

variable "schedule" {
  type        = string
  description = "The schedule for the job."
  default     = "0 * * * *"
}
