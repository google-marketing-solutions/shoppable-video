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
import datetime
import enum
import json
import os
from typing import Optional


class Error(Exception):
  """Generic Error class for module."""


@dataclasses.dataclass
class Product:
  """Product data class representing an actual product from Merchant Center."""

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


class Source(enum.Enum):
  """Enum for video sources."""

  GOOGLE_ADS = "google_ads"
  GCS = "gcs"
  MANUAL_ENTRY = "manual_entry"


@dataclasses.dataclass
class Video:
  """Video data class."""

  source: Source
  video_id: Optional[str] = None
  gcs_uri: Optional[str] = None
  md5_hash: Optional[str] = None

  def __post_init__(self):
    if (self.video_id is not None) + (self.gcs_uri is not None) != 1:
      raise ValueError(
          "Exactly one of youtube_id or gcs_uri must be provided."
      )

  def to_json(self) -> str:
    """Returns a JSON string representation of the Video."""
    return json.dumps(dataclasses.asdict(self))


@dataclasses.dataclass
class IdentifiedProduct:
  """Product data class representing a product identified by Gemini."""

  title: str
  description: str
  color_pattern_style_usage: str
  category: str
  subcategory: Optional[str]
  video_timestamp: datetime.timedelta

  def to_json(self) -> str:
    """Returns a JSON string representation of the IdentifiedProduct."""
    return json.dumps(dataclasses.asdict(self))


def get_env_var(key: str) -> str:
  """Gets an environment variable or raises an exception if it is not set."""
  value = os.environ.get(key)
  if not value:
    raise ValueError(f"{key} environment variable is not set.")
  return value
