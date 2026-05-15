# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# terraform/modules/webapp/frontend/main.tf

# ------------------------------------------------------------------------------
# RANDOM SUFFIX GENERATION
# ------------------------------------------------------------------------------
# Generates a random suffix for the bucket name.
# This ensures the bucket name is globally unique across all of Google Cloud.
# ------------------------------------------------------------------------------

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# ------------------------------------------------------------------------------
# GCS BUCKET (STATIC HOSTING)
# ------------------------------------------------------------------------------
# Creates a Google Cloud Storage bucket configured for static website hosting.
# This bucket will serve the compiled Angular application files.
# ------------------------------------------------------------------------------

resource "google_storage_bucket" "frontend" {
  name          = "${var.project_id}-${var.app_name}-${random_id.bucket_suffix.hex}"
  location      = var.region
  force_destroy = true # Allows Terraform to destroy the bucket even if it contains objects.

  # Explicitly enable Uniform Bucket-Level Access.
  # This disables ACLs and satisfies the 'constraints/storage.uniformBucketLevelAccess' policy.
  # ----------------------------------------------------------------------------
  uniform_bucket_level_access = true

  # Configures the bucket to serve 'index.html' for root requests and 404 errors.
  # This 'not_found_page' setting is critical for Angular's Single Page Application (SPA) routing
  # to work correctly when users refresh the page on a sub-route.
  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }

  # ----------------------------------------------------------------------------
  # CORS CONFIGURATION (Conditional)
  # ----------------------------------------------------------------------------
  # Only applied if var.cors_config.enable is true.
  # ----------------------------------------------------------------------------
  dynamic "cors" {
    for_each = var.cors_config.enable ? [1] : []
    content {
      origin          = var.cors_config.origins
      method          = ["GET", "HEAD", "OPTIONS"]
      response_header = ["*"]
      max_age_seconds = 3600
    }
  }

  labels = var.labels

  lifecycle {
    prevent_destroy = true
  }
}

# ------------------------------------------------------------------------------
# PUBLIC READ ACCESS
# ------------------------------------------------------------------------------
# Grants public read access (Storage Object Viewer) to all objects stored in the bucket.
# This makes the website accessible to the public internet.
# ------------------------------------------------------------------------------

resource "google_storage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.frontend.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# ------------------------------------------------------------------------------
# AUTOMATED BUILD AND DEPLOY
# ------------------------------------------------------------------------------
resource "null_resource" "build_and_deploy" {

  # 1. TRIGGER
  # This calculates a hash of all files in the 'src' directory, plus key config files.
  # The build only runs if a code change is observed OR if the bucket ID changes.
  triggers = {
    source_code_hash = sha1(join("", [
      for f in setunion(
        fileset(var.frontend_source_dir, "src/**/*"),
        fileset(var.frontend_source_dir, "{angular.json,package.json,package-lock.json}")
      ) : filesha1("${var.frontend_source_dir}/${f}")
    ]))
    bucket_id = google_storage_bucket.frontend.id
  }

  # 2. THE BUILD COMMAND
  provisioner "local-exec" {
    working_dir = var.frontend_source_dir

    # 'gcloud storage rsync' is generally faster and uses the same auth as gcloud.
    command = <<EOT
      set -e # Exit immediately if any command fails.

      echo "--- 📦 Installing Dependencies ---"
      npm install

      echo "--- 🏗️ Building Angular App ---"
      npm run build -- --configuration production

      echo "--- 🚀 Uploading to Bucket: ${google_storage_bucket.frontend.name} ---"
      cd dist/${var.frontend_project_name}/browser && gcloud storage rsync . gs://${google_storage_bucket.frontend.name} --recursive --delete-unmatched-destination-objects
    EOT

    interpreter = ["/bin/bash", "-c"]
  }

  depends_on = [google_storage_bucket.frontend]
}
