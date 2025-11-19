# main.tf

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

locals {
  enable_video_queuing = var.spreadsheet_id != null || var.ads_customer_id != null
  jobs_queue_videos_env_vars = merge(
    {
      PROJECT_ID         = data.google_project.project.name
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

resource "null_resource" "prevent_run_without_enable_video_queuing" {
  lifecycle {
    precondition {
      condition     = local.enable_video_queuing
      error_message = "Either spreadsheet_id or ads_customer_id must be provided."
    }
  }
}

# ------------------------------------------------------------------------------
# IAM & SERVICE ACCOUNT
# ------------------------------------------------------------------------------

resource "google_project_service" "enable_apis" {
  for_each = toset([
    "iam.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "generativelanguage.googleapis.com",
    "run.googleapis.com",
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "sheets.googleapis.com",
  ])
  project            = data.google_project.project.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_service_account" "service_account" {
  account_id   = var.service_account
  display_name = "Shoppable Video Service Account"
  depends_on   = [google_project_service.enable_apis]
}

resource "google_project_iam_member" "project" {
  for_each = toset([
    "roles/bigquery.dataOwner",
    "roles/bigquery.jobUser",
    "roles/cloudtasks.enqueuer",
    "roles/cloudtasks.viewer",
    "roles/iam.serviceAccountOpenIdTokenCreator",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/run.invoker",
    "roles/secretmanager.viewer",
    "roles/storage.objectViewer",
    "roles/aiplatform.user"
  ])
  project = data.google_project.project.number
  role    = each.key
  member  = google_service_account.service_account.member
}

# ------------------------------------------------------------------------------
# CORE SERVICE MODULES (APIs, Secrets, Storage, BigQuery)
# ------------------------------------------------------------------------------

module "apis" {
  source     = "./modules/apis"
  project_id = data.google_project.project.project_id
}

module "secrets" {
  source                 = "./modules/secrets"
  project_id             = data.google_project.project.project_id
  service_account_member = google_service_account.service_account.member
  api_key                = module.apis.api_key_string
}

module "bigquery" {
  source                             = "./modules/bigquery"
  project_id                         = data.google_project.project.project_id
  service_account_email              = google_service_account.service_account.email
  bigquery_dataset_id                = var.bigquery_dataset_id
  merchant_id                        = var.merchant_id
  ads_customer_id                    = var.ads_customer_id
}

module "storage" {
  source                = "./modules/storage"
  project_id            = data.google_project.project.project_id
  bucket_name           = var.gcs_embeddings_bucket_name
  bucket_location       = var.location
  bucket_ttl_days       = var.gcs_bucket_ttl_days
  service_account_email = google_service_account.service_account.email
}

resource "google_artifact_registry_repository" "repository" {
  project       = var.project_id
  location      = var.location
  repository_id = var.repository_id
  format        = "DOCKER"
  depends_on = [
    google_project_service.enable_apis
  ]
}


# ------------------------------------------------------------------------------
# EMBEDDING GENERATION PIPELINE MODULES (Functions, Tasks, Scheduler)
# ------------------------------------------------------------------------------

module "functions_generate_embedding" {
  source                = "./modules/functions"
  project_id            = data.google_project.project.project_id
  service_account_email = google_service_account.service_account.email
  location              = var.location
  function_name         = "generate-embedding-tf"
  function_description  = "Generates embeddings from Cloud Task message."
  source_dir            = "../src/product_embeddings/generate_embedding"
  entry_point           = "run"
  runtime               = "python313"
  environment_variables = {
    PROJECT_ID               = data.google_project.project.name
    DATASET_ID               = module.bigquery.dataset_id
    TABLE_NAME               = module.bigquery.product_embeddings_table_name
    EMBEDDING_DIMENSIONALITY = var.vector_search_embedding_dimensions
    EMBEDDING_MODEL_NAME     = var.embedding_model_name
  }
  secret_environment_variables = {
    gemini_api_key = {
      key     = "GOOGLE_API_KEY"
      secret  = module.secrets.secret_id
      version = "latest"
    }
  }
  random_id_prefix = random_id.default.hex
  depends_on = [
    google_project_service.enable_apis,
    module.storage
  ]
}

module "tasks_product_embeddings_queue" {
  source                = "./modules/tasks"
  name                  = "product-embeddings-queue-tf"
  project_id            = data.google_project.project.project_id
  location              = var.location
  service_account_email = google_service_account.service_account.email
  function_url          = module.functions_generate_embedding.function_url
}

module "jobs_queue_products" {
  source                = "./modules/jobs"
  project_id            = data.google_project.project.project_id
  service_account_email = google_service_account.service_account.email
  location              = var.location
  job_name              = "queue-products-tf"
  image                 = "${var.location}-docker.pkg.dev/${var.project_id}/${var.repository_id}/queue-products:latest"
  timeout               = "1800s"
  retries               = 0
  environment_variables = {
    PROJECT_ID         = data.google_project.project.name
    DATASET_ID         = module.bigquery.dataset_id
    MERCHANT_ID        = var.merchant_id
    QUEUE_ID           = module.tasks_product_embeddings_queue.queue_name
    LOCATION           = var.location
    CLOUD_FUNCTION_URL = module.functions_generate_embedding.function_url
    PRODUCT_LIMIT      = var.product_limit
  }
  depends_on = [
    google_project_service.enable_apis,
    module.storage
  ]
}

module "scheduler_queue_products" {
  source                = "./modules/scheduler"
  name                  = "scheduled-queue-products"
  project_id            = data.google_project.project.project_id
  location              = var.location
  job_name              = module.jobs_queue_products.job_name
  service_account_email = google_service_account.service_account.email
}

# ------------------------------------------------------------------------------
# VIDEO ANALYSIS PIPELINE MODULES
# ------------------------------------------------------------------------------

module "functions_analyze_video" {
  source                = "./modules/functions"
  project_id            = data.google_project.project.project_id
  service_account_email = google_service_account.service_account.email
  location              = var.location
  function_name         = "analyze-video-tf"
  function_description  = "Analyzes videos from Cloud Task message."
  source_dir            = "../src/video_inventory_analysis/analyze_video"
  entry_point           = "run"
  runtime               = "python313"
  environment_variables = {
    PROJECT_ID               = data.google_project.project.project_id
    DATASET_ID               = module.bigquery.dataset_id
    TABLE_NAME               = module.bigquery.video_analysis_table_name
    GENERATIVE_MODEL_NAME    = var.generative_model_name
    EMBEDDING_MODEL_NAME     = var.embedding_model_name
    EMBEDDING_DIMENSIONALITY = var.vector_search_embedding_dimensions
  }
  secret_environment_variables = {
    gemini_api_key = {
      key     = "GOOGLE_API_KEY"
      secret  = module.secrets.secret_id
      version = "latest"
    }
  }
  random_id_prefix = random_id.default.hex
  depends_on = [
    google_project_service.enable_apis,
    module.storage
  ]
}

module "tasks_video_analysis_queue" {
  source                = "./modules/tasks"
  name                  = "video-analysis-queue-tf"
  project_id            = data.google_project.project.project_id
  location              = var.location
  service_account_email = google_service_account.service_account.email
  function_url          = module.functions_analyze_video.function_url
}


module "jobs_queue_videos" {
  source                = "./modules/jobs"
  project_id            = data.google_project.project.project_id
  service_account_email = google_service_account.service_account.email
  location              = var.location
  job_name              = "queue-videos-tf"
  image                 = "${var.location}-docker.pkg.dev/${var.project_id}/${var.repository_id}/queue-videos:latest"
  timeout               = "1800s"
  retries               = 0
  environment_variables = local.jobs_queue_videos_env_vars
  depends_on = [
    google_project_service.enable_apis,
    module.storage
  ]
}

module "scheduler_queue_videos" {
  source                = "./modules/scheduler"
  name                  = "scheduled-queue-videos"
  project_id            = data.google_project.project.project_id
  location              = var.location
  schedule              = "0 */6 * * *"
  job_name              = module.jobs_queue_videos.job_name
  service_account_email = google_service_account.service_account.email
}
