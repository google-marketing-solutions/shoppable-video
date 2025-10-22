# modules/storage/variables.tf

variable "project_id" {
  description = "The ID of the project in which to provision resources."
  type        = string
}

variable "bucket_location" {
  description = "The location of the GCS bucket."
  type        = string
}

variable "bucket_name" {
  description = "The name of the GCS bucket to create."
  type        = string
}

variable "service_account_email" {
  description = "The email of the service account to grant access to the bucket."
  type        = string
}

variable "bucket_ttl_days" {
  description = "The number of days after which to delete objects in the bucket."
  type        = number
}
