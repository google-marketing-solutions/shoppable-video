# modules/bigquery/main.tf

resource "google_project_service" "enable_apis" {
  project = var.project_id
  for_each = toset(
    [
      "bigquery.googleapis.com",
      "bigquerydatatransfer.googleapis.com"
    ]
  )
  service            = each.key
  disable_on_destroy = false
}

resource "google_project_service_identity" "bq_data_transfer" {
  provider = google-beta
  project  = var.project_id
  service  = "bigquerydatatransfer.googleapis.com"
}

resource "google_project_iam_member" "bq_dt_sa" {
  for_each = toset([
    "roles/iam.serviceAccountTokenCreator",
    "roles/bigquerydatatransfer.serviceAgent"
  ])
  role    = each.key
  project = var.project_id
  member  = google_project_service_identity.bq_data_transfer.member
}


resource "google_bigquery_dataset" "dataset" {
  dataset_id  = var.bigquery_dataset_id
  description = "Shoppable Video Dataset"
  access {
    role          = "OWNER"
    user_by_email = var.service_account_email
  }
  access {
    role          = "WRITER"
    user_by_email = google_project_service_identity.bq_data_transfer.email
  }
  lifecycle {
    ignore_changes  = [access]
    prevent_destroy = true
  }
  depends_on = [google_project_service.enable_apis]
}

resource "google_bigquery_data_transfer_config" "merchant_center_config" {
  display_name           = "merchant_center_transfer"
  data_source_id         = "merchant_center"
  schedule               = "every 24 hours"
  destination_dataset_id = google_bigquery_dataset.dataset.dataset_id
  params = {
    "merchant_id"     = var.merchant_id
    "export_products" = "true"
  }
  service_account_name = var.service_account_email
}

# Create the BigQuery table with a defined schema
resource "google_bigquery_table" "product_embeddings" {
  project    = google_bigquery_dataset.dataset.project
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = "product_embeddings"
  schema = jsonencode([
    {
      "name" : "id",
      "type" : "STRING",
      "mode" : "NULLABLE",
      "description" : "The unique identifier for the offer"
    },
    {
      "name" : "insertion_timestamp",
      "type" : "TIMESTAMP",
      "mode" : "NULLABLE",
      "description" : "When the record was inserted"
    },
    {
      "name" : "embedding",
      "type" : "FLOAT64",
      "mode" : "REPEATED",
      "description" : "The embedding vector"
    },
    {
      "name" : "embedding_metadata",
      "type" : "RECORD",
      "mode" : "NULLABLE",
      "fields" : [
        {
          "name" : "title",
          "type" : "STRING",
          "mode" : "NULLABLE",
          "description" : "The title of the offer"
        },
        {
          "name" : "brand",
          "type" : "STRING",
          "mode" : "NULLABLE",
          "description" : "The brand of the offer"
        }
      ]
    }
  ])
}
