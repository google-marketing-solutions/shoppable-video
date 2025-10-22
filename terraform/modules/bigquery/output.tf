# modules/bigquery/output.tf

output "dataset_id" {
  value = google_bigquery_dataset.dataset.dataset_id
}
output "table_name" {
  value = google_bigquery_table.product_embeddings.table_id
}
