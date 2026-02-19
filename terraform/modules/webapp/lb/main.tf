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

# terraform/modules/webapp/lb/main.tf

# ------------------------------------------------------------------------------
# SERVERLESS NETWORK ENDPOINT GROUP (NEG)
# ------------------------------------------------------------------------------
# Creates a Serverless NEG to route traffic to the Cloud Run service.
# This component acts as the bridge between the Global LB and the Regional Cloud Run.
# ------------------------------------------------------------------------------

resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  name                  = "${var.app_name}-serverless-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  project               = var.project_id
  cloud_run {
    service = var.cloud_run_service_name
  }
}

# ------------------------------------------------------------------------------
# BACKEND SERVICES
# ------------------------------------------------------------------------------

# Creates the Backend Service for API traffic (Dynamic Content).
# This service connects the URL map to the Cloud Run NEG and attaches Cloud Armor.
resource "google_compute_backend_service" "api_backend" {
  name       = "${var.app_name}-api-backend"
  protocol   = "HTTPS"
  project    = var.project_id
  enable_cdn = false # CDN is disabled for APIs to ensure data freshness.

  backend {
    group = google_compute_region_network_endpoint_group.serverless_neg.id
  }

  iap {
    enabled = var.iap_config.enable_iap
  }
  # Attaches the Cloud Armor security policy if enabled.
  security_policy = var.armor_settings.enable_cloud_armor ? google_compute_security_policy.edge_sec[0].id : null
}

resource "google_iap_web_backend_service_iam_member" "domain_access" {
  for_each            = var.iap_config.enable_iap ? toset(var.iap_config.access_members) : toset([])
  project             = var.project_id
  web_backend_service = google_compute_backend_service.api_backend.name
  role                = "roles/iap.httpsResourceAccessor"
  member              = each.value
}


# Creates the Backend Bucket for Frontend traffic (Static Content).
# This connects the URL map to the GCS bucket hosting the application assets.
resource "google_compute_backend_bucket" "static_backend" {
  name        = "${var.app_name}-static-backend"
  bucket_name = var.frontend_bucket_name
  project     = var.project_id
  enable_cdn  = var.lb_settings.enable_cdn
}

# ------------------------------------------------------------------------------
# SSL CERTIFICATES
# ------------------------------------------------------------------------------
# Creates a Google-managed SSL certificate if requested.
# This certificate will be automatically provisioned and renewed by Google.
# ------------------------------------------------------------------------------

resource "google_compute_managed_ssl_certificate" "default" {
  count = var.lb_settings.use_managed_certs && var.lb_settings.domain_name != null ? 1 : 0

  name    = "${var.app_name}-managed-cert"
  project = var.project_id

  managed {
    domains = [var.lb_settings.domain_name]
  }
}

# ------------------------------------------------------------------------------
# ROUTING AND PROXY
# ------------------------------------------------------------------------------

# Creates the URL Map to define routing rules.
# Routes '/api/*' to Cloud Run (API Backend) and everything else to GCS (Static Backend).
resource "google_compute_url_map" "default" {
  name            = "${var.app_name}-url-map"
  project         = var.project_id
  default_service = google_compute_backend_bucket.static_backend.id

  host_rule {
    hosts        = ["*"]
    path_matcher = "all-paths"
  }

  path_matcher {
    name            = "all-paths"
    default_service = google_compute_backend_bucket.static_backend.id

    # Specific routing rule for API calls.
    path_rule {
      paths   = ["/api/*", "/docs", "/docs/*", "/openapi.json"]
      service = google_compute_backend_service.api_backend.id
    }
  }
}

# Creates the Target HTTPS Proxy.
# This proxy terminates SSL connections at the edge using the configured certificate.
resource "google_compute_target_https_proxy" "default" {
  name    = "${var.app_name}-https-proxy"
  project = var.project_id
  url_map = google_compute_url_map.default.id

  ssl_certificates = (
    var.lb_settings.use_managed_certs && var.lb_settings.domain_name != null
    ? [google_compute_managed_ssl_certificate.default[0].id] # Google-managed Certificate.
    : [
      for name in var.lb_settings.custom_cert_names :
      "projects/${var.project_id}/global/sslCertificates/${name}"
    ] # User Provided (Expanded to full IDs).
  )
}

# Creates the Global Forwarding Rule.
# This is the public entry point that binds the static IP to the HTTPS proxy.
resource "google_compute_global_forwarding_rule" "default" {
  name       = "${var.app_name}-forwarding-rule"
  project    = var.project_id
  target     = google_compute_target_https_proxy.default.id
  port_range = "443"
  ip_address = var.global_ip
  labels     = var.labels
}

# ------------------------------------------------------------------------------
# HTTP-TO-HTTPS REDIRECT
# ------------------------------------------------------------------------------
resource "google_compute_url_map" "https_redirect" {
  name    = "${var.app_name}-https-redirect"
  project = var.project_id
  default_url_redirect {
    https_redirect         = true
    strip_query            = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

resource "google_compute_target_http_proxy" "https_redirect" {
  name    = "${var.app_name}-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.https_redirect.id
}

resource "google_compute_global_forwarding_rule" "https_redirect" {
  name       = "${var.app_name}-http-forwarding-rule"
  project    = var.project_id
  target     = google_compute_target_http_proxy.https_redirect.id
  port_range = "80"
  ip_address = var.global_ip # Uses the SAME IP as HTTPS.
  labels     = var.labels
}
