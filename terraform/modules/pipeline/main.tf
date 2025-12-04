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

locals {
  jobs_queue_videos_env_vars = merge(
    {
      PROJECT_ID         = var.project_id
      DATASET_ID         = module.bigquery.dataset_id
      QUEUE_ID           = module.tasks_video_analysis_queue.queue_name
      LOCATION           = var.location
      CLOUD_FUNCTION_URL = module.functions_analyze_video.function_url
      VIDEO_LIMIT        = var.video_limit
    },
    var.ads_customer_id != null ? { "ADS_CUSTOMER_ID" = var.ads_customer_id } : {},
    var.spreadsheet_id != null ? { "SPREADSHEET_ID" = var.spreadsheet_id } : {}
  )
}

# ------------------------------------------------------------------------------
# CORE SERVICE MODULES (Storage, BigQuery)
# ------------------------------------------------------------------------------

module "bigquery" {
  source                             = "./bigquery"
  project_id                         = var.project_id
  service_account_email              = var.service_account_email
  bigquery_dataset_id                = var.bigquery_dataset_id
  merchant_id                        = var.merchant_id
  ads_customer_id                    = var.ads_customer_id
  refresh_window_days                = var.refresh_window_days
  vector_search_embedding_dimensions = var.vector_search_embedding_dimensions
  number_of_matched_products         = var.number_of_matched_products
}

module "storage" {
  source                = "./storage"
  project_id            = var.project_id
  bucket_name           = var.gcs_embeddings_bucket_name
  bucket_location       = var.location
  bucket_ttl_days       = var.gcs_bucket_ttl_days
  service_account_email = var.service_account_email
}

# ------------------------------------------------------------------------------
# EMBEDDING GENERATION PIPELINE MODULES (Functions, Tasks, Scheduler)
# ------------------------------------------------------------------------------

module "functions_generate_embedding" {
  source                = "./functions"
  project_id            = var.project_id
  service_account_email = var.service_account_email
  location              = var.location
  function_name         = "generate-embedding-tf"
  function_description  = "Generates embeddings from Cloud Task message."
  source_dir            = "${path.module}/../../../src/pipeline/product_embeddings/generate_embedding"
  entry_point           = "run"
  runtime               = "python313"
  environment_variables = {
    PROJECT_ID               = var.project_id
    DATASET_ID               = module.bigquery.dataset_id
    TABLE_NAME               = module.bigquery.product_embeddings_table_name
    EMBEDDING_DIMENSIONALITY = var.vector_search_embedding_dimensions
    EMBEDDING_MODEL_NAME     = var.embedding_model_name
  }
  secret_environment_variables = {
    gemini_api_key = {
      key     = "GOOGLE_API_KEY"
      secret  = var.secret_id
      version = "latest"
    }
  }
  random_id_prefix = var.random_id_prefix
  depends_on = [
    module.storage
  ]
}

module "tasks_product_embeddings_queue" {
  source                = "./tasks"
  name                  = "generate-embedding-queue-tf"
  project_id            = var.project_id
  location              = var.location
  service_account_email = var.service_account_email
  function_url          = module.functions_generate_embedding.function_url
}

module "jobs_queue_products" {
  source                = "./jobs"
  project_id            = var.project_id
  service_account_email = var.service_account_email
  location              = var.location
  job_name              = "queue-products-tf"
  image                 = "${var.location}-docker.pkg.dev/${var.project_id}/${var.repository_id}/queue-products:latest"
  timeout               = "1800s"
  retries               = 0
  environment_variables = {
    PROJECT_ID         = var.project_id
    DATASET_ID         = module.bigquery.dataset_id
    MERCHANT_ID        = var.merchant_id
    QUEUE_ID           = module.tasks_product_embeddings_queue.queue_name
    LOCATION           = var.location
    CLOUD_FUNCTION_URL = module.functions_generate_embedding.function_url
    PRODUCT_LIMIT      = var.product_limit
  }
  depends_on = [
    module.storage
  ]
}

module "scheduler_queue_products" {
  source                = "./scheduler"
  name                  = "scheduled-queue-products"
  project_id            = var.project_id
  location              = var.location
  job_name              = module.jobs_queue_products.job_name
  service_account_email = var.service_account_email
  schedule              = "0 0 * * *"
}

# ------------------------------------------------------------------------------
# VIDEO ANALYSIS PIPELINE MODULES
# ------------------------------------------------------------------------------

module "functions_analyze_video" {
  source                = "./functions"
  project_id            = var.project_id
  service_account_email = var.service_account_email
  location              = var.location
  function_name         = "analyze-video-tf"
  function_description  = "Analyzes videos from Cloud Task message."
  source_dir            = "${path.module}/../../../src/pipeline/video_inventory_analysis/analyze_video"
  entry_point           = "run"
  runtime               = "python313"
  environment_variables = {
    PROJECT_ID               = var.project_id
    DATASET_ID               = module.bigquery.dataset_id
    TABLE_NAME               = module.bigquery.video_analysis_table_name
    GENERATIVE_MODEL_NAME    = var.generative_model_name
    EMBEDDING_MODEL_NAME     = var.embedding_model_name
    EMBEDDING_DIMENSIONALITY = var.vector_search_embedding_dimensions
  }
  secret_environment_variables = {
    gemini_api_key = {
      key     = "GOOGLE_API_KEY"
      secret  = var.secret_id
      version = "latest"
    }
  }
  random_id_prefix = var.random_id_prefix
  depends_on = [
    module.storage
  ]
}

module "tasks_video_analysis_queue" {
  source                = "./tasks"
  name                  = "video-inventory-analysis-queue-tf"
  project_id            = var.project_id
  location              = var.location
  service_account_email = var.service_account_email
  function_url          = module.functions_analyze_video.function_url
}


module "jobs_queue_videos" {
  source                = "./jobs"
  project_id            = var.project_id
  service_account_email = var.service_account_email
  location              = var.location
  job_name              = "queue-videos-tf"
  image                 = "${var.location}-docker.pkg.dev/${var.project_id}/${var.repository_id}/queue-videos:latest"
  timeout               = "1800s"
  retries               = 0
  environment_variables = local.jobs_queue_videos_env_vars
  depends_on = [
    module.storage
  ]
}

module "scheduler_queue_videos" {
  source                = "./scheduler"
  name                  = "scheduled-queue-videos"
  project_id            = var.project_id
  location              = var.location
  schedule              = "0 */6 * * *"
  job_name              = module.jobs_queue_videos.job_name
  service_account_email = var.service_account_email
}
