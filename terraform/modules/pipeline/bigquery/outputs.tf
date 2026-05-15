# Copyright 2026 Google LLC
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

# terraform/modules/pipeline/bigquery/outputs.tf

output "dataset_id" {
  description = "The ID of the BigQuery dataset."
  value       = google_bigquery_dataset.dataset.dataset_id
}

output "product_embeddings_table_name" {
  description = "The name of the BigQuery table storing product embeddings."
  value       = google_bigquery_table.product_embeddings.table_id
}

output "video_analysis_table_name" {
  description = "The name of the BigQuery table storing video analysis metadata."
  value       = google_bigquery_table.video_analysis.table_id
}

output "matched_products_table_name" {
  description = "The name of the BigQuery table storing matched products."
  value       = google_bigquery_table.matched_products.table_id
}

output "products_table_name" {
  description = "The name of the BigQuery table storing product catalog details."
  value       = "Products_${var.merchant_id}"
}

output "latest_products_table_name" {
  description = "The name of the BigQuery view/table for latest product updates."
  value       = "Products_${var.merchant_id}_Latest"
}

output "latest_products_topic_id" {
  description = "The Pub/Sub topic ID published to when latest products sync completes."
  value       = google_pubsub_topic.latest_products_done.id
}

output "matched_products_topic_id" {
  description = "The Pub/Sub topic ID published to when matched products analysis completes."
  value       = google_pubsub_topic.matched_products_done.id
}
