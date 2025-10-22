# modules/cloudscheduler/variables.tf

variable "name" {
  type = string
}

variable "project_id" {
  type = string
}

variable "location" {
  type = string
}

variable "function_url" {
  description = "The URL of the function to invoke."
  type        = string
  default     = null
}

variable "job_name" {
  description = "The name of the job to invoke."
  type        = string
  default     = null
}

variable "body" {
  type    = string
  default = null
}

variable "service_account_email" {
  type = string
}

variable "schedule" {
  type    = string
  default = "0 * * * *"
}
