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

# modules/cloudscheduler/main.tf

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
    uri         = var.function_url != null ? var.function_url : "https://${var.location}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.job_name}:run"
    # body needs to be encoded as bytes
    body = var.body != null ? base64encode(var.body) : null
    headers = {
      "Content-Type" = "application/json"
    }
    oidc_token {
      service_account_email = var.service_account_email
    }
  }
}
