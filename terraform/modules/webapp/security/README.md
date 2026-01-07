<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.14.0 |
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 7.13.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_google"></a> [google](#provider\_google) | >= 7.13.0 |
| <a name="provider_null"></a> [null](#provider\_null) | n/a |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [google_secret_manager_secret.app_secrets](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret_iam_member.secret_access](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_iam_member) | resource |
| [google_service_account.backend_sa](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/service_account) | resource |
| [null_resource.secret_version_manager](https://registry.terraform.io/providers/hashicorp/null/latest/docs/resources/resource) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | The application name prefix used for resource naming. | `string` | n/a | yes |
| <a name="input_labels"></a> [labels](#input\_labels) | Labels to apply to the security resources. | `map(string)` | `{}` | no |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | The Google Cloud Project ID. | `string` | n/a | yes |
| <a name="input_secret_map"></a> [secret\_map](#input\_secret\_map) | Key = Env\_Var\_Name, Value = Filename\_In\_secrets\_dir | `map(string)` | <pre>{<br/>  "GOOGLE_ADS_DEVELOPER_TOKEN": "developer_token.txt",<br/>  "GOOGLE_CLIENT_ID": "google_client_id.txt",<br/>  "GOOGLE_CLIENT_SECRET": "google_client_secret.txt",<br/>  "SESSION_SECRET_KEYS": "session_keys.txt"<br/>}</pre> | no |
| <a name="input_secrets_dir"></a> [secrets\_dir](#input\_secrets\_dir) | Path to the local directory containing secret files. Must not be committed to Git. | `string` | `"./config/secrets"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_secret_ids"></a> [secret\_ids](#output\_secret\_ids) | Returns a map of secret objects compatible with the backend module. |
| <a name="output_service_account_email"></a> [service\_account\_email](#output\_service\_account\_email) | n/a |
<!-- END_TF_DOCS -->