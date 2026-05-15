# Project Setup Module

This Terraform module provisions the foundational Google Cloud infrastructure and IAM configuration required for the Shoppable Video solution. It establishes the core environment, including service enablement, identity management, artifact storage, and secure credentials management.

## Architecture Overview

The module provisions the following core resources:
*   **Google Cloud APIs**: Enables all required service APIs (Vertex AI, BigQuery, Cloud Run, Cloud Functions, Cloud Tasks, Cloud Scheduler, Secret Manager, Artifact Registry, Firestore, etc.).
*   **Service Account & IAM**: Creates a dedicated service account (`shoppable-video-sa`) and assigns minimal required IAM roles for executing pipeline jobs, cloud functions, and web applications.
*   **Artifact Registry**: Creates a Docker repository (`shoppable-video`) to store container images for pipeline jobs and backend services.
*   **Gemini API Key & Secrets Management**: Generates a restricted Generative Language API key, creates Secret Manager secrets for application credentials (e.g., Google Ads developer token, OAuth credentials), and securely initializes secret versions using local templates.

## Prerequisites

To apply this module, the executing user or service account must have the following roles on the target Google Cloud Project:
*   `roles/owner` or `roles/resourcemanager.projectIamAdmin` (for IAM role bindings)
*   `roles/serviceusage.serviceUsageAdmin` (for enabling APIs)
*   `roles/secretmanager.admin` (for creating secrets)
*   `roles/artifactregistry.admin` (for creating repositories)

## Usage Example

```hcl
module "project_setup" {
  source                 = "./modules/project_setup"
  project_id             = "my-gcp-project-id"
  project_number         = "123456789012"
  location               = "us-central1"
  service_account_id     = "shoppable-video-sa"
  repository_id          = "shoppable-video"
  app_name               = "shoppable-video"
  deploy_webapp          = true
  google_ads_customer_id = "123-456-7890"
}
```

## Inputs

| Name | Type | Description | Default | Required |
| :--- | :--- | :--- | :--- | :--- |
| `project_id` | `string` | The Google Cloud Project ID. | n/a | Yes |
| `project_number` | `string` | The Google Cloud Project Number. | n/a | Yes |
| `location` | `string` | The Google Cloud region/location for deploying resources. | n/a | Yes |
| `service_account_id` | `string` | The ID of the service account to create. | n/a | Yes |
| `repository_id` | `string` | The ID of the Artifact Registry repository. | n/a | Yes |
| `app_name` | `string` | The application name prefix used for secret and resource naming. | n/a | Yes |
| `deploy_webapp` | `bool` | Whether to deploy optional web application secrets (OAuth, session keys). | `false` | No |
| `google_ads_customer_id` | `string` | The Google Ads Customer ID (determines if developer token secret is required). | `null` | No |
| `labels` | `map(string)` | A map of key/value label pairs to assign to resources. | `{}` | No |
| `secrets_config` | `object(...)` | Configuration object specifying secret file mappings and directory locations. | `{...}` | No |

## Outputs

| Name | Description |
| :--- | :--- |
| `service_account_email` | The email address of the created service account. |
| `api_key_secret_id` | The Secret Manager ID storing the Gemini API key. |
| `repository_id` | The ID of the Artifact Registry repository. |
| `secret_ids` | A map of secret objects (ID and version) compatible with backend and pipeline modules. |
