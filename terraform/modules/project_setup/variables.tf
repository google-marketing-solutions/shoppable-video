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

# terraform/modules/project_setup/variables.tf

variable "project_id" {
  type        = string
  description = "The project ID to deploy to."
}

variable "project_number" {
  type        = string
  description = "The number of the project to deploy to."
}

variable "location" {
  type        = string
  description = "The location to deploy to."
}

variable "service_account_id" {
  type        = string
  description = "The service account to use."
}

variable "repository_id" {
  type        = string
  description = "The Artifact Registry repository ID."
}

variable "secrets_config" {
  description = "Configuration for local secret injection."
  type = object({
    directory = string
    file_map  = map(string)
  })
  default = {
    directory = "./config/secrets"
    file_map = {
      "GOOGLE_CLIENT_ID"           = "google_client_id.txt"
      "GOOGLE_CLIENT_SECRET"       = "google_client_secret.txt"
      "GOOGLE_ADS_DEVELOPER_TOKEN" = "developer_token.txt"
      "SESSION_SECRET_KEYS"        = "session_keys.txt"
    }
  }
}

variable "deploy_webapp" {
  description = "Whether the webapp is being deployed."
  type        = bool
  default     = false
}

variable "google_ads_customer_id" {
  description = "The Google Ads customer ID."
  type        = string
  default     = null
}

variable "app_name" {
  description = "The application name prefix used for resource naming."
  type        = string
  default     = "shoppable-video"
}

variable "labels" {
  description = "Labels to apply to the resources."
  type        = map(string)
  default = {
    app = "shoppable-video"
  }
}
