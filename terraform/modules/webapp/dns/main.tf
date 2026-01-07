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

# terraform/modules/webapp/dns/main.tf

# ------------------------------------------------------------------------------
# MANAGED ZONE CREATION
# ------------------------------------------------------------------------------
# If the user requests a new zone, this resource creates it.
# ------------------------------------------------------------------------------
resource "google_dns_managed_zone" "main" {
  count       = var.create_zone ? 1 : 0
  name        = var.managed_zone_name
  dns_name    = var.zone_dns_name # e.g., "example.com." (Must end with a dot)
  description = "Provisioned by Terraform for ${var.domain_name}"
  project     = var.dns_project_id
}

# ------------------------------------------------------------------------------
# A-RECORD CREATION
# ------------------------------------------------------------------------------
resource "google_dns_record_set" "a_record" {
  name    = "${var.domain_name}."
  type    = "A"
  ttl     = 300
  project = var.dns_project_id

  # If the zone was created, reference the resource name (implicit dependency).
  # If no zone was created, use the string variable directly.
  managed_zone = var.create_zone ? google_dns_managed_zone.main[0].name : var.managed_zone_name

  rrdatas = [var.lb_ip_address]
}
