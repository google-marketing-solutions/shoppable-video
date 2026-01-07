# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# you may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# terraform/modules/webapp/security/variables.tf

# ------------------------------------------------------------------------------
# MODULE VARIABLES
# ------------------------------------------------------------------------------
# Defines the inputs required for Identity and Secret Management.
# ------------------------------------------------------------------------------

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "app_name" {
  description = "The application name prefix used for resource naming."
  type        = string
}

variable "secrets_dir" {
  description = "Path to the local directory containing secret files. Must not be committed to Git."
  type        = string
  default     = "./config/secrets"
}

# Key = Env_Var_Name, Value = Filename_In_secrets_dir
variable "secret_map" {
  type = map(string)
  default = {
    "GOOGLE_CLIENT_ID"           = "google_client_id.txt"
    "GOOGLE_CLIENT_SECRET"       = "google_client_secret.txt"
    "GOOGLE_ADS_DEVELOPER_TOKEN" = "developer_token.txt"
    "SESSION_SECRET_KEYS"        = "session_keys.txt"
  }
}

variable "labels" {
  description = "Labels to apply to the security resources."
  type        = map(string)
  default     = {}
}

variable "service_account_email" {
  description = "Optional: Use an existing Service Account email. If null, one will be created."
  type        = string
  default     = null
}
