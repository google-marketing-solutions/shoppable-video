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

# terraform/modules/webapp/main.tf

# ------------------------------------------------------------------------------
# ROOT MODULE ORCHESTRATION
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# DYNAMIC DOMAIN LOGIC
# ------------------------------------------------------------------------------
# Implements the 3-tier precedence logic for determining the application domain.
# 1. Managed DNS (Highest Priority): If 'dns_config.create_record' is 'true'.
# 2. Custom Domain (Medium Priority): If 'lb_config.domain_name' is provided.
# 3. Fallback (Lowest Priority): Uses the IP-based 'nip.io' domain.
# ------------------------------------------------------------------------------

locals {
  use_managed_dns   = var.dns_config.create_record
  use_custom_domain = var.lb_config.domain_name != null && var.lb_config.domain_name != ""

  final_domain_name = (
    local.use_managed_dns ? var.dns_config.record_name :
    local.use_custom_domain ? var.lb_config.domain_name :
    "${module.networking.global_ip}.nip.io"
  )

  # Determine which GCP Project ID to use for DNS (user provided override OR current GCP Project).
  dns_target_project = var.dns_config.project_id != null ? var.dns_config.project_id : var.project_id
}

# NETWORKING MODULE.
# Provisions VPC and Subnets using the externalized CIDR.
module "networking" {
  source       = "./networking"
  project_id   = var.project_id
  region       = var.location
  app_name     = var.app_name
  subnet_cidr  = var.networking_config.subnet_cidr
  routing_mode = var.networking_config.routing_mode
  log_config   = var.networking_config.log_config
  labels       = var.labels
}

# BIGQUERY MODULE.
module "bigquery" {
  source     = "./bigquery"
  project_id = var.project_id
  dataset_id = var.bigquery_dataset_id
}


# SECURITY MODULE.
module "security" {
  source                = "./security"
  project_id            = var.project_id
  app_name              = var.app_name
  secrets_dir           = var.secrets_config.directory == "./config/secrets" ? "${path.module}/config/secrets" : var.secrets_config.directory
  secret_map            = var.secrets_config.file_map
  labels                = var.labels
  service_account_email = var.service_account_email
}

# BACKEND MODULE
module "backend" {
  source         = "./backend"
  project_id     = var.project_id
  project_number = var.project_number
  region         = var.location
  app_name       = var.app_name

  # ------------------------------------------------------------
  # IMAGE SELECTION LOGIC
  # ------------------------------------------------------------
  # Image is provided by the build module.
  # ------------------------------------------------------------
  docker_image = var.backend_image

  service_account_email = module.security.service_account_email

  # ----------------------------------------------------------------------------
  # SECRET VERSION PINNING LOGIC
  # ----------------------------------------------------------------------------
  # Merges the dynamic secrets from the security module with any manual overrides.
  # ----------------------------------------------------------------------------

  secret_ids = {
    for k, v in module.security.secret_ids : k => {
      secret_id = v.secret_id
      # Look up if a pinned version exists in var.pinned_secrets, else use default 'latest'.
      version = lookup(var.pinned_secrets, k, v.version)
    }
  }

  scaling_config     = var.backend_config.scaling
  resource_limits    = var.backend_config.resources
  ingress_style      = var.backend_config.ingress_style
  container_override = var.backend_config.container_override

  extra_env_vars = {
    PROJECT_ID        = var.project_id
    DATASET_ID        = var.bigquery_dataset_id
    VIDEO_ANALYSIS_TABLE_ID = var.video_analysis_table_id
    MATCHED_PRODUCTS_TABLE_ID  = var.matched_products_table_id
    CANDIDATE_STATUS_TABLE_ID   = module.bigquery.candidate_status_table_id
    CANDIDATE_STATUS_VIEW_ID    = module.bigquery.candidate_status_view_id
  }

  # --------------------------------------------------------
  # CONNECT NETWORKING TO BACKEND
  # --------------------------------------------------------
  # Use the IP reserved in the networking module.
  # This provides a valid value for Pydantic immediately.
  # --------------------------------------------------------
  lb_domain    = local.final_domain_name
  frontend_url = "https://${local.final_domain_name}"

  labels     = var.labels
  depends_on = [module.networking]
}

# FRONTEND MODULE.
module "frontend" {
  source                = "./frontend"
  project_id            = var.project_id
  region                = var.location
  app_name              = var.app_name
  frontend_source_dir   = "${path.root}/../src/webapp/frontend"
  frontend_project_name = "client-app" # Check the 'angular.json > outputPath' for the exact name.
  labels                = var.labels
}

# DNS MODULE.
# Provisions the A-record only if Managed DNS is requested.
module "dns" {
  source = "./dns"
  count  = local.use_managed_dns ? 1 : 0

  dns_project_id    = local.dns_target_project
  managed_zone_name = var.dns_config.managed_zone_name
  domain_name       = local.final_domain_name
  lb_ip_address     = module.networking.global_ip
  create_zone       = var.dns_config.create_zone
  zone_dns_name     = var.dns_config.zone_dns_name
}

# LOAD BALANCER MODULE.
module "lb" {
  source = "./lb"

  project_id = var.project_id
  region     = var.location
  app_name   = var.app_name

  # --- Dependency Wiring ---
  cloud_run_service_name = module.backend.service_name
  frontend_bucket_name   = module.frontend.bucket_name

  global_ip = module.networking.global_ip

  # --- Configuration ---
  lb_settings = {
    enable_cdn = var.lb_config.enable_cdn

    domain_name = local.final_domain_name

    use_managed_certs = var.lb_config.use_managed_certs
    ssl_policy        = var.lb_config.ssl_policy
    custom_cert_names = var.lb_config.custom_cert_names
  }

  armor_settings = var.armor_settings
  labels         = var.labels
}
