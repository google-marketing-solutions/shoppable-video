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

# terraform/modules/webapp/bigquery/outputs.tf

output "candidate_status_table_id" {
  value = google_bigquery_table.candidate_status.table_id
}

output "candidate_status_view_id" {
  value = google_bigquery_table.candidate_status_view.table_id
}

output "google_ads_insertion_requests_table_id" {
  value = google_bigquery_table.google_ads_insertion_requests.table_id
}

output "ad_group_insertion_status_table_id" {
  value = google_bigquery_table.ad_group_insertion_status.table_id
}
