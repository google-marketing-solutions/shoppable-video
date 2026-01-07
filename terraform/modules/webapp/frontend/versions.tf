# ------------------------------------------------------------------------------
# VERSION CONFIGURATION
# ------------------------------------------------------------------------------
# Locks the versions of Terraform and Providers to ensure consistent behavior
# across different environments.
# ------------------------------------------------------------------------------

terraform {
  required_version = ">= 1.14.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.13.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.7.2"
    }
  }
}
