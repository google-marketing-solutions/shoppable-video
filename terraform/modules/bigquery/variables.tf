# modules/bigquery/variables.tf

variable "project_id" {
  type = string
}

variable "service_account_email" {
  type = string
}

variable "bigquery_dataset_id" {
  type = string
}

variable "merchant_id" {
  type = string
}

variable "ads_customer_id" {
  type = string
}

variable "refresh_window_days" {
  type = string
}

variable "vector_search_embedding_dimensions" {
  type = string
}

variable "number_of_matched_products" {
  type = number
}
