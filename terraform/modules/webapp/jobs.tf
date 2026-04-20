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

# terraform/modules/webapp/jobs.tf

resource "google_cloud_run_v2_job" "ads_insertion_job" {
  name                = "${var.app_name}-ads-insertion"
  location            = var.location
  project             = var.project_id
  deletion_protection = false

  template {
    template {
      service_account = var.service_account_email

      containers {
        image = var.cloud_run_job_image

        dynamic "env" {
          for_each = {
            for k, v in module.security.secret_ids : k => {
              secret_id = v.secret_id
              version = lookup(var.pinned_secrets, k, v.version)
            }
          }
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.secret_id
                version = env.value.version
              }
            }
          }
        }

        dynamic "env" {
          for_each = {
            PROJECT_ID                = var.project_id
            DATASET_ID                = var.bigquery_dataset_id
            GOOGLE_ADS_INSERTION_REQUESTS_TABLE_ID = module.bigquery.google_ads_insertion_requests_table_id
            AD_GROUP_INSERTION_STATUS_TABLE_ID     = module.bigquery.ad_group_insertion_status_table_id
            GOOGLE_ADS_CUSTOMER_ID                 = var.google_ads_customer_id
          }
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }
}

resource "google_cloud_scheduler_job" "ads_insertion_scheduler" {
  name             = "${var.app_name}-ads-insertion-schedule"
  region           = var.location
  project          = var.project_id
  description      = "Triggers the ads insertion Cloud Run job every 15 minutes."
  schedule         = "*/15 * * * *"
  time_zone        = "America/Los_Angeles"
  attempt_deadline = "300s"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.location}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.ads_insertion_job.name}:run"
    headers = {
      "Content-Type" = "application/json"
    }
    oidc_token {
      service_account_email = var.service_account_email
    }
  }
}
