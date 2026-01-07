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

# terraform/modules/webapp/networking/variables.tf

# ------------------------------------------------------------------------------
# MODULE VARIABLES
# ------------------------------------------------------------------------------
# Defines the input variables required to provision networking resources.
# ------------------------------------------------------------------------------

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "region" {
  description = "The default GCP region for regional resources."
  type        = string
}

variable "app_name" {
  description = "The application name prefix used for resource naming."
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR range for the primary application subnet."
  type        = string
}

variable "labels" {
  description = "Labels to apply to networking resources."
  type        = map(string)
  default     = {}
}

variable "routing_mode" {
  description = "The network-wide routing mode to use. If set to 'GLOBAL', the network's cloud routers will see all subnets in the network, across all regions. Options: 'REGIONAL', 'GLOBAL'."
  type        = string
  default     = "GLOBAL"

  validation {
    condition     = contains(["REGIONAL", "GLOBAL"], var.routing_mode)
    error_message = "Routing mode must be either 'REGIONAL' or 'GLOBAL'."
  }
}

variable "log_config" {
  description = "Configures VPC Flow Logs for the Subnet(s). Allows tuning of sampling and metadata to control costs."
  type = object({
    enable               = bool
    aggregation_interval = optional(string, "INTERVAL_5_SEC") # Options: INTERVAL_5_SEC, INTERVAL_30_SEC, INTERVAL_1_MIN, etc.
    flow_sampling        = optional(number, 0.5)              # 0.0 to 1.0 (1.0 = 100% of traffic). 0.5 is a good balance.
    metadata             = optional(string, "INCLUDE_ALL_METADATA")
  })
  default = {
    enable               = false # Default to OFF to prevent unexpected costs.
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}
