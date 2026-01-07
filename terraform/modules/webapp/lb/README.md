<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.14.0 |
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 7.13.0 |
| <a name="requirement_google-beta"></a> [google-beta](#requirement\_google-beta) | >= 7.13.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_google"></a> [google](#provider\_google) | >= 7.13.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [google_compute_backend_bucket.static_backend](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_backend_bucket) | resource |
| [google_compute_backend_service.api_backend](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_backend_service) | resource |
| [google_compute_global_forwarding_rule.default](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_global_forwarding_rule) | resource |
| [google_compute_global_forwarding_rule.https_redirect](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_global_forwarding_rule) | resource |
| [google_compute_managed_ssl_certificate.default](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_managed_ssl_certificate) | resource |
| [google_compute_region_network_endpoint_group.serverless_neg](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_region_network_endpoint_group) | resource |
| [google_compute_security_policy.edge_sec](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_security_policy) | resource |
| [google_compute_target_http_proxy.https_redirect](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_target_http_proxy) | resource |
| [google_compute_target_https_proxy.default](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_target_https_proxy) | resource |
| [google_compute_url_map.default](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_url_map) | resource |
| [google_compute_url_map.https_redirect](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_url_map) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | The application name prefix. | `string` | n/a | yes |
| <a name="input_armor_settings"></a> [armor\_settings](#input\_armor\_settings) | Configures Cloud Armor Security Policy rules, including managed OWASP rules and custom logic. | <pre>object({<br/>    enable_cloud_armor = bool<br/>    armor_tier         = optional(string)<br/><br/>    # Map of managed rule sets (e.g., SQLi, XSS) with enable flags and sensitivity levels.<br/>    managed_rules = map(object({<br/>      enabled           = bool<br/>      priority          = number<br/>      action            = optional(string)<br/>      sensitivity_level = optional(number)<br/>    }))<br/><br/>    # List of custom user rules for business logic (e.g., Geo-blocking).<br/>    custom_rules = list(object({<br/>      priority    = number<br/>      action      = string<br/>      expression  = string<br/>      description = optional(string)<br/>      rate_limit = optional(object({<br/>        rate_limit_threshold = number<br/>        interval_sec         = number<br/>        conform_action       = string<br/>        exceed_action        = string<br/>      }))<br/>    }))<br/><br/>    # List of IPs to block globally.<br/>    denylist_ips = list(string)<br/>  })</pre> | n/a | yes |
| <a name="input_cloud_run_service_name"></a> [cloud\_run\_service\_name](#input\_cloud\_run\_service\_name) | The name of the Cloud Run service (from backend module). | `string` | n/a | yes |
| <a name="input_frontend_bucket_name"></a> [frontend\_bucket\_name](#input\_frontend\_bucket\_name) | The name of the GCS bucket for static content routing. | `string` | n/a | yes |
| <a name="input_global_ip"></a> [global\_ip](#input\_global\_ip) | The static global IP address reserved for this Load Balancer. | `string` | n/a | yes |
| <a name="input_labels"></a> [labels](#input\_labels) | Labels to apply to load balancer resources. | `map(string)` | `{}` | no |
| <a name="input_lb_settings"></a> [lb\_settings](#input\_lb\_settings) | Configures Load Balancer features including CDN, Domain, and SSL Policy. | <pre>object({<br/>    enable_cdn        = bool<br/>    domain_name       = optional(string)<br/>    ssl_policy        = optional(string)<br/>    use_managed_certs = bool<br/>    custom_cert_names = optional(list(string), [])<br/>  })</pre> | n/a | yes |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | The Google Cloud Project ID. | `string` | n/a | yes |
| <a name="input_region"></a> [region](#input\_region) | The GCP region to be used for deploying load balancing resources. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_load_balancer_ip"></a> [load\_balancer\_ip](#output\_load\_balancer\_ip) | The public IP address of the Load Balancer. |
<!-- END_TF_DOCS -->