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

# terraform/modules/webapp/variables.tf

# ------------------------------------------------------------------------------
# CORE INFRASTRUCTURE VARIABLES
# ------------------------------------------------------------------------------

variable "project_id" {
  description = "The Google Cloud Project ID where resources will be deployed."
  type        = string
}

variable "project_number" {
  description = "The Google Cloud Project Number."
  type        = string
}

variable "location" {
  description = "The default location (region) for resources (e.g., Cloud Run, Subnets, etc.)."
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "A prefix used for naming resources to ensure consistency (e.g., 'ads-platform')."
  type        = string
  default     = "shoppable-video"
}

variable "service_account_email" {
  description = "The email of the service account to be used by the backend. If not provided, one will be created."
  type        = string
  default     = null
}

# ------------------------------------------------------------------------------
# SECURITY AND SECRET VARIABLES
# ------------------------------------------------------------------------------

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

variable "pinned_secrets" {
  description = "Optional map to pin specific secret versions. Key is the Env_Var_Name (e.g. 'GOOGLE_CLIENT_ID'), Value is the version (e.g., '2')."
  type        = map(string)
  default     = {} # Empty means everything uses 'latest'.
}

variable "armor_settings" {
  description = "Configures Cloud Armor (WAF) policies. Supports granular OWASP tuning and custom logic."
  type = object({
    enable_cloud_armor = bool # Toggles the creation of the security policy entirely.

    armor_tier = optional(string, "STANDARD") # Options: 'STANDARD' (Pay-as-you-go) or 'MANAGED' (Subscription).

    # Defines which Google-managed rule sets to apply (e.g., SQLi, XSS, etc.).
    managed_rules = optional(map(object({
      enabled           = bool
      priority          = number
      action            = optional(string, "deny(403)")
      sensitivity_level = optional(number, 1) # Sensitivity: 1 (Relaxed) to 4 (Strict). Default 1 is standard balance.
      })), {
      # Default Baseline: Covers OWASP Top 10.
      "sqli-v33-stable"              = { enabled = true, priority = 1000, sensitivity_level = 1 }
      "xss-v33-stable"               = { enabled = true, priority = 1001, sensitivity_level = 1 }
      "lfi-v33-stable"               = { enabled = true, priority = 1002, sensitivity_level = 1 }
      "rce-v33-stable"               = { enabled = true, priority = 1003, sensitivity_level = 1 }
      "rfi-v33-stable"               = { enabled = true, priority = 1004, sensitivity_level = 1 }
      "methodenforcement-v33-stable" = { enabled = true, priority = 1005, sensitivity_level = 1 }
      "scannerdetection-v33-stable"  = { enabled = true, priority = 1006, sensitivity_level = 1 }
      "protocolattack-v33-stable"    = { enabled = true, priority = 1007, sensitivity_level = 1 }
      "sessionfixation-v33-stable"   = { enabled = true, priority = 1008, sensitivity_level = 1 }
      "cve-canary"                   = { enabled = true, priority = 1009, sensitivity_level = 1 }
      "json-sqli-canary"             = { enabled = true, priority = 1010, sensitivity_level = 1 }
    })

    # Allows injection of custom CEL logic (e.g., Geo-blocking, Rate Limiting, etc.).
    custom_rules = optional(list(object({
      priority    = number
      action      = string # e.g., "allow", "deny(403)", or "rate_limit".
      expression  = string # CEL: "origin.region_code == 'US'".
      description = optional(string)

      # Rate Limit Config (Required only if action == "rate_limit").
      rate_limit = optional(object({
        rate_limit_threshold = number
        interval_sec         = number
        conform_action       = string
        exceed_action        = string
      }))
    })), [])

    denylist_ips = optional(list(string), []) # A simple list of CIDR ranges to block globally at the highest priority.
  })

  default = {
    enable_cloud_armor = false
    custom_rules       = []
    denylist_ips       = []
  }
}

# ------------------------------------------------------------------------------
# DNS CONFIGURATION
# ------------------------------------------------------------------------------

variable "dns_config" {
  description = "Configures automated DNS record creation."
  type = object({
    create_record     = bool                  # If true, attempts to create a Google Cloud DNS record.
    create_zone       = optional(bool, false) # Create the zone itself.
    managed_zone_name = optional(string)      # Name of the existing zone (required if create_record is true).
    zone_dns_name     = optional(string)      # Root domain (e.g. "example.com."). Required if creating zone.
    record_name       = optional(string)      # The FQDN to create (required if create_record is true).
    project_id        = optional(string)      # Optional: GCP Project ID where the zone lives. If null, uses the current GCP Project.
  })
  default = {
    create_record     = false
    create_zone       = false
    managed_zone_name = null
    zone_dns_name     = null
    record_name       = null
    project_id        = null
  }
}

