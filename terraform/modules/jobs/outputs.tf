# modules/jobs/outputs.tf

output "job_name" {
  description = "The name of the Cloud Run job."
  value       = google_cloud_run_v2_job.job.name
}
