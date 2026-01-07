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

# terraform/modules/webapp/dns/variables.tf

# ------------------------------------------------------------------------------
# MODULE VARIABLES
# ------------------------------------------------------------------------------

variable "dns_project_id" {
  description = "The GCP Project ID where the Cloud DNS Managed Zone is located."
  type        = string
}

variable "managed_zone_name" {
  description = "The name of the Cloud DNS Managed Zone (e.g., 'example-zone')."
  type        = string
}

variable "domain_name" {
  description = "The fully qualified domain name (FQDN) to register (e.g., 'app.example.com')."
  type        = string
}

variable "lb_ip_address" {
  description = "The global IP address of the Load Balancer to point the A-record to."
  type        = string
}

variable "create_zone" {
  description = "If true, Terraform will create a new Cloud DNS Managed Zone. If false, it assumes the zone exists."
  type        = bool
  default     = false
}

variable "zone_dns_name" {
  description = "The DNS suffix for the zone (e.g., 'example.com.'). Required only if 'create_zone' is true."
  type        = string
  default     = ""
}
