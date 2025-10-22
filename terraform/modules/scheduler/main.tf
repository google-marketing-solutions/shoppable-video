# modules/cloudscheduler/main.tf

resource "google_project_service" "enable_apis" {
  project = var.project_id
  service = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}


resource "google_cloud_scheduler_job" "scheduler_job" {
  name             = var.name
  region           = var.location
  description      = "Invoke ${var.name} on a schedule."
  schedule         = var.schedule # defaults to "0 * * * *" # Hourly
  time_zone        = "America/New_York"
  attempt_deadline = "300s"
  paused           = true

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = var.function_url != null ? var.function_url : "https://" + var.location + "-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/" + var.project_id + "/jobs/" + var.job_name + ":run"
    # body needs to be encoded as bytes
    body = var.body != null ? base64encode(var.body) : null
    headers = {
      "Content-Type" = "application/json"
    }
    oidc_token {
      service_account_email = var.service_account_email
    }
  }
  depends_on = [
    google_project_service.enable_apis
  ]
}
