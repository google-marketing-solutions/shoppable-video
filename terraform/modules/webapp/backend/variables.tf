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

# terraform/modules/webapp/backend/variables.tf

# ------------------------------------------------------------------------------
# MODULE VARIABLES
# ------------------------------------------------------------------------------
# Defines the inputs required to deploy the Cloud Run service.
# ------------------------------------------------------------------------------

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "project_number" {
  description = "The Google Cloud Project Number."
  type        = string
}

variable "region" {
  description = "The region where Cloud Run will be deployed."
  type        = string
}

variable "app_name" {
  description = "The application name prefix."
  type        = string
}

variable "docker_image" {
  description = "The container image URI (e.g., gcr.io/proj/img:tag)."
  type        = string
}

variable "service_account_email" {
  description = "The email of the GCP Service Account to attach to Cloud Run."
  type        = string
}

variable "secret_ids" {
  description = "Map of environment variables to secret configurations. Key is the Env_Var_name."
  type = map(object({
    secret_id = string                     # The resource ID of the secret.
    version   = optional(string, "latest") # Defaults to 'latest' if not provided.
  }))
}

variable "labels" {
  description = "Labels to apply to the Cloud Run service."
  type        = map(string)
  default     = {}
}

variable "scaling_config" {
  description = "Configures the auto-scaling behavior for Cloud Run."
  type = object({
    max_instance_count = number
    min_instance_count = number
  })
  default = {
    max_instance_count = 5
    min_instance_count = 2
  }
}

variable "lb_domain" {
  description = "The domain or IP of the Load Balancer (e.g., '34.1.2.3' or 'example.com')."
  type        = string
}

variable "frontend_url" {
  description = "The full URL of the frontend (e.g., 'https://34.1.2.3')."
  type        = string
}

variable "extra_env_vars" {
  description = "Additional environment variables to inject into the container."
  type        = map(string)
  default     = {}
}

# ------------------------------------------------------------------------------
# RUNTIME CONFIGURATION
# ------------------------------------------------------------------------------

variable "ingress_style" {
  description = "Traffic restrictions: 'INGRESS_TRAFFIC_ALL' (Public) or 'INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER' (Private)."
  type        = string
  default     = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
}

variable "resource_limits" {
  description = "Compute resources allocated to the container."
  type = object({
    cpu    = string
    memory = string
  })
  default = {
    cpu    = "2000m"  # 2 vCPU
    memory = "1024Mi" # 1 GB
  }
}

variable "container_override" {
  description = "Override Docker ENTRYPOINT (command) and CMD (args). Set to null to use Dockerfile defaults."
  type = object({
    command = optional(list(string)) # Default null.
    args    = optional(list(string)) # Default null.
  })
  default = {
    command = null
    args    = null
  }
}
