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
| [google_dns_managed_zone.main](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/dns_managed_zone) | resource |
| [google_dns_record_set.a_record](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/dns_record_set) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_create_zone"></a> [create\_zone](#input\_create\_zone) | If true, Terraform will create a new Cloud DNS Managed Zone. If false, it assumes the zone exists. | `bool` | `false` | no |
| <a name="input_dns_project_id"></a> [dns\_project\_id](#input\_dns\_project\_id) | The GCP Project ID where the Cloud DNS Managed Zone is located. | `string` | n/a | yes |
| <a name="input_domain_name"></a> [domain\_name](#input\_domain\_name) | The fully qualified domain name (FQDN) to register (e.g., 'app.example.com'). | `string` | n/a | yes |
| <a name="input_lb_ip_address"></a> [lb\_ip\_address](#input\_lb\_ip\_address) | The global IP address of the Load Balancer to point the A-record to. | `string` | n/a | yes |
| <a name="input_managed_zone_name"></a> [managed\_zone\_name](#input\_managed\_zone\_name) | The name of the Cloud DNS Managed Zone (e.g., 'example-zone'). | `string` | n/a | yes |
| <a name="input_zone_dns_name"></a> [zone\_dns\_name](#input\_zone\_dns\_name) | The DNS suffix for the zone (e.g., 'example.com.'). Required only if 'create\_zone' is true. | `string` | `""` | no |

## Outputs

No outputs.
<!-- END_TF_DOCS -->