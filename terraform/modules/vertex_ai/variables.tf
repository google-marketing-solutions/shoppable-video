# modules/vertex_ai/variables.tf

variable "project_id" {
  description = "The project ID to deploy to."
  type        = string
}

variable "location" {
  description = "The location to deploy to."
  type        = string
}

variable "index_display_name" {
  description = "The display name of the Vertex AI Index."
  type        = string
}

variable "embedding_dimensions" {
  description = "The number of dimensions of the embeddings."
  type        = number
}
