# Build Module

This Terraform module manages the automated compilation and containerization of the Shoppable Video microservices. It leverages Google Cloud Build to build Docker images from local source code and pushes them to Google Artifact Registry.

## Architecture Overview

The module executes the following build workflows:
*   **Pipeline Images**: Compiles and pushes container images for the core asynchronous pipeline jobs (`queue-products` and `queue-videos`).
*   **Web Application Images (Optional)**: If `deploy_webapp` is enabled, compiles and pushes container images for the API backend (`webapp-backend`), ad insertion job (`webapp-push-to-ads`), and data synchronization utility (`data-sync`).
*   **Immutable Image Tracking**: Captures exact sha256 image digests to export fully qualified, immutable container URIs to downstream Terraform modules (ensuring Cloud Run and Cloud Jobs deploy the exact built artifacts).

## Prerequisites

To apply this module, the executing user or service account must have the following roles on the target Google Cloud Project:
*   `roles/cloudbuild.builds.editor` (to submit Cloud Build jobs)
*   `roles/artifactregistry.writer` (to push images to the repository)
*   `roles/storage.objectViewer` (to read source archives if staging via GCS)

## Usage Example

```hcl
module "build" {
  source        = "./modules/build"
  project_id    = "my-gcp-project-id"
  location      = "us-central1"
  repository_id = "shoppable-video"
  deploy_webapp = true
}
```

## Inputs

| Name | Type | Description | Default | Required |
| :--- | :--- | :--- | :--- | :--- |
| `project_id` | `string` | The Google Cloud Project ID. | n/a | Yes |
| `location` | `string` | The Google Cloud region/location for Artifact Registry. | n/a | Yes |
| `repository_id` | `string` | The ID of the Artifact Registry repository where images will be pushed. | n/a | Yes |
| `deploy_webapp` | `bool` | Whether to build container images for the optional web application backend. | `true` | No |

## Outputs

| Name | Description |
| :--- | :--- |
| `image_uris` | A map of image names to their fully qualified, immutable container URIs (including sha256 digests). |
