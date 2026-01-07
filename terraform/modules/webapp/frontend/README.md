<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.14.0 |
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 7.13.0 |
| <a name="requirement_random"></a> [random](#requirement\_random) | >= 3.7.2 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_google"></a> [google](#provider\_google) | >= 7.13.0 |
| <a name="provider_null"></a> [null](#provider\_null) | n/a |
| <a name="provider_random"></a> [random](#provider\_random) | >= 3.7.2 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [google_storage_bucket.frontend](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket_iam_member.public_read](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_iam_member) | resource |
| [null_resource.build_and_deploy](https://registry.terraform.io/providers/hashicorp/null/latest/docs/resources/resource) | resource |
| [random_id.bucket_suffix](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/id) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | The application name prefix used for resource naming. | `string` | n/a | yes |
| <a name="input_cors_config"></a> [cors\_config](#input\_cors\_config) | CORS configuration for the bucket. Set origins to specific domains for production security. | <pre>object({<br/>    enable  = bool<br/>    origins = list(string)<br/>  })</pre> | <pre>{<br/>  "enable": false,<br/>  "origins": [<br/>    "*"<br/>  ]<br/>}</pre> | no |
| <a name="input_frontend_project_name"></a> [frontend\_project\_name](#input\_frontend\_project\_name) | The name of the Angular project (used to find the 'dist/' folder). | `string` | n/a | yes |
| <a name="input_frontend_source_dir"></a> [frontend\_source\_dir](#input\_frontend\_source\_dir) | The relative path to the Angular frontend source code (e.g., '../frontend'). | `string` | n/a | yes |
| <a name="input_labels"></a> [labels](#input\_labels) | Labels to apply to the storage bucket. | `map(string)` | `{}` | no |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | The Google Cloud Project ID. | `string` | n/a | yes |
| <a name="input_region"></a> [region](#input\_region) | The region where the storage bucket will be created. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_bucket_name"></a> [bucket\_name](#output\_bucket\_name) | The name of the created GCS bucket. |
<!-- END_TF_DOCS -->