# variables.tf

variable "project_id" {
  type = string
}

variable "service_account" {
  type = string
}

variable "merchant_id" {
  type = string
}

variable "bigquery_dataset_id" {
  type    = string
  default = "shoppable_video"
}

variable "location" {
  type    = string
  default = "us-central1"
}

variable "product_limit" {
  type    = number
  default = 100
}

variable "gcs_embeddings_bucket_name" {
  type        = string
  description = "The name of the GCS bucket to store embeddings."
  default     = "shoppable-video-embeddings"
}

variable "gcs_bucket_ttl_days" {
  description = "The number of days after which to delete objects in the bucket."
  type        = number
  default     = 90
}

variable "vector_search_index_id" {
  type    = string
  default = "shoppable-video-index"
}

variable "vector_search_embedding_dimensions" {
  type    = number
  default = 256
}

variable "repository_id" {
  type    = string
  default = "shoppable-video"
}

