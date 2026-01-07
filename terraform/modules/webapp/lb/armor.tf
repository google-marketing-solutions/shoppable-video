# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# you may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# terraform/modules/webapp/lb/armor.tf

# ------------------------------------------------------------------------------
# CLOUD ARMOR SECURITY POLICY
# ------------------------------------------------------------------------------
# Defines the Web Application Firewall (WAF) rules applied at the edge.
# This policy protects the application from common web attacks and abuse.
# ------------------------------------------------------------------------------

resource "google_compute_security_policy" "edge_sec" {
  count = var.armor_settings.enable_cloud_armor ? 1 : 0

  name        = "${var.app_name}-waf-policy"
  description = "Cloud Armor WAF policy covering OWASP Top 10 and custom rules."
  project     = var.project_id
  type        = "CLOUD_ARMOR"

  # ----------------------------------------------------------------------------
  # 1. GLOBAL DENYLIST RULES
  # ----------------------------------------------------------------------------
  # Blocks specific IP ranges from accessing the application entirely.
  dynamic "rule" {
    for_each = var.armor_settings.denylist_ips
    content {
      action   = "deny(403)"
      priority = 10 + rule.key
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = [rule.value]
        }
      }
      description = "Denies access from specific IP address."
    }
  }

  # ----------------------------------------------------------------------------
  # 2. CUSTOM USER RULES
  # ----------------------------------------------------------------------------
  # Injects custom CEL expressions defined by the user.
  # Handles logic like Geo-blocking or Rate Limiting.
  dynamic "rule" {
    for_each = var.armor_settings.custom_rules
    content {
      action   = rule.value.action
      priority = rule.value.priority
      match {
        expr {
          expression = rule.value.expression
        }
      }
      description = try(rule.value.description, "Custom User Rule")

      # Applies rate limiting configuration if provided.
      dynamic "rate_limit_options" {
        for_each = rule.value.rate_limit != null ? [rule.value.rate_limit] : []
        content {
          conform_action = rate_limit_options.value.conform_action
          exceed_action  = rate_limit_options.value.exceed_action

          # 'enforce_on_key' defines how clients are identified (e.g., by IP).
          # Defaulting to 'IP' if not specified in the complex object.
          enforce_on_key = "IP"

          # 'rate_limit_threshold' must be a nested block, NOT an attribute.
          rate_limit_threshold {
            count        = rate_limit_options.value.rate_limit_threshold
            interval_sec = rate_limit_options.value.interval_sec
          }
        }
      }
    }
  }

  # ----------------------------------------------------------------------------
  # 3. MANAGED RULE SETS (OWASP PROTECTION)
  # ----------------------------------------------------------------------------
  # Iterates over the managed_rules map to enable Google's pre-configured rules.
  dynamic "rule" {
    for_each = { for k, v in var.armor_settings.managed_rules : k => v if v.enabled }
    content {
      action   = rule.value.action
      priority = rule.value.priority
      match {
        expr {
          expression = "evaluatePreconfiguredWaf('${rule.key}', {'sensitivity': ${rule.value.sensitivity_level}})"
        }
      }
      description = "Managed Rule: ${rule.key} (Sensitivity: ${rule.value.sensitivity_level})"
    }
  }

  # ----------------------------------------------------------------------------
  # 4. DEFAULT RULE
  # ----------------------------------------------------------------------------
  # Allows all traffic that hasn't been explicitly blocked by previous rules.
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule."
  }
}
