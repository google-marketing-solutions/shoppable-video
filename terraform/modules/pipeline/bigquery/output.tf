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

# terraform/modules/pipeline/bigquery/output.tf

output "dataset_id" {
  value = google_bigquery_dataset.dataset.dataset_id
}

output "product_embeddings_table_name" {
  value = google_bigquery_table.product_embeddings.table_id
}

output "video_analysis_table_name" {
  value = google_bigquery_table.video_analysis.table_id
}

output "matched_products_table_name" {
  value = google_bigquery_table.matched_products.table_id
}

output "matched_products_view_name" {
  value = google_bigquery_table.matched_products_view.table_id
}

output "products_table_name" {
  value = "${var.project_id}.${google_bigquery_dataset.dataset.dataset_id}.Products_${var.merchant_id}"

}

output "latest_products_table_name" {
  value = "${var.project_id}.${google_bigquery_dataset.dataset.dataset_id}.Products_${var.merchant_id}_Latest"
}


