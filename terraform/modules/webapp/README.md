# Web Application Module

This Terraform module provisions the complete, enterprise-grade web application and API backend for the Shoppable Video solution. It establishes a secure, scalable environment for marketing teams to review AI-generated product matches, curate video feeds, and synchronize ad insertions directly with Google Ads.

## Architecture Overview

The module orchestrates several specialized submodules to deliver a robust three-tier architecture:
*   **Security & Identity (`./security`)**: Creates dedicated service accounts for the backend API and ad insertion jobs, enforcing least-privilege access to Secret Manager and BigQuery.
*   **Networking (`./networking`)**: Establishes a secure VPC network, Serverless VPC Access connector, and Cloud NAT to provide static, secure outbound IP addresses for Google Ads API communication.
*   **Database (`./firestore`)**: Provisions a native Firestore database and composite indexes to manage user sessions, video curation workflows, and ad deployment logs.
*   **Frontend (`./frontend`)**: Configures a Google Cloud Storage bucket for secure static website hosting and automates the compilation and synchronization of the Angular SPA.
*   **Backend API (`./backend`)**: Deploys the Python REST API as a Cloud Run v2 Service, protected by Identity-Aware Proxy (IAP) to ensure only authorized enterprise users can access the system.
*   **Load Balancing & WAF (`./lb`)**: Provisions a global External HTTPS Load Balancer with managed SSL certificates, Cloud CDN, and Cloud Armor WAF policies to route traffic seamlessly between the frontend bucket and backend API.
*   **Ad Insertion Job (`jobs.tf`)**: Deploys a dedicated Cloud Run Job (`shoppable-video-ads-insertion-job`) to execute curated ad group updates against Google Ads APIs.

## Prerequisites

To apply this module, the executing user or service account must have the following roles on the target Google Cloud Project:
*   `roles/compute.admin` (for VPC networks, load balancers, Cloud Armor, Cloud NAT)
*   `roles/run.admin` (for Cloud Run services and jobs)
*   `roles/storage.admin` (for frontend static hosting buckets)
*   `roles/datastore.owner` (for Firestore databases and indexes)
*   `roles/dns.admin` (for Cloud DNS zones and records)
*   `roles/iam.securityAdmin` (for IAP and IAM bindings)
*   `roles/vpcaccess.admin` (for Serverless VPC Access connectors)

## Usage Example

```hcl
module "webapp" {
  source                 = "./modules/webapp"
  project_id             = "my-gcp-project-id"
  project_number         = "123456789012"
  location               = "us-central1"
  app_name               = "shoppable-video"
  secret_ids             = module.project_setup.secret_ids
  backend_image          = "us-central1-docker.pkg.dev/my-gcp-project-id/shoppable-video/webapp-backend:latest"
  cloud_run_job_image    = "us-central1-docker.pkg.dev/my-gcp-project-id/shoppable-video/webapp-push-to-ads:latest"
  data_sync_image        = "us-central1-docker.pkg.dev/my-gcp-project-id/shoppable-video/data-sync:latest"
  merchant_id            = "123456789"
  service_account_email  = "shoppable-video-sa@my-gcp-project-id.iam.gserviceaccount.com"
  bigquery_dataset_id    = "shoppable_video"
  google_ads_customer_id = "123-456-7890"
  firestore_database_id  = "(default)"
  networking_config = {
    subnet_cidr = "10.1.0.0/24"
  }
  iap_config = {
    enable_iap     = true
    access_members = ["domain:google.com"]
  }
}
```

## Inputs

| Name | Type | Description | Default | Required |
| :--- | :--- | :--- | :--- | :--- |
| `project_id` | `string` | The Google Cloud Project ID. | n/a | Yes |
| `project_number` | `string` | The Google Cloud Project Number. | n/a | Yes |
| `location` | `string` | The Google Cloud region/location for deploying resources. | n/a | Yes |
| `app_name` | `string` | The application name prefix used for resource naming. | n/a | Yes |
| `secret_ids` | `map(object)` | Map of secret objects (ID and version) for backend injection. | n/a | Yes |
| `merchant_id` | `string` | The Google Merchant Center Account ID. | n/a | Yes |
| `service_account_email` | `string` | The primary service account email address. | n/a | Yes |
| `bigquery_dataset_id` | `string` | The BigQuery dataset ID for analytics queries. | n/a | Yes |
| `backend_image` | `string` | The fully qualified Docker image URI for the Cloud Run backend API. | `null` | No |
| `cloud_run_job_image` | `string` | The fully qualified Docker image URI for the ad insertion job. | `null` | No |
| `data_sync_image` | `string` | The fully qualified Docker image URI for the data synchronization utility. | `null` | No |
| `google_ads_customer_id` | `string` | The Google Ads Customer ID. | `null` | No |
| `firestore_database_id` | `string` | The ID of the Firestore database. Use `(default)` for the default database. | `"(default)"` | No |
| `networking_config` | `object(...)` | Custom networking configuration (e.g., subnet CIDR ranges). | `{...}` | No |
| `iap_config` | `object(...)` | Identity-Aware Proxy (IAP) configuration object. | `{...}` | No |
| `labels` | `map(string)` | A map of key/value label pairs to assign to resources. | `{}` | No |

## Outputs

| Name | Description |
| :--- | :--- |
| `load_balancer_ip` | The global static IP address reserved for the External HTTPS Load Balancer. |
| `frontend_bucket_url` | The Google Cloud Storage URI (`gs://...`) for the frontend static hosting bucket. |
| `backend_service_url` | The direct Cloud Run URL of the backend API service (restricted by IAM/IAP). |
