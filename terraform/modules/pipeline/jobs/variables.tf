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

# modules/jobs/variables.tf

variable "job_name" {
  description = "The name of the Cloud Run job."
  type        = string
}

variable "location" {
  description = "The location of the Cloud Run job."
  type        = string
}

variable "service_account_email" {
  description = "The email of the service account to use for the job."
  type        = string
}

variable "image" {
  description = "The container image to use for the job."
  type        = string
}

variable "args" {
  description = "The arguments to pass to the container."
  type        = list(string)
  default     = []
}

variable "project_id" {
  description = "The ID of the project."
  type        = string
}

variable "environment_variables" {
  description = "The environment variables to pass to the container."
  type        = map(string)
  default     = {}
}

variable "timeout" {
  description = "The timeout for the Cloud Run job in seconds."
  type        = string
  default     = "600s"
}

variable "retries" {
  description = "The number of retries for the Cloud Run job."
  type        = number
  default     = 0
}
