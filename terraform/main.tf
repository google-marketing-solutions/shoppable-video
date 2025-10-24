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
  source                = "./modules/bigquery"
  project_id            = data.google_project.project.project_id
  service_account_email = google_service_account.service_account.email
  bigquery_dataset_id   = var.bigquery_dataset_id
  merchant_id           = var.merchant_id
  ads_customer_id       = var.ads_customer_id
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
    LOCATION                 = var.location
    EMBEDDING_DIMENSIONALITY = var.vector_search_embedding_dimensions
    VECTOR_SEARCH_INDEX_NAME = module.vertex_ai.index_resource_name
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

module "functions_queue_products" {
  source                = "./modules/functions"
  project_id            = data.google_project.project.project_id
  service_account_email = google_service_account.service_account.email
  location              = var.location
  function_name         = "queue-products-tf"
  function_description  = "Queues new products to Cloud Tasks."
  source_dir            = "../src/product_embeddings/queue_products"
  entry_point           = "run"
  runtime               = "python313"
  environment_variables = {
    PROJECT_ID            = data.google_project.project.name
    DATASET_ID            = module.bigquery.dataset_id
    QUEUE_ID              = module.tasks_product_embeddings_queue.queue_name
    LOCATION              = var.location
    MERCHANT_ID           = var.merchant_id
    CLOUD_FUNCTION_URL    = module.functions_generate_embedding.function_url
    SERVICE_ACCOUNT_EMAIL = google_service_account.service_account.email
  }
  max_instance_count = 1
  timeout_seconds    = 300
  random_id_prefix   = random_id.default.hex
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
  function_url          = module.functions_queue_products.function_url
  service_account_email = google_service_account.service_account.email
  body                  = jsonencode({
    product_limit = var.product_limit
  })
}

# ------------------------------------------------------------------------------
# VECTOR SEARCH INDEXING MODULE
# ------------------------------------------------------------------------------
module "vertex_ai" {
  source               = "./modules/vertex_ai"
  project_id           = var.project_id
  location             = var.location
  index_display_name   = "shoppable-video-product-embeddings"
  embedding_dimensions = var.vector_search_embedding_dimensions
}

module "jobs_import_index" {
  source                = "./modules/jobs"
  project_id            = data.google_project.project.project_id
  service_account_email = google_service_account.service_account.email
  location              = var.location
  job_name              = "import-index-tf"
  image                 = "${var.location}-docker.pkg.dev/${var.project_id}/${var.repository_id}/import_index:latest"
  timeout               = "3600s"
  retries               = 0
  environment_variables = {
    PROJECT_ID               = data.google_project.project.project_id
    LOCATION                 = var.location
    DATASET_ID               = module.bigquery.dataset_id
    TABLE_NAME               = module.bigquery.product_embeddings_table_name
    VECTOR_SEARCH_INDEX_NAME = module.vertex_ai.index_resource_name
  }
}

# module "scheduler_update_vector_search_index" {
#   source                = "./modules/scheduler"
#   name                  = "scheduled-build-vector-search-index"
#   project_id            = data.google_project.project.project_id
#   location              = var.location
#   schedule              = "0 0 1 * *"
#   job_name              = module.jobs_update_vector_search_index.job_name
#   service_account_email = google_service_account.service_account.email
#   body                  = jsonencode({})
# }
