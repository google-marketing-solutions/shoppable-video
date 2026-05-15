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

# terraform/modules/pipeline/functions/variables.tf

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "service_account_email" {
  description = "The service account email to run the Cloud Function."
  type        = string
}

variable "location" {
  description = "The Google Cloud region/location for deploying the Cloud Function."
  type        = string
}

variable "function_name" {
  description = "The name of the Cloud Function."
  type        = string
}

variable "function_description" {
  description = "The description of the Cloud Function."
  type        = string
}

variable "source_dir" {
  description = "The local directory containing the Cloud Function source code."
  type        = string
}

variable "entry_point" {
  description = "The entry point function name in the source code."
  type        = string
}

variable "runtime" {
  description = "The runtime environment for the Cloud Function (e.g., python311)."
  type        = string
}

variable "max_instance_count" {
  description = "The maximum number of instances for the Cloud Function."
  type        = number
  default     = 100
}

variable "max_instance_request_concurrency" {
  description = "The maximum request concurrency per instance."
  type        = number
  default     = 20
}

variable "available_memory" {
  description = "The amount of memory available to the Cloud Function."
  type        = string
  default     = "1G"
}

variable "available_cpu" {
  description = "The amount of CPU available to the Cloud Function."
  type        = string
  default     = "1"
}

variable "timeout_seconds" {
  description = "The execution timeout in seconds for the Cloud Function."
  type        = number
  default     = 180
}

variable "secret_environment_variables" {
  description = "A map of secret environment variables to inject from Secret Manager."
  type = map(object({
    key     = string
    secret  = string
    version = string
  }))
  default = {}
}

variable "environment_variables" {
  description = "A map of environment variables to inject into the Cloud Function."
  type        = map(string)
  default     = {}
}

variable "random_id_prefix" {
  description = "A prefix for the random ID generated for the storage bucket object."
  type        = string
}
