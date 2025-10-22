# modules/storage/variables.tf

resource "google_project_service" "enable_apis" {
  project = var.project_id
  service = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_storage_bucket" "bucket" {
  project      = var.project_id
  name         = var.bucket_name
  location     = var.bucket_location

  force_destroy = true
  lifecycle_rule {
    condition {
      age = var.bucket_ttl_days
    }
    action {
      type = "Delete"
    }
  }

  public_access_prevention = "enforced"
  depends_on = [google_project_service.enable_apis]
}

resource "google_storage_bucket_iam_member" "bucket_iam" {
  bucket = google_storage_bucket.bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.service_account_email}"
}
