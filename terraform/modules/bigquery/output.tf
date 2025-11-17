# modules/bigquery/output.tf

output "dataset_id" {
  value = google_bigquery_dataset.dataset.dataset_id
}
output "product_embeddings_table_name" {
  value = google_bigquery_table.product_embeddings.table_id
}
output "video_analysis_table_name" {
  value = google_bigquery_table.video_analysis.table_id
}
