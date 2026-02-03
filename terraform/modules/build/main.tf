# Copyright 2025 Google LLC
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

# terraform/modules/build/main.tf

# ------------------------------------------------------------------------------
# DOCKER BUILD AND PUSH MODULE
# ------------------------------------------------------------------------------
# Builds and pushes multiple Docker images to Google Artifact Registry.
# Triggers rebuilds only when relevant source files change.
# ------------------------------------------------------------------------------

locals {
  # Root of the repository (assuming terraform/ is one level deep)
  root_dir = abspath("${path.root}/..")

  # Configuration for each image
  _base_images = {
    "queue-products" = {
      dockerfile = "src/pipeline/product_embeddings/queue_products/Dockerfile"
      watch_paths = [
        "src/pipeline/product_embeddings/queue_products",
        "src/pipeline/shared"
      ]
    },
    "queue-videos" = {
      dockerfile = "src/pipeline/video_inventory_analysis/queue_videos/Dockerfile"
      watch_paths = [
        "src/pipeline/video_inventory_analysis/queue_videos",
        "src/pipeline/shared"
      ]
    },
    "webapp-backend" = {
      dockerfile = "src/webapp/backend/Dockerfile"
      watch_paths = [
        "src/webapp/backend"
      ]
    }
  }

  images = {
    for k, v in local._base_images : k => v
    if k != "webapp-backend" || var.deploy_webapp
  }

  # Calculate a hash for each image based on its watch paths, ignoring common non-source files
  image_hashes = {
    for name, config in local.images : name => sha1(join("", [
      for path in config.watch_paths : sha1(join("", [
        for f in fileset("${local.root_dir}/${path}", "**") :
        filesha1("${local.root_dir}/${path}/${f}")
        if length(regexall("(__pycache__|\\.git|\\.venv|\\.DS_Store|\\.md$|\\.pyc$|\\.env$)", f)) == 0
      ]))
    ]))
  }
}

resource "null_resource" "build_push" {
  for_each = local.images

  triggers = {
    hash = local.image_hashes[each.key]
  }

  provisioner "local-exec" {
    command = <<EOT
      IMAGE_URI="${var.location}-docker.pkg.dev/${var.project_id}/${var.repository_id}/${each.key}:${self.triggers.hash}"
      LATEST_TAG="${var.location}-docker.pkg.dev/${var.project_id}/${var.repository_id}/${each.key}:latest"

      echo "Submitting Cloud Build for ${each.key}..."

      # Submit build to Cloud Build
      # We generate a dynamic cloudbuild.yaml to handle the specific Dockerfile path and tags
      gcloud builds submit ${local.root_dir} \
        --project "${var.project_id}" \
        --region "${var.location}" \
        --config <(cat <<YAML
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: [ 'build', '-t', '$IMAGE_URI', '-t', '$LATEST_TAG', '-f', '${each.value.dockerfile}', '.' ]
images:
- '$IMAGE_URI'
- '$LATEST_TAG'
YAML
)
    EOT

    interpreter = ["/bin/bash", "-c"]
  }
}
