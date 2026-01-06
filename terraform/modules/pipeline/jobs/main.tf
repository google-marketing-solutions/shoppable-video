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

# terraform/modules/pipeline/jobs/main.tf

resource "google_cloud_run_v2_job" "job" {
  name                = var.job_name
  deletion_protection = false
  location            = var.location
  client              = "terraform"
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
