# ------------------------------------------------------------------------------
# MODULE VARIABLES
# ------------------------------------------------------------------------------
# Defines the inputs required to provision the static asset storage.
# ------------------------------------------------------------------------------

variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
}

variable "region" {
  description = "The region where the storage bucket will be created."
  type        = string
}

variable "app_name" {
  description = "The application name prefix used for resource naming."
  type        = string
}

variable "labels" {
  description = "Labels to apply to the storage bucket."
  type        = map(string)
  default     = {}
}

variable "cors_config" {
  description = "CORS configuration for the bucket. Set origins to specific domains for production security."
  type = object({
    enable  = bool
    origins = list(string)
  })
  default = {
    enable  = false # Default to OFF (Secure/Same-Origin).
    origins = ["*"]
  }
}

variable "frontend_source_dir" {
  description = "The relative path to the Angular frontend source code (e.g., '../frontend')."
  type        = string
}

variable "frontend_project_name" {
  description = "The name of the Angular project (used to find the 'dist/' folder)."
  type        = string
}
