# ------------------------------------------------------------------------------
# MODULE OUTPUTS
# ------------------------------------------------------------------------------
# Exposes the bucket name for integration with the Load Balancer module.
# ------------------------------------------------------------------------------

output "bucket_name" {
  description = "The name of the created GCS bucket."
  value       = google_storage_bucket.frontend.name
}
