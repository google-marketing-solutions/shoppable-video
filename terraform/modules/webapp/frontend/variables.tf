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

# terraform/modules/webapp/frontend/variables.tf

# ------------------------------------------------------------------------------
# MODULE VARIABLES
# ------------------------------------------------------------------------------
# Defines the inputs required to provision the static asset storage.
# ------------------------------------------------------------------------------

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "region" {
  description = "The region where the storage bucket will be created."
  type        = string
}

variable "app_name" {
  description = "The application name prefix used for resource naming."
  type        = string
}

variable "labels" {
  description = "Labels to apply to the storage bucket."
  type        = map(string)
  default     = {}
}

variable "cors_config" {
  description = "CORS configuration for the bucket. Set origins to specific domains for production security."
  type = object({
    enable  = bool
    origins = list(string)
  })
  default = {
    enable  = false # Default to OFF (Secure/Same-Origin).
    origins = ["*"]
  }
}

variable "frontend_source_dir" {
  description = "The relative path to the Angular frontend source code (e.g., '../frontend')."
  type        = string
}

variable "frontend_project_name" {
  description = "The name of the Angular project (used to find the 'dist/' folder)."
  type        = string
}