# ------------------------------------------------------------------------------
# LOAD BALANCER VARIABLES
# ------------------------------------------------------------------------------

variable "lb_config" {
  description = "Configures the Global Load Balancer, CDN, and SSL settings."
  type = object({
    enable_cdn        = bool                           # Toggles Cloud CDN for the frontend bucket.
    domain_name       = optional(string)               # If dns_config.create_record is false, this value is used. If this is also null, falls back to 'nip.io'.
    ssl_policy        = optional(string, "COMPATIBLE") # Options: 'COMPATIBLE' (Broader support) or 'MODERN' (Stricter security).
    use_managed_certs = bool                           # If true, Google provisions the cert. If false, user provides the cert.
    custom_cert_names = optional(list(string), [])     # List of self-managed SSL Certificate resource names to use if use_managed_certs is false. Example: ["my-uploaded-cert-v1", "my-backup-cert"]
  })
  default = {
    enable_cdn        = true
    domain_name       = null # Defaults to null to allow fallback to 'nip.io'.
    use_managed_certs = true
    ssl_policy        = "COMPATIBLE"
    custom_cert_names = []
  }

  # ----------------------------------------------------------------------------
  # VALIDATION LOGIC
  # ----------------------------------------------------------------------------
  # Ensures that if Google-managed Certificates are disabled, the user must provide
  # at least one custom certificate name. Otherwise, the LB would have no SSL.
  # ----------------------------------------------------------------------------
  validation {
    condition     = var.lb_config.use_managed_certs == true || length(var.lb_config.custom_cert_names) > 0
    error_message = "Configuration Error: If 'use_managed_certs' is set to false, at least one certificate name in 'custom_cert_names' must be provided."
  }
}

# ------------------------------------------------------------------------------
# NETWORK CONFIGURATION
# ------------------------------------------------------------------------------

variable "networking_config" {
  description = "Configuration for VPC and Subnets."
  type = object({
    subnet_cidr  = string # e.g., "10.0.0.0/24".
    routing_mode = optional(string, "GLOBAL")
    log_config = optional(object({
      enable               = bool
      aggregation_interval = optional(string)
      flow_sampling        = optional(number)
      metadata             = optional(string)
      }), {
      enable = false
    })
  })
  default = {
    subnet_cidr  = "10.0.0.0/24"
    routing_mode = "GLOBAL"
    log_config   = { enable = false }
  }
}

# ------------------------------------------------------------------------------
# LABELS AND TAGGING
# ------------------------------------------------------------------------------

variable "labels" {
  description = "A map of labels to apply to contained resources. Keys and values must be lowercase, and may only contain letters, numbers, hyphens, and underscores."
  type        = map(string)
  default = {
    app = "shoppable-video-webapp"
  }
}

# ------------------------------------------------------------------------------
# CI/CD AND IMAGE CONFIGURATION
# ------------------------------------------------------------------------------

variable "backend_image" {
  description = "The Docker image URI for the backend service (provided by the build module)."
  type        = string
}

variable "bigquery_dataset_id" {
  description = "The BigQuery Dataset ID to be used by the webapp."
  type        = string
}

variable "video_analysis_table_id" {
  description = "The BigQuery table ID that contains video analyses"
  type        = string
}

variable "matched_products_table_id" {
  description = "The BigQuery table ID that contains matched products"
  type        = string
}



# ------------------------------------------------------------------------------
# BACKEND CONFIGURATION
# ------------------------------------------------------------------------------

variable "backend_config" {
  description = "Configuration for the Backend Cloud Run service."
  type = object({
    scaling = optional(object({
      max_instance_count = number
      min_instance_count = number
      }), {
      max_instance_count = 5
      min_instance_count = 2
    })

    # Default to PRIVATE (LB Only). Override to "INGRESS_TRAFFIC_ALL" in tfvars for testing.
    ingress_style = optional(string, "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER")

    resources = optional(object({
      cpu    = string
      memory = string
      }), {
      cpu    = "4000m"  # Default to 4 vCPU.
      memory = "2048Mi" # Default to 2 GiB.
    })

    # Default to null so Dockerfile CMD is used by default.
    container_override = optional(object({
      command = optional(list(string))
      args    = optional(list(string))
      }), {
      command = null
      args    = null
    })
  })

  default = {
    scaling = {
      max_instance_count = 5
      min_instance_count = 2
    }
    ingress_style = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
    resources = {
      cpu    = "4000m"
      memory = "2048Mi"
    }
    container_override = {
      command = null
      args    = null
    }
  }
}
