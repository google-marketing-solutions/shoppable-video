# Copyright 2025 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common Module."""

import dataclasses
import json
import os
from typing import Optional


class Error(Exception):
  """Generic Error class for module."""


@dataclasses.dataclass
class Product:
  """Product data class."""

  offer_id: str
  # Core Attributes
  title: str
  brand: str
  description: str
  # Categorization
  product_type: str
  google_product_category: str
  # Additional attributes
  age_group: Optional[str] = None
  color: Optional[str] = None
  gender: Optional[str] = None
  material: Optional[str] = None
  pattern: Optional[str] = None

  def to_json(self) -> str:
    """Returns a JSON string representation of the Product."""
    return json.dumps(dataclasses.asdict(self))


def get_env_var(key: str) -> str:
  """Gets an environment variable or raises an exception if it is not set."""
  value = os.environ.get(key)
  if not value:
    raise ValueError(f'{key} environment variable is not set.')
  return value
