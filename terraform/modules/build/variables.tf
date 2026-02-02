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

# terraform/modules/build/variables.tf

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "location" {
  description = "The location (region) for the Artifact Registry."
  type        = string
}

variable "repository_id" {
  description = "The ID of the Artifact Registry repository."
  type        = string
}

variable "deploy_webapp" {
  description = "Whether to build the webapp backend image."
  type        = bool
  default     = true
}