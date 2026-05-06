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

# terraform/modules/firestore/main.tf

resource "google_firestore_database" "database" {
  project                     = var.project_id
  name                        = var.database_id
  location_id                 = var.location
  type                        = "FIRESTORE_NATIVE"
  concurrency_mode            = "OPTIMISTIC"
  app_engine_integration_mode = "DISABLED"
  delete_protection_state     = "DELETE_PROTECTION_DISABLED"
}

# ------------------------------------------------------------------------------
# COLLECTION GROUP INDEXES (Single Field uses google_firestore_field)
# ------------------------------------------------------------------------------

resource "google_firestore_field" "matched_products_video_uuid_index" {
  project    = var.project_id
  database   = google_firestore_database.database.name
  collection = "matched_products"
  field      = "video_uuid"

  index_config {
    indexes {
      order       = "ASCENDING"
      query_scope = "COLLECTION_GROUP"
    }
    indexes {
      order       = "DESCENDING"
      query_scope = "COLLECTION_GROUP"
    }
  }
}

resource "google_firestore_field" "deployments_video_uuid_index" {
  project    = var.project_id
  database   = google_firestore_database.database.name
  collection = "deployments"
  field      = "video_uuid"

  index_config {
    indexes {
      order       = "ASCENDING"
      query_scope = "COLLECTION_GROUP"
    }
    indexes {
      order       = "DESCENDING"
      query_scope = "COLLECTION_GROUP"
    }
  }
}

# ------------------------------------------------------------------------------
# COMPOSITE INDEXES (Multi-Field uses google_firestore_index)
# ------------------------------------------------------------------------------

resource "google_firestore_index" "ads_insertions_status_timestamp_index" {
  project     = var.project_id
  database    = google_firestore_database.database.name
  collection  = "ads_insertions"
  query_scope = "COLLECTION"

  fields {
    field_path = "status"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timestamp"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "ads_insertions_status_leased_at_index" {
  project     = var.project_id
  database    = google_firestore_database.database.name
  collection  = "ads_insertions"
  query_scope = "COLLECTION"

  fields {
    field_path = "status"
    order      = "ASCENDING"
  }

  fields {
    field_path = "leased_at"
    order      = "ASCENDING"
  }
}

# ------------------------------------------------------------------------------
# SECURITY RULES
# ------------------------------------------------------------------------------

resource "google_firebaserules_ruleset" "firestore" {
  project = var.project_id
  source {
    files {
      content = file("${path.module}/firestore.rules")
      name    = "firestore.rules"
    }
  }
  depends_on = [google_firestore_database.database]
}

resource "google_firebaserules_release" "firestore" {
  project      = var.project_id
  name         = var.database_id == "(default)" ? "cloud.firestore" : "cloud.firestore/${var.database_id}"
  ruleset_name = google_firebaserules_ruleset.firestore.name
}
