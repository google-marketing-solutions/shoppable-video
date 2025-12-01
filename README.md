# **Shoppable Video Accelerator**

## **Overview**

Maximize the impact of your [Demand Gen campaigns with Product
Feeds](https://support.google.com/google-ads/answer/13721750?hl=en) by using
Gemini's multimodal functionality to intelligently map products to your video
creative.

This tool automates the discovery of relevant merchandise within video content
to ensure accurate and engaging ad placements.

## **Features**

* **Gemini API Integration:** Utilizes Gemini's multimodal functionality to
    identify products within video creatives.
* **Google Merchant Center Integration:** Retrieves product data directly from
    Google Merchant Center via the [Merchant Center BigQuery
    Transfer](https://cloud.google.com/bigquery/docs/merchant-center-transfer).
* **Google Ads Integration:** Retrieves YouTube videos linked to your existing
    Google Ads Campaigns.
* **Cloud-Based Architecture:** Employs Google Cloud services, including Cloud
    Tasks, to ensure scalability, reliability, and efficient processing.
* **BigQuery Data Storage:** Stores both product data and identified video
    products in BigQuery, providing a centralized repository for analysis.
* **Structured Output:** Enforces structured output to constrain Gemini's
    generative results, ensuring data consistency and simplifying downstream
    processing.

## Solution Design

![A diagram describing the solution design](assets/solution_architecture.png)

### Product Embeddings

To discover the most relevant products and enable intelligent matching, this
solution leverages **embeddings and vector search**.

**What are Embeddings?** Embeddings are numerical representations of information
(like text descriptions or product attributes) that capture their semantic
meaning. Think of it like assigning a unique "digital fingerprint" to each
product based on its characteristics. Products that are similar in meaning or
content will have fingerprints that are numerically close to each other. In this
solution, details like a product's title, description, and other attributes are
converted into these numerical vectors using a Gemini embedding model.

**How does Vector Search work?** [Vector
Search](https://cloud.google.com/vertex-ai/docs/matching-engine/overview)
(sometimes called Approximate Nearest Neighbor or ANN) is a technique that
efficiently finds the "closest" or most similar embeddings to a given query
embedding. By storing all your product embeddings in a searchable database (like
BigQuery), the system can quickly and intelligently identify which products from
your Merchant Center catalog are the best matches for products detected within
video content.

1. On a scheduled basis (daily by default), the **Queue Products** Cloud Run
    job:
    1. Queries BigQuery to identify the set of products from Merchant Center
        that do not yet have an embedding.
    2. Pushes new products to the **`product-embeddings-queue`** in Cloud
        Tasks.
2. Cloud Tasks orchestrates a call to the **Generate Embedding** Cloud Function
    for each product.
3. The **Generate Embedding** function:
    1. Gets the text to embed based on the product's title, description, and
        other attributes.
    2. Makes an HTTP request to Gemini's `embedContent` endpoint which returns
        an embedding vector.
    3. Writes the embedding to the `product_embeddings` table in BigQuery.

Here is an example of the text used to generate an embedding for a product from
Merchant Center:

```text
Title: Google Pixel 10
Brand: Google
Product Category: Electronics > Communications > Telephony > Mobile Phones
Product Type: Mobile Phones
Color: Obsidian
Description: The Google Pixel 10 is the latest smartphone from Google, featuring a powerful new processor, a stunning display, and an advanced camera system.
```

### Video Inventory Analysis

1. On a scheduled basis (every 6 hours by default), the **Queue Videos** Cloud
    Run job:
    1. Executes queries to retrieve the set of unprocessed videos from:
        1. Google Ads (via Google Ads BigQuery Data Transfer)
        2. From a user-provided Google Sheet which can contain either Youtube
            Video IDs (e.g.
            [`dQw4w9WgXcQ`](https://www.youtube.com/watch?v=dQw4w9WgXcQ)) or
            Cloud Storage URIs (e.g. `gs://bucket_name/dir/file`)
    2. Filters out any videos that have already been processed by checking
        against the `video_analysis` table in BigQuery.
    3. Pushes new videos to the **`video-analysis-queue`** in Cloud Tasks.
2. Cloud Tasks orchestrates a call to the **Analyze Video** Cloud Function for
    each video.
3. The **Analyze Video** function:
    1. Temporarily uploads the video file (for GCS URIs) to the Gemini File API
        or uses the URL directly for Youtube videos.
    2. Makes an API call to Gemini's multimodal model to identify the relevant
        products and details in the video.
    3. Generates an embedding for each identified product.
    4. Writes the set of identified products to the `video_analysis` table in
        BigQuery.

Here is an example of the text used to generate an embedding for a product
identified in a video:

```text
Title: Black-colored Smartphone with Advanced Camera
Description: A sleek, black-colored smartphone with a large edge-to-edge display and a prominent module on the rear housing multiple camera lenses.
Color, Pattern, Style, Usage: Matte black finish, minimalist style, used for capturing high-quality photographs.
Category: Electronics
Subcategory: Mobile Phones
```

### Product / Video Mapping

A BigQuery table (`matched_products`) is materialized by a scheduled query to
join the embeddings of products identified in videos with the most similar
products from Merchant Center.

1. A scheduled query runs periodically (every 24 hours by default) to find
    newly identified products from video analysis that have not yet been mapped.
2. For each identified product, the query uses the `VECTOR_SEARCH` function in
    BigQuery to find the most similar products from the `product_embeddings`
    table.
3. The `VECTOR_SEARCH` function calculates the distance between the embedding
    of the identified product and the embeddings of all the products in Merchant
    Center.
4. The `top_k` (configurable, default is 10) products with the smallest
    distance (i.e., the most similar products) are stored in the
    `matched_products` table for each identified product.

## **Installation**

This section outlines the steps to install and configure Shoppable Video
Accelerator.

### **Requirements**

To use Shoppable Video Accelerator, you'll need the following:

* A [Google Cloud project](https://console.cloud.google.com) with billing
    enabled.
* [Terraform](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/install-cli),
    installed on your local machine or Cloud Shell.
* [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install),
    installed and [configured](https://cloud.google.com/sdk/docs/initializing).
* Access to a [Google Merchant
    Center](https://business.google.com/us/merchant-center/) account,
    specifically for setting up the [Merchant Center Transfer in
    BigQuery](https://cloud.google.com/bigquery/docs/merchant-center-transfer).
* \[Optional\] Access to a Google Ads account, specifically for setting up the
    [Google Ads Data Transfer in
    BigQuery](https://docs.cloud.google.com/bigquery/docs/google-ads-transfer)

Shoppable Video Accelerator uses
[Terraform](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/infrastructure-as-code)
to automate the deployment of resources on Google Cloud Platform, streamlining
the setup process.

#### **Google Cloud Platform Services and APIs**

> \[\!IMPORTANT\] Terraform will automatically enable most of these APIs during
> the installation.

* **Core Services:**
  * [IAM (Identity and Access
        Management)](https://cloud.google.com/iam/docs/overview)
        (iam.googleapis.com)
  * [API Keys](https://cloud.google.com/docs/authentication/api-keys)
        (apikeys.googleapis.com)
* **Development and Deployment:**
  * [Cloud Build API](https://cloud.google.com/cloud-build/docs/overview)
        (cloudbuild.googleapis.com)
  * [Artifact Registry
        API](https://cloud.google.com/artifact-registry/docs/overview)
        (artifactregistry.googleapis.com)
* **Serverless Compute and Task Management:**
  * [Cloud Functions API](https://cloud.google.com/functions/docs/overview)
        (cloudfunctions.googleapis.com)
  * [Cloud Run API](https://cloud.google.com/run/docs/overview)
        (run.googleapis.com)
  * [Cloud Scheduler API](https://cloud.google.com/scheduler/docs)
        (cloudscheduler.googleapis.com)
  * [Cloud Tasks API](https://cloud.google.com/tasks/docs)
        (cloudtasks.googleapis.com)
* **Data and Analytics:**
  * [BigQuery API](https://cloud.google.com/bigquery/docs)
        (bigquery.googleapis.com)
  * [BigQuery Data Transfer Service
        API](https://cloud.google.com/bigquery/docs/merchant-center-transfer)
        (bigquerydatatransfer.googleapis.com)
  * [Google Sheets API](https://developers.google.com/sheets/api/overview)
        (sheets.googleapis.com)
  * [Cloud Storage API](https://cloud.google.com/storage)
        (storage.googleapis.com)
  * [YouTube Data API](https://developers.google.com/youtube/v3)
        (youtube.googleapis.com)
* **Artificial Intelligence and Machine Learning:**
  * [Generative Language API](https://ai.google.dev/gemini-api/docs)
        (generativelanguage.googleapis.com)
  * [Vertex AI
        API](https://cloud.google.com/vertex-ai/docs/start/overview-key-concepts)
        (aiplatform.googleapis.com)
* **Security:**
  * [Secret Manager
        API](https://cloud.google.com/security/products/secret-manager)
        (secretmanager.googleapis.com)

#### **Service Account**

The solution will create a service account with the following permissions:

* [roles/bigquery.dataOwner](https://cloud.google.com/bigquery/docs/access-control#bigquery.dataOwner)
* [roles/bigquery.jobUser](https://cloud.google.com/bigquery/docs/access-control#bigquery.jobUser)
* [roles/cloudtasks.enqueuer](https://docs.cloud.google.com/tasks/docs/access-control#cloudtasks.enqueuer)
* [roles/cloudtasks.viewer](https://cloud.google.com/tasks/docs/access-control#cloudtasks.viewer)
* [roles/iam.serviceAccountOpenIdTokenCreator](https://docs.cloud.google.com/iam/docs/roles-permissions/iam#iam.serviceAccountOpenIdTokenCreator)
* [roles/iam.serviceAccountUser](https://docs.cloud.google.com/iam/docs/roles-permissions/iam#iam.serviceAccountUser)
* [roles/logging.logWriter](https://cloud.google.com/logging/docs/access-control#logging.logWriter)
* [roles/run.invoker](https://docs.cloud.google.com/run/docs/reference/iam/roles#run.invoker)
* [roles/secretmanager.viewer](https://cloud.google.com/secret-manager/docs/access-control#secretmanager.viewer)
* [roles/storage.objectViewer](https://cloud.google.com/storage/docs/access-control/iam-roles#storage.objectViewer)
* [roles/aiplatform.user](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)

### **Installation Steps**

Follow these steps to install and deploy Shoppable Video Accelerator:

#### **1. Clone the Repository**

Clone the repository using Cloud Shell or your local machine.

```bash
git clone https://github.com/google-marketing-solutions/shoppable-video.git
```

#### **2. Build Cloud Build Artifacts**

Before deploying the Terraform configuration, you need to build the container
images for the Cloud Run jobs. Navigate to the root of the repository and run
the following command:

```bash
 gcloud builds submit --region=${LOCATION} --config cloudbuild.yaml
```

This command uses the `cloudbuild.yaml` file to build and push the container
images to Artifact Registry.

#### **3. Enable APIs & Access in your Google Cloud Project**

Before deploying, ensure the following APIs are enabled in your Google Cloud
project:

* [Cloud Resource Manager
    API](https://console.cloud.google.com/apis/library/cloudresourcemanager.googleapis.com)
    (cloudresourcemanager.googleapis.com)
* [Service Usage
    API](https://console.cloud.google.com/apis/library/serviceusage.googleapis.com)
    (serviceusage.googleapis.com)

All other APIs will be enabled automatically by Terraform.

If you are running Terraform as a human user, ensure that you have the
appropriate BigQuery role (either bigquery.dataOwner or bigquery.dataEditor). If
you can't apply this role with project-level access, then complete the
instructions until the solution dataset is created (and TF fails), then grant
dataset-level access manually and rerun Terraform.

#### **4. Provide Values for Variables**

Create a variables.tfvars file in the terraform/ directory and provide the
following values ([click here for
details](https://developer.hashicorp.com/terraform/language/values/variables#variable-definitions-tfvars-files)).

| variable                              | description                                                                                                                                                                                                          | required | default                      |
| :------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------- | :--------------------------- |
| project\_id                           | Google Cloud Project ID                                                                                                                                                                                              | required |                              |
| service\_account                      | Name of the service account to create. This account will be used to run and manage the solution. ({service\_account}@{project\_id}.iam.gserviceaccount.com)                                                          | required |                              |
| merchant\_id                          | Merchant ID or Merchant Aggregator ID (MCA) to use. To find your Merchant Center identifier, log into Merchant Center and look for the number at the top-right corner of the page, above your account email address. | required |                              |
| ads\_customer\_id                     | Google Ads Customer ID for retrieving YouTube videos linked to existing Google Ads Campaigns.                                                                                                                        | optional | `null`                       |
| spreadsheet\_id                       | Google Sheet ID containing YouTube Video IDs or Google Cloud Storage URIs for video analysis.                                                                                                                        | optional | `null`                       |
| bigquery\_dataset\_id                 | Name of the dataset to create in BigQuery where Merchant Center transfer table(s) and output will be stored.                                                                                                         | optional | `shoppable_video`            |
| location                              | [Google Cloud region](https://cloud.withgoogle.com/region-picker) to use.                                                                                                                                            | optional | `us-central1`                |
| product\_limit                        | Number of products to process per batch.                                                                                                                                                                             | optional | `1000`                       |
| video\_limit                          | Number of videos to process per batch.                                                                                                                                                                               | optional | `10`                         |
| gcs\_embeddings\_bucket\_name         | The name of the GCS bucket to store embeddings.                                                                                                                                                                      | optional | `shoppable-video-embeddings` |
| gcs\_bucket\_ttl\_days                | The number of days after which to delete objects in the bucket.                                                                                                                                                      | optional | `90`                         |
| vector\_search\_embedding\_dimensions | The number of dimensions for the product embedding vectors.                                                                                                                                                          | optional | `1536`                       |
| repository\_id                        | The ID of the repository in Artifact Registry.                                                                                                                                                                       | optional | `shoppable-video`            |
| generative\_model\_name               | [Gemini model variant](https://ai.google.dev/gemini-api/docs/models#model-variations) to use for video analysis.                                                                                                     | optional | `gemini-2.5-flash`           |
| embedding\_model\_name                | The embedding model to use for generating product embeddings.                                                                                                                                                        | optional | `gemini-embedding-001`       |
| refresh\_window\_days                 | The number of days to look back for new products and videos to process.                                                                                                                                              | optional | `7`                          |
| number\_of\_matched\_products         | The number of top matching products to retrieve for each video.                                                                                                                                                      | optional | `10`                         |

**Example terraform/variables.tfvars file:**

```text
project_id = "your-gcp-project-id"
service_account = "shoppable-video-sa"
merchant_id = "123456789"
ads_customer_id = "1234567890"
spreadsheet_id = "your-spreadsheet-id"
bigquery_dataset_id = "my_shoppable_video_dataset"
location = "us-central1"
product_limit = 500
video_limit = 20
gcs_embeddings_bucket_name = "my-shoppable-video-embeddings"
gcs_bucket_ttl_days = 120
vector_search_embedding_dimensions = 1536
repository_id = "my-shoppable-video-repo"
generative_model_name = "gemini-2.5-flash"
embedding_model_name = "gemini-embedding-001"
refresh_window_days = "14"
number_of_matched_products = 5
```

#### **5. Deploy Shoppable Video Accelerator**

To deploy Shoppable Video Accelerator using Terraform, run the following
commands:

> \[\!WARNING\] If you are running Terraform using Cloud Shell, you may need to
> update Terraform to at least v1.11
>
> Follow the
> [instructions](https://developer.hashicorp.com/terraform/install#linux) (or
> run this command from the docs below in your terminal.)
>
> ```bash
> wget -O - <https://apt.releases.hashicorp.com/gpg> | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
> echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
> sudo apt update && sudo apt install terraform
> ```

First, initialize the Terraform configuration:

`terraform init`

Then, apply the Terraform configuration. This will display the changes to be
applied and prompt you for confirmation:

`terraform apply -var-file=variables.tfvars`

Type yes and press Enter to confirm the deployment.

> \[\!IMPORTANT\] Terraform will try to set up the Merchant Center Transfer
> using the credentials of the newly created service account. In order to get
> the transfer to succeed, you will need to either
>
> * [Grant the service
>     account](https://support.google.com/merchants/answer/12160472) with
>     "Performance and insights" access in Merchant Center.
> * Replace the service account with your human user who has access to
>     Merchant Center.
>   * Go to BigQuery \> Data Transfers \> merchant\_center\_transfer \>
>         Configuration
>   * Click "Update Credentials"
>
> If this is your first time using the Merchant Center Transfer, your `terraform
> apply` might fail with a "table not found" error. It can take up to 24 hours
> for the Merchant Center transfer table to become available. Once the transfer
> succeeds and the table exists in BigQuery, run the apply command again.

Lastly, you will need to enable the two newly-created Cloud Scheduler jobs.

Terraform sets the jobs to PAUSED to prevent the solution from running
inadvertently.

To enable the jobs:

1. Navigate to **Cloud Scheduler** in the Google Cloud Console.
2. Find the jobs named `scheduled-queue-products` and `scheduled-queue-videos`.
3. For each job, click the toggle in the "State" column to change it from
    "Paused" to "Enabled".

You can also force a manual run of the job to check if everything is working as
expected; look at Cloud Logging or the output BQ table. To force a manual run:

1. In the Cloud Scheduler page, click on the job you want to run
    (`queue-products-job` or `scheduled-queue-videos`).
2. Click the **"Force run"** button at the top of the page.

Alternatively, you can use the `gcloud` CLI:

To enable a job:

```bash
gcloud scheduler jobs enable scheduled-queue-products --project=[YOUR_PROJECT_ID]
gcloud scheduler jobs enable scheduled-queue-videos --project=[YOUR_PROJECT_ID]
```

To force a manual run:

```bash
gcloud scheduler jobs run scheduled-queue-products --project=[YOUR_PROJECT_ID]
gcloud scheduler jobs run scheduled-queue-videos --project=[YOUR_PROJECT_ID]
```

## **Destroy Deployed Resources**

To remove all Shoppable Video Accelerator resources from your Google Cloud
project, run the following command from the terraform/ directory:

`terraform destroy -var-file=variables.tfvars`

Type yes and press Enter to confirm the deletion of all deployed resources.

## **Contributing**

See the [contributing guidelines](contributing.md) for details on how to
contribute to this project.

## **License**

This project is licensed under the Apache 2.0 License.

## **Disclaimer**

This is not an officially supported Google product. This project is not eligible
for the [Google Open Source Software Vulnerability Rewards
Program](https://bughunters.google.com/open-source-security).
