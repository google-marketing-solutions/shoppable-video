# modules/apis/main.tf

resource "google_project_service" "enable_apis" {
  project = var.project_id
  service = "apikeys.googleapis.com"
  disable_on_destroy = false
}

resource "google_apikeys_key" "api_key" {
  name         = "shoppable-video-generative-language-api-key-prod"
  display_name = "Shoppable Video Generative Language API key"
  project      = var.project_id
  restrictions {
    api_targets {
      service = "generativelanguage.googleapis.com"
    }
  }
  depends_on = [google_project_service.enable_apis]
}

