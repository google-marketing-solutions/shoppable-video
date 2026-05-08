# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""General utility functions and shared helpers for the push-to-ads module."""

from typing import Any
import models


def normalize_customer_id(customer_id: Any) -> str:
  """Ensures consistency and strips hyphens from any customer ID input.

  Args:
    customer_id: Raw string, number, or object representation of the ID.

  Returns:
    A clean, stringified identifier string with hyphens completely removed.
  """
  if not customer_id:
    return ""
  return str(customer_id).replace("-", "")


def parse_strategy(raw_strategy: Any) -> models.ListingGroupStrategy:
  """Safely promotes arbitrary raw metadata inputs into typed update strategies.

  Args:
    raw_strategy: Raw object/string extracted from metadata maps.

  Returns:
    The recognized ListingGroupStrategy value, falling back to PRESERVE.
  """
  if isinstance(raw_strategy, models.ListingGroupStrategy):
    return raw_strategy
  try:
    return models.ListingGroupStrategy[str(raw_strategy or "PRESERVE").upper()]
  except (KeyError, ValueError, TypeError):
    return models.ListingGroupStrategy.PRESERVE
