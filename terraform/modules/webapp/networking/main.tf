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

# terraform/modules/webapp/networking/main.tf

# ------------------------------------------------------------------------------
# VPC NETWORK
# ------------------------------------------------------------------------------
# Creates a custom VPC Network.
# 'auto_create_subnetworks' is set to false to allow explicit control over IP ranges.
# ------------------------------------------------------------------------------

resource "google_compute_network" "vpc" {
  name                    = "${var.app_name}-vpc"
  project                 = var.project_id
  auto_create_subnetworks = false
  routing_mode            = var.routing_mode
}

# ------------------------------------------------------------------------------
# SUBNETWORK
# ------------------------------------------------------------------------------
# Creates a subnet for the application in the specified region.
# The CIDR range is passed via variables to support external IP planning.
# ------------------------------------------------------------------------------

resource "google_compute_subnetwork" "app_subnet" {
  name                     = "${var.app_name}-subnet"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true

  # ----------------------------------------------------------------------------
  # VPC FLOW LOGS
  # ----------------------------------------------------------------------------
  # Dynamically enables flow logs based on the variable configuration.
  # ----------------------------------------------------------------------------
  dynamic "log_config" {
    for_each = var.log_config.enable ? [1] : []
    content {
      aggregation_interval = var.log_config.aggregation_interval
      flow_sampling        = var.log_config.flow_sampling
      metadata             = var.log_config.metadata
    }
  }
}

# ------------------------------------------------------------------------------
# GLOBAL IP RESERVATION
# ------------------------------------------------------------------------------
# Reserves a global static IP address for the Load Balancer.
# ------------------------------------------------------------------------------

resource "google_compute_global_address" "lb_ip" {
  name        = "${var.app_name}-global-ip"
  project     = var.project_id
  description = "Static IP reserved for the Global HTTPS Load Balancer."
  labels      = var.labels
}
