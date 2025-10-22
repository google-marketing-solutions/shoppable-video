# modules/storage/output.tf

output "bucket_uri" {
  description = "The URI of the GCS bucket created."
  value       = google_storage_bucket.bucket.url
}
