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

# terraform/main.tf

# ------------------------------------------------------------------------------
# TERRAFORM & PROVIDER CONFIGURATION
# ------------------------------------------------------------------------------

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.3.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 7.3.0"
    }
  }
}

provider "google" {
  project               = var.project_id
  billing_project       = var.project_id
  user_project_override = true
}

provider "google-beta" {
  project               = var.project_id
  billing_project       = var.project_id
  user_project_override = true
}

# ------------------------------------------------------------------------------
# DATA SOURCES
# ------------------------------------------------------------------------------

data "google_project" "project" {}

# ------------------------------------------------------------------------------
# LOCAL RESOURCES
# ------------------------------------------------------------------------------

resource "random_id" "default" {
  byte_length = 8
}

# ------------------------------------------------------------------------------
# PROJECT SETUP MODULE
# ------------------------------------------------------------------------------

module "project_setup" {
  source             = "./modules/project_setup"
  project_id         = var.project_id
  project_number     = data.google_project.project.number
  location           = var.location
  service_account_id = var.service_account
  repository_id      = var.repository_id
}

# ------------------------------------------------------------------------------
# BUILD MODULE
# ------------------------------------------------------------------------------

module "build" {
  source        = "./modules/build"
  project_id    = var.project_id
  location      = var.location
  repository_id = module.project_setup.repository_id
  deploy_webapp = var.deploy_webapp
  depends_on    = [module.project_setup]
}

# ------------------------------------------------------------------------------
# PIPELINE MODULE
# ------------------------------------------------------------------------------

module "pipeline" {
  source = "./modules/pipeline"

  # Project & Service Account
  project_id            = var.project_id
  location              = var.location
  service_account_email = module.project_setup.service_account_email

  # BigQuery
  bigquery_dataset_id = var.bigquery_dataset_id
  merchant_id         = var.merchant_id
  ads_customer_id     = var.ads_customer_id
  refresh_window_days = var.refresh_window_days

  # Embeddings & Vector Search
  vector_search_embedding_dimensions = var.vector_search_embedding_dimensions
  number_of_matched_products         = var.number_of_matched_products
  gcs_embeddings_bucket_name         = var.gcs_embeddings_bucket_name
  gcs_bucket_ttl_days                = var.gcs_bucket_ttl_days
  embedding_model_name               = var.embedding_model_name

  # Cloud Functions & Jobs
  random_id_prefix      = random_id.default.hex
  product_limit         = var.product_limit
  generative_model_name = var.generative_model_name
  repository_id         = var.repository_id
  video_limit           = var.video_limit
  spreadsheet_id        = var.spreadsheet_id
  api_key_secret_id     = module.project_setup.api_key_secret_id

  # Images from Build Module
  queue_products_image = module.build.image_uris["queue-products"]
  queue_videos_image   = module.build.image_uris["queue-videos"]
  depends_on           = [module.build, module.project_setup]
}

# ------------------------------------------------------------------------------
# WEBAPP MODULE
# ------------------------------------------------------------------------------

module "webapp" {
  source = "./modules/webapp"
  count  = var.deploy_webapp ? 1 : 0

  project_id     = var.project_id
  project_number = data.google_project.project.number
  location       = var.location
  app_name       = var.repository_id

  # Image from Build Module
  backend_image = lookup(module.build.image_uris, "webapp-backend", null)

  # Service Account
  service_account_email = module.project_setup.service_account_email

  # BigQuery
  bigquery_dataset_id       = module.pipeline.bigquery_dataset_id
  video_analysis_table_id   = module.pipeline.video_analysis_table_id
  matched_products_table_id = module.pipeline.matched_products_table_id
  matched_products_view_id  = module.pipeline.matched_products_view_id
  latest_products_table_id  = module.pipeline.latest_products_table_id

  # Networking
  networking_config = {
    subnet_cidr = "10.1.0.0/24" # Use a different CIDR than default if needed
  }
  depends_on = [module.build, module.project_setup]
}

