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

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [google_cloud_run_service_iam_member.invoker](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_service_iam_member) | resource |
| [google_cloud_run_v2_service.default](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | The application name prefix. | `string` | n/a | yes |
| <a name="input_container_override"></a> [container\_override](#input\_container\_override) | Override Docker ENTRYPOINT (command) and CMD (args). Set to null to use Dockerfile defaults. | <pre>object({<br/>    command = optional(list(string)) # Default null.<br/>    args    = optional(list(string)) # Default null.<br/>  })</pre> | <pre>{<br/>  "args": null,<br/>  "command": null<br/>}</pre> | no |
| <a name="input_docker_image"></a> [docker\_image](#input\_docker\_image) | The container image URI (e.g., gcr.io/proj/img:tag). | `string` | n/a | yes |
| <a name="input_frontend_url"></a> [frontend\_url](#input\_frontend\_url) | The full URL of the frontend (e.g., 'https://34.1.2.3'). | `string` | n/a | yes |
| <a name="input_ingress_style"></a> [ingress\_style](#input\_ingress\_style) | Traffic restrictions: 'INGRESS\_TRAFFIC\_ALL' (Public) or 'INGRESS\_TRAFFIC\_INTERNAL\_LOAD\_BALANCER' (Private). | `string` | `"INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"` | no |
| <a name="input_labels"></a> [labels](#input\_labels) | Labels to apply to the Cloud Run service. | `map(string)` | `{}` | no |
| <a name="input_lb_domain"></a> [lb\_domain](#input\_lb\_domain) | The domain or IP of the Load Balancer (e.g., '34.1.2.3' or 'example.com'). | `string` | n/a | yes |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | The Google Cloud Project ID. | `string` | n/a | yes |
| <a name="input_region"></a> [region](#input\_region) | The region where Cloud Run will be deployed. | `string` | n/a | yes |
| <a name="input_resource_limits"></a> [resource\_limits](#input\_resource\_limits) | Compute resources allocated to the container. | <pre>object({<br/>    cpu    = string<br/>    memory = string<br/>  })</pre> | <pre>{<br/>  "cpu": "2000m",<br/>  "memory": "1024Mi"<br/>}</pre> | no |
| <a name="input_scaling_config"></a> [scaling\_config](#input\_scaling\_config) | Configures the auto-scaling behavior for Cloud Run. | <pre>object({<br/>    max_instance_count = number<br/>    min_instance_count = number<br/>  })</pre> | <pre>{<br/>  "max_instance_count": 5,<br/>  "min_instance_count": 2<br/>}</pre> | no |
| <a name="input_secret_ids"></a> [secret\_ids](#input\_secret\_ids) | Map of environment variables to secret configurations. Key is the Env\_Var\_name. | <pre>map(object({<br/>    secret_id = string                     # The resource ID of the secret.<br/>    version   = optional(string, "latest") # Defaults to 'latest' if not provided.<br/>  }))</pre> | n/a | yes |
| <a name="input_service_account_email"></a> [service\_account\_email](#input\_service\_account\_email) | The email of the GCP Service Account to attach to Cloud Run. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_service_name"></a> [service\_name](#output\_service\_name) | The name of the created Cloud Run service. |
| <a name="output_service_url"></a> [service\_url](#output\_service\_url) | The direct URL of the Cloud Run service. |
<!-- END_TF_DOCS -->