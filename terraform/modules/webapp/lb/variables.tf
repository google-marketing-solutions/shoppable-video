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

# terraform/modules/webapp/lb/variables.tf

# ------------------------------------------------------------------------------
# MODULE VARIABLES
# ------------------------------------------------------------------------------
# Defines configuration for Traffic, Security, and SSL termination.
# ------------------------------------------------------------------------------

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "app_name" {
  description = "The application name prefix."
  type        = string
}

variable "region" {
  description = "The GCP region to be used for deploying load balancing resources."
  type        = string
}

# --- DEPENDENCY INJECTION ---

variable "cloud_run_service_name" {
  description = "The name of the Cloud Run service (from backend module)."
  type        = string
}

variable "frontend_bucket_name" {
  description = "The name of the GCS bucket for static content routing."
  type        = string
}

variable "global_ip" {
  description = "The static global IP address reserved for this Load Balancer."
  type        = string
}

# --- CONFIGURATION OBJECTS ---

variable "lb_settings" {
  description = "Configures Load Balancer features including CDN, Domain, and SSL Policy."
  type = object({
    enable_cdn        = bool
    domain_name       = optional(string)
    ssl_policy        = optional(string)
    use_managed_certs = bool
    custom_cert_names = optional(list(string), [])
  })
}

variable "armor_settings" {
  description = "Configures Cloud Armor Security Policy rules, including managed OWASP rules and custom logic."
  type = object({
    enable_cloud_armor = bool
    armor_tier         = optional(string)

    # Map of managed rule sets (e.g., SQLi, XSS) with enable flags and sensitivity levels.
    managed_rules = map(object({
      enabled           = bool
      priority          = number
      action            = optional(string)
      sensitivity_level = optional(number)
    }))

    # List of custom user rules for business logic (e.g., Geo-blocking).
    custom_rules = list(object({
      priority    = number
      action      = string
      expression  = string
      description = optional(string)
      rate_limit = optional(object({
        rate_limit_threshold = number
        interval_sec         = number
        conform_action       = string
        exceed_action        = string
      }))
    }))

    # List of IPs to block globally.
    denylist_ips = list(string)
  })
}

variable "iap_config" {
  description = "Configures IAP for the API backend."
  type = object({
    enable_iap     = bool
    access_members = list(string)
  })
  default = {
    enable_iap     = true
    access_members = ["domain:google.com"]
  }
}

variable "labels" {
  description = "Labels to apply to load balancer resources."
  type        = map(string)
  default     = {}
}
