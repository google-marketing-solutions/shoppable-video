# modules/jobs/variables.tf

variable "job_name" {
  description = "The name of the Cloud Run job."
  type        = string
}

variable "location" {
  description = "The location of the Cloud Run job."
  type        = string
}

variable "service_account_email" {
  description = "The email of the service account to use for the job."
  type        = string
}

variable "image" {
  description = "The container image to use for the job."
  type        = string
}

variable "args" {
  description = "The arguments to pass to the container."
  type        = list(string)
  default     = []
}

variable "project_id" {
  description = "The ID of the project."
  type        = string
}

variable "environment_variables" {
  description = "The environment variables to pass to the container."
  type        = map(string)
  default     = {}
}

variable "timeout" {
  description = "The timeout for the Cloud Run job in seconds."
  type        = string
  default     = "600s"
}

variable "retries" {
  description = "The number of retries for the Cloud Run job."
  type        = number
  default     = 0
}
