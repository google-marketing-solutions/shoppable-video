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

# terraform/modules/pipeline/bigquery/main.tf

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
  lifecycle {
    prevent_destroy = true
  }
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

locals {
  vector_index_query = <<-EOT
      # Vector Dimensionality = ${var.vector_search_embedding_dimensions}
      CREATE OR REPLACE VECTOR INDEX product_embeddings_index
      ON `${google_bigquery_dataset.dataset.project}.${google_bigquery_dataset.dataset.dataset_id}.${google_bigquery_table.product_embeddings.table_id}`(embedding)
      STORING(id, embedding_metadata)
      OPTIONS(index_type = 'IVF');
  EOT
}

resource "google_bigquery_job" "create_vector_index" {
  job_id = "create_vector_index_job_${md5(local.vector_index_query)}"
  query {
    query              = local.vector_index_query
    create_disposition = ""
    write_disposition  = ""
  }
  depends_on = [google_bigquery_table.product_embeddings]
}


resource "google_bigquery_data_transfer_config" "ads_transfer" {
  count                  = var.ads_customer_id != null ? 1 : 0
  display_name           = "ads_transfer"
  data_source_id         = "google_ads"
  schedule               = "every 24 hours"
  destination_dataset_id = google_bigquery_dataset.dataset.dataset_id
  params = {
    "customer_id"               = var.ads_customer_id
    "custom_report_table_names" = jsonencode(["videos"])
    "custom_report_queries" = jsonencode([<<EOT
      SELECT
        customer.id,
        customer.descriptive_name,
        campaign.id,
        campaign.name,
        campaign.advertising_channel_type,
        campaign.advertising_channel_sub_type,
        campaign.bidding_strategy_type,
        ad_group.id,
        ad_group.name,
        ad_group.type,
        ad_group_ad.ad.type,
        video.channel_id,
        video.resource_name,
        video.id,
        video.title,
        video.duration_millis
      FROM video
    EOT
    ])
  }
  service_account_name = var.service_account_email
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_bigquery_table" "video_analysis" {
  project    = google_bigquery_dataset.dataset.project
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = "video_analysis"
  schema = jsonencode([
    {
      "name" : "uuid",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "timestamp",
      "type" : "TIMESTAMP",
      "mode" : "NULLABLE",
      "defaultValueExpression" : "CURRENT_TIMESTAMP()"
    },
    {
      "name" : "source",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "video_id",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "metadata",
      "type" : "RECORD",
      "mode" : "NULLABLE",
      "fields" : [
        {
          "name" : "title",
          "type" : "STRING",
          "mode" : "NULLABLE"
        },
        {
          "name" : "description",
          "type" : "STRING",
          "mode" : "NULLABLE"
        }
      ]
    },
    {
      "name" : "gcs_uri",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "md5_hash",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "status",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "error_message",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "identified_products",
      "type" : "RECORD",
      "mode" : "REPEATED",
      "fields" : [
        {
          "name" : "title",
          "type" : "STRING",
          "mode" : "NULLABLE"
        },
        {
          "name" : "description",
          "type" : "STRING",
          "mode" : "NULLABLE"
        },
        {
          "name" : "color_pattern_style_usage",
          "type" : "STRING",
          "mode" : "NULLABLE"
        },
        {
          "name" : "category",
          "type" : "STRING",
          "mode" : "NULLABLE"
        },
        {
          "name" : "subcategory",
          "type" : "STRING",
          "mode" : "NULLABLE"
        },
        {
          "name" : "video_timestamp",
          "type" : "INTEGER",
          "mode" : "NULLABLE"
        },
        {
          "name" : "relevance_reasoning",
          "type" : "STRING",
          "mode" : "NULLABLE"
        },
        {
          "name" : "embedding",
          "type" : "FLOAT64",
          "mode" : "REPEATED"
        },
        {
          "name" : "uuid"
          "type" : "STRING",
          "mode" : "NULLABLE"
        }
      ]
    }
  ])
}

# Create the BigQuery table with a defined schema
resource "google_bigquery_table" "matched_products" {
  project    = google_bigquery_dataset.dataset.project
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = "matched_products"
  schema = jsonencode([
    {
      "name" : "timestamp",
      "type" : "TIMESTAMP",
      "mode" : "NULLABLE"
    },
    {
      "name" : "uuid",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "identified_product_title",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "mode" : "NULLABLE"
      "name" : "identified_product_description"
      "type" : "STRING"
    },
    {
      "name" : "matched_product_offer_id",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "matched_product_title",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "matched_product_brand",
      "type" : "STRING",
      "mode" : "NULLABLE"
    },
    {
      "name" : "distance",
      "type" : "FLOAT",
      "mode" : "NULLABLE"
    }
  ])
}

resource "google_bigquery_data_transfer_config" "matched_products_analysis" {
  display_name           = "matched_products_scheduled"
  data_source_id         = "scheduled_query"
  schedule               = "every 24 hours"
  destination_dataset_id = google_bigquery_dataset.dataset.dataset_id
  params = {
    query = templatefile("${path.module}/templates/matched_products.sql",
      {
        PROJECT_ID                    = var.project_id
        DATASET_ID                    = google_bigquery_dataset.dataset.dataset_id
        VIDEO_ANALYSIS_TABLE_NAME     = google_bigquery_table.video_analysis.table_id
        PRODUCT_EMBEDDINGS_TABLE_NAME = google_bigquery_table.product_embeddings.table_id
        MATCHED_PRODUCTS_TABLE_NAME   = google_bigquery_table.matched_products.table_id
        REFRESH_WINDOW_DAYS           = var.refresh_window_days
        NUM_OF_MATCHED_PRODUCTS       = var.number_of_matched_products
      }
    )
    destination_table_name_template = "matched_products"
    write_disposition               = "WRITE_APPEND"
  }
  service_account_name = var.service_account_email
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_bigquery_data_transfer_config" "latest_products" {
  display_name   = "latest_products_scheduled"
  data_source_id = "scheduled_query"
  schedule       = "every 6 hours"
  params = {
    query = templatefile("${path.module}/templates/latest_products.sql",
      {
        PROJECT_ID  = var.project_id
        DATASET_ID  = google_bigquery_dataset.dataset.dataset_id
        MERCHANT_ID = var.merchant_id
      }
    )
  }
  service_account_name = var.service_account_email
  lifecycle {
    prevent_destroy = true
  }
}


resource "google_bigquery_table" "matched_products_view" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = "matched_products_view"
  view {
    query          = <<EOF
    SELECT
      timestamp,
      uuid,
      identified_product_title,
      identified_product_description,
      matched_product_offer_id,
      matched_product_title,
      matched_product_brand,
      distance,
    FROM `${var.project_id}.${google_bigquery_dataset.dataset.dataset_id}.${google_bigquery_table.matched_products.table_id}`
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY uuid, matched_product_offer_id
      ORDER BY timestamp DESC
    ) = 1
    EOF
    use_legacy_sql = false
  }
  depends_on = [google_bigquery_table.matched_products]
}

