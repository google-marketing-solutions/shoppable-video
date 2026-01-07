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
| [google_compute_global_address.lb_ip](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_global_address) | resource |
| [google_compute_network.vpc](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_network) | resource |
| [google_compute_subnetwork.app_subnet](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_subnetwork) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | The application name prefix used for resource naming. | `string` | n/a | yes |
| <a name="input_labels"></a> [labels](#input\_labels) | Labels to apply to networking resources. | `map(string)` | `{}` | no |
| <a name="input_log_config"></a> [log\_config](#input\_log\_config) | Configures VPC Flow Logs for the Subnet(s). Allows tuning of sampling and metadata to control costs. | <pre>object({<br/>    enable               = bool<br/>    aggregation_interval = optional(string, "INTERVAL_5_SEC") # Options: INTERVAL_5_SEC, INTERVAL_30_SEC, INTERVAL_1_MIN, etc.<br/>    flow_sampling        = optional(number, 0.5)              # 0.0 to 1.0 (1.0 = 100% of traffic). 0.5 is a good balance.<br/>    metadata             = optional(string, "INCLUDE_ALL_METADATA")<br/>  })</pre> | <pre>{<br/>  "aggregation_interval": "INTERVAL_5_SEC",<br/>  "enable": false,<br/>  "flow_sampling": 0.5,<br/>  "metadata": "INCLUDE_ALL_METADATA"<br/>}</pre> | no |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | The Google Cloud Project ID. | `string` | n/a | yes |
| <a name="input_region"></a> [region](#input\_region) | The default GCP region for regional resources. | `string` | n/a | yes |
| <a name="input_routing_mode"></a> [routing\_mode](#input\_routing\_mode) | The network-wide routing mode to use. If set to 'GLOBAL', the network's cloud routers will see all subnets in the network, across all regions. Options: 'REGIONAL', 'GLOBAL'. | `string` | `"GLOBAL"` | no |
| <a name="input_subnet_cidr"></a> [subnet\_cidr](#input\_subnet\_cidr) | The CIDR range for the primary application subnet. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_global_ip"></a> [global\_ip](#output\_global\_ip) | The reserved global static IP address. |
<!-- END_TF_DOCS -->