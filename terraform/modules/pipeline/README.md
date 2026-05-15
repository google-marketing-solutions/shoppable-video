# Pipeline Module

This Terraform module provisions the core asynchronous data processing, AI analysis, and multimodal embedding generation pipeline for the Shoppable Video solution. It orchestrates data ingestion from Google Merchant Center and Google Ads, coordinates AI-driven video analysis via Gemini, and manages product matching analytics in BigQuery.

## Architecture Overview

The module orchestrates several interconnected microservices and submodules:
*   **BigQuery Analytics (`./bigquery`)**: Creates the central BigQuery dataset (`shoppable_video`), schemas for product embeddings and video analysis, scheduled queries for matching analytics, and configures automated Merchant Center data transfers.
*   **Embedding Generation Pipeline**:
    *   **Cloud Function (`./functions`)**: Deploys `generate-embedding-tf` to generate multimodal vector embeddings for product images and metadata using Gemini embedding models.
    *   **Cloud Tasks (`./tasks`)**: Provisions `generate-embedding-queue-tf` to throttle and manage embedding generation workloads.
    *   **Cloud Run Job (`./jobs`)**: Deploys `queue-products-tf` to batch pull products from BigQuery and push them to Cloud Tasks.
    *   **Cloud Scheduler (`./scheduler`)**: Automates daily product catalog embedding runs (`0 0 * * *`).
*   **Video Analysis Pipeline**:
    *   **Cloud Function (`./functions`)**: Deploys `analyze-video-tf` to inspect video creative and intelligently map relevant merchandise using Gemini multimodal generative models.
    *   **Cloud Tasks (`./tasks`)**: Provisions `video-inventory-analysis-queue-tf` to manage video analysis execution queues.
    *   **Cloud Run Job (`./jobs`)**: Deploys `queue-videos-tf` to fetch active video inventory from Google Ads campaigns or manual Google Sheets and enqueue them for analysis.
    *   **Cloud Scheduler (`./scheduler`)**: Automates recurring video inventory analysis every 6 hours (`0 */6 * * *`).

## Prerequisites

To apply this module, the executing user or service account must have the following roles on the target Google Cloud Project:
*   `roles/bigquery.admin` (to create datasets, tables, and data transfer configs)
*   `roles/cloudfunctions.admin` (to deploy Cloud Functions)
*   `roles/run.admin` (to deploy Cloud Run Jobs)
*   `roles/cloudtasks.admin` (to create task queues)
*   `roles/cloudscheduler.admin` (to create scheduler jobs)
*   `roles/iam.serviceAccountUser` (to attach the pipeline service account to compute resources)

## Usage Example

```hcl
module "pipeline" {
  source                             = "./modules/pipeline"
  project_id                         = "my-gcp-project-id"
  location                           = "us-central1"
  service_account_email              = "shoppable-video-sa@my-gcp-project-id.iam.gserviceaccount.com"
  bigquery_dataset_id                = "shoppable_video"
  merchant_id                        = "123456789"
  google_ads_customer_id             = "123-456-7890"
  vector_search_embedding_dimensions = 3072
  number_of_matched_products         = 10
  gcs_embeddings_bucket_name         = "shoppable-video-embeddings"
  gcs_bucket_ttl_days                = 90
  random_id_prefix                   = "a1b2c3d4"
  embedding_model_name               = "gemini-embedding-2-preview"
  embed_images                       = true
  num_images_to_embed                = 3
  product_limit                      = 1000
  generative_model_name              = "gemini-2.5-flash"
  repository_id                      = "shoppable-video"
  video_limit                        = 10
  api_key_secret_id                  = "shoppable_video_api_key"
  queue_products_image               = "us-central1-docker.pkg.dev/my-gcp-project-id/shoppable-video/queue-products:latest"
  queue_videos_image                 = "us-central1-docker.pkg.dev/my-gcp-project-id/shoppable-video/queue-videos:latest"
}
```

## Inputs

| Name | Type | Description | Default | Required |
| :--- | :--- | :--- | :--- | :--- |
| `project_id` | `string` | The Google Cloud Project ID. | n/a | Yes |
| `location` | `string` | The Google Cloud region/location for deploying resources. | n/a | Yes |
| `service_account_email` | `string` | The service account email to execute pipeline resources and tasks. | n/a | Yes |
| `bigquery_dataset_id` | `string` | The BigQuery dataset ID for storing analytics and embeddings. | n/a | Yes |
| `merchant_id` | `string` | The Google Merchant Center Account ID containing product data. | n/a | Yes |
| `api_key_secret_id` | `string` | The Secret Manager ID containing the Gemini API key. | n/a | Yes |
| `random_id_prefix` | `string` | A prefix for random ID generation to ensure unique storage bucket names. | n/a | Yes |
| `embedding_model_name` | `string` | The name of the Gemini embedding model to use. | n/a | Yes |
| `vector_search_embedding_dimensions` | `number` | The number of dimensions for vector search embeddings. | n/a | Yes |
| `embed_images` | `bool` | Whether to generate embeddings for product images. | n/a | Yes |
| `num_images_to_embed` | `number` | The number of product images to embed per product. | n/a | Yes |
| `generative_model_name` | `string` | The name of the Gemini generative model to use for video analysis. | n/a | Yes |
| `product_limit` | `number` | The maximum number of products to queue per run. | n/a | Yes |
| `video_limit` | `number` | The maximum number of videos to queue per run. | n/a | Yes |
| `number_of_matched_products` | `number` | The number of top matched products to retrieve per video. | n/a | Yes |
| `gcs_embeddings_bucket_name` | `string` | The name of the GCS bucket for embeddings. | n/a | Yes |
| `gcs_bucket_ttl_days` | `number` | The TTL (in days) for objects in the GCS bucket. | n/a | Yes |
| `repository_id` | `string` | The Artifact Registry repository ID. | n/a | Yes |
| `google_ads_customer_id` | `string` | The Google Ads Customer ID. | `null` | No |
| `spreadsheet_id` | `string` | The ID of the Google Sheet for manual video entry. | `null` | No |
| `developer_token_secret_id` | `string` | The Secret Manager ID containing the Google Ads developer token. | `null` | No |
| `queue_products_image` | `string` | The fully qualified Docker image URI for the queue-products job. | `null` | No |
| `queue_videos_image` | `string` | The fully qualified Docker image URI for the queue-videos job. | `null` | No |

## Outputs

| Name | Description |
| :--- | :--- |
| `bigquery_dataset_id` | The ID of the BigQuery dataset used for storing shoppable video analytics. |
| `video_analysis_table_id` | The ID of the BigQuery table storing video analysis results. |
| `matched_products_table_id` | The ID of the BigQuery table storing matched product mappings. |
| `products_table_id` | The ID of the BigQuery table storing product catalog embeddings. |
| `latest_products_table_id` | The ID of the BigQuery view or table for latest product syncs. |
