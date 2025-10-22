# modules/vertex_ai/output.tf

output "index_resource_name" {
  description = "The resource name of the Vertex AI Index."
  value       = google_vertex_ai_index.default.id
}

output "index_endpoint_resource_name" {
  description = "The resource name of the Vertex AI Index Endpoint."
  value       = google_vertex_ai_index_endpoint.default.id
}
