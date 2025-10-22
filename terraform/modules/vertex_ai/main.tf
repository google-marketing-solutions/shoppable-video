# modules/vertex_ai/main.tf

resource "google_vertex_ai_index" "default" {
  project             = var.project_id
  region              = var.location
  display_name        = var.index_display_name
  description         = "Vector search index for product embeddings"
  index_update_method = "STREAM_UPDATE"

  metadata {
    config {
      dimensions                = var.embedding_dimensions
      approximate_neighbors_count = 150
      distance_measure_type     = "DOT_PRODUCT_DISTANCE"
      shard_size = "SHARD_SIZE_SMALL"

      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count = 1000
          leaf_nodes_to_search_percent = 7
        }
      }
    }
  }
}

resource "google_vertex_ai_index_endpoint" "default" {
  display_name            = "shoppable-video-endpoint"
  description             = "Endpoint for vector search index"
  region                  = var.location
  public_endpoint_enabled = false
}

resource "google_vertex_ai_index_endpoint_deployed_index" "default" {
  index_endpoint    = google_vertex_ai_index_endpoint.default.id
  index             = google_vertex_ai_index.default.id
  deployed_index_id = "products"
  region = var.location
  dedicated_resources {
    machine_spec {
      machine_type = "e2-standard-2"
    }
    min_replica_count = 1
    max_replica_count = 2
  }
}
