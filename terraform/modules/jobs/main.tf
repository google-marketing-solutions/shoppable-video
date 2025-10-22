# modules/jobs/main.tf

resource "google_cloud_run_v2_job" "job" {
  name     = var.job_name
  deletion_protection = false
  location = var.location
  client   = "terraform"
  template {
    template {
      service_account = var.service_account_email
      timeout         = var.timeout
      max_retries     = var.retries
      containers {
        image = var.image
        args  = var.args
        dynamic "env" {
          for_each = var.environment_variables
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }
}
