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
import re
from typing import Any, Optional
import uuid

GCS_URI_PATTERN = re.compile(r'^(?:gs://)?([^/]+)(?:/(.*))?$')


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

  def get_text_for_embedding(self) -> str:
    """Returns the text to be used in generating an embedding for the given product."""
    attributes = [
        ('Title', self.title),
        ('Brand', self.brand),
        ('Product Category', self.google_product_category),
        ('Product Type', self.product_type),
        ('Age Group', self.age_group),
        ('Color', self.color),
        ('Gender', self.gender),
        ('Material', self.material),
        ('Pattern', self.pattern),
        ('Description', self.description),
    ]
    return '\n'.join(
        [f'{label}: {value}' for label, value in attributes if value]
    )


class Source(str, enum.Enum):
  """Enum for video sources."""

  GOOGLE_ADS = 'google_ads'
  GCS = 'gcs'
  MANUAL_ENTRY = 'manual_entry'


@dataclasses.dataclass
class Video:
  """Video data class."""

  source: Source
  video_id: Optional[str] = None
  gcs_uri: Optional[str] = None
  md5_hash: Optional[str] = None

  def __post_init__(self):
    """Validates that exactly one of `video_id` or `gcs_uri` is provided."""
    if (self.video_id is not None) + (self.gcs_uri is not None) != 1:
      raise ValueError('Exactly one of youtube_id or gcs_uri must be provided.')

  def to_json(self) -> str:
    """Returns a JSON string representation of the Video."""
    return json.dumps(dataclasses.asdict(self))

  def get_resource_id(self) -> str:
    """Returns the resource ID of the video (for logging)."""
    return self.video_id or self.gcs_uri or ''


@dataclasses.dataclass
class IdentifiedProduct:
  """Product data class representing a product identified by Gemini."""

  title: str
  description: str
  color_pattern_style_usage: str
  category: str
  subcategory: Optional[str]
  video_timestamp: datetime.timedelta
  relevance_reasoning: str
  embedding: Optional[list[float]]
  uuid: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))

  def to_dict(self, exclude_embedding: bool = False) -> dict[str, Any]:
    """Returns a dictionary representation of the IdentifiedProduct.

    Args:
      exclude_embedding: if True, embedding vector will be included in output.

    Returns:
      A dict of the dataclass with some fields formatted (e.g `video_timestamp`
      field is converted to milliseconds.)
    """
    product_dict = dataclasses.asdict(self)
    product_dict['video_timestamp'] = int(
        self.video_timestamp.total_seconds() * 1000
    )
    if 'embedding' in product_dict and exclude_embedding:
      del product_dict['embedding']
    return product_dict

  def get_text_for_embedding(self) -> str:
    """Returns the text to be used in generating an embedding for the given product."""
    attributes = [
        ('Title', self.title),
        ('Description', self.description),
        ('Color, Pattern, Style, Usage', self.color_pattern_style_usage),
        ('Category', self.category),
        ('Subcategory', self.subcategory),
    ]
    return '\n'.join(
        [f'{label}: {value}' for label, value in attributes if value]
    )


def get_env_var(key: str) -> str:
  """Gets an environment variable or raises an exception if it is not set."""
  value = os.environ.get(key)
  if not value:
    raise ValueError(f"'{key}' environment variable is not set or empty.")
  return value


def split_gcs_uri(gcs_uri: str) -> tuple[str, str]:
  """Splits a Cloud Storage URI into its bucket and path."""
  match = GCS_URI_PATTERN.match(gcs_uri)
  if not match:
    raise ValueError(f'Unable to parse provided GCS URI: {gcs_uri}')
  bucket = match.group(1)
  path = match.group(2)
  return bucket, path
