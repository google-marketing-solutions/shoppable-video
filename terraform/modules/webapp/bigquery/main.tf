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

# terraform/modules/webapp/bigquery/main.tf

resource "google_bigquery_table" "candidate_status" {
  project    = var.project_id
  dataset_id = var.dataset_id
  table_id   = "candidate_status"
  schema = jsonencode([
    {
      "name" : "video_analysis_uuid",
      "type" : "STRING",
      "mode" : "REQUIRED"
    },
    {
      "name" : "identified_product_uuid",
      "type" : "STRING",
      "mode" : "REQUIRED"
    },
    {
      "name" : "candidate_offer_id",
      "type" : "STRING",
      "mode" : "REQUIRED"
    },
    {
      "name" : "status",
      "type" : "STRING",
      "mode" : "REQUIRED"
    },
    {
      "name" : "is_added_by_user",
      "type" : "BOOLEAN",
      "mode" : "REQUIRED"
    },
    {
      "name" : "user",
      "type" : "STRING",
      "mode" : "REQUIRED"
    },
    {
      "name" : "modified_timestamp",
      "type" : "TIMESTAMP",
      "mode" : "NULLABLE",
      "defaultValueExpression" : "CURRENT_TIMESTAMP()"
    }
  ])
  lifecycle {
    ignore_changes = [
      schema, # Avoid destructive changes if schema evolves
    ]
  }
}

resource "google_bigquery_table" "candidate_status_view" {
  project    = var.project_id
  dataset_id = var.dataset_id
  table_id   = "candidate_status_view"

  view {
    query          = <<EOF
    SELECT
      video_analysis_uuid,
      identified_product_uuid,
      candidate_offer_id,
      status,
      is_added_by_user,
      user,
      modified_timestamp
    FROM `${var.project_id}.${var.dataset_id}.${google_bigquery_table.candidate_status.table_id}`
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY video_analysis_uuid, identified_product_uuid, candidate_offer_id
      ORDER BY modified_timestamp DESC
    ) = 1
    EOF
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.candidate_status]
}
