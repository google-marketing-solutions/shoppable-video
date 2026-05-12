# Copyright 2025 Google LLC
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

"""This module defines data models for video-related records."""

import datetime
from typing import Dict, List, Optional

from app.models import product
import pydantic


class VideoMetadata(pydantic.BaseModel):
  """Represents metadata for a video.

  Attributes:
    title: the title of the video
    description: the description of the video
  """

  title: Optional[str] = None
  description: Optional[str] = None


class Video(pydantic.BaseModel):
  """Represents a video either from Youtube or GCS.

  Attributes:
    uuid: a unique identifier for the video
    video_id: a video ID (applicable for Youtube)
    source: one of google_ads, gcs, or manual_entry
    gcs_uri: a GCS URI (applicable for GCS)
    md5_hash: a MD5 hash (applicable for GCS)
    metadata: metadata for the video
  """

  uuid: str
  source: str
  video_id: Optional[str] = None
  gcs_uri: Optional[str] = None
  md5_hash: Optional[str] = None
  metadata: Optional[VideoMetadata] = None


class VideoAnalysis(pydantic.BaseModel):
  """Represents a video analysis and its associated products.

  Attributes:
    video: the video that was analyzed.
    identified_products: a list of identified products.
  """

  video: Video
  identified_products: List[product.IdentifiedProduct]


class VideoAnalysisSummary(pydantic.BaseModel):
  """Represents a summary of a video analysis.

  Attributes:
    video: the video that was analyzed.
    identified_products_count: the number of identified products.
    matched_products_count: the number of matched products across all identified
      products.
    approved_products_count: the number of approved matched products.
    active_pushes: a dictionary mapping request UUIDs to timestamps for active
      pushes.
    has_successful_push: a boolean indicating if the video has any successful
      pushes.
    status: the consolidated status for the video.
  """

  video: Video
  identified_products_count: int = pydantic.Field(ge=0)
  matched_products_count: int = pydantic.Field(ge=0)
  approved_products_count: int = pydantic.Field(ge=0)
  active_pushes: Dict[str, datetime.datetime] = pydantic.Field(
      default_factory=dict
  )
  has_successful_push: bool = False
  status: str = ""


class PaginationParams(pydantic.BaseModel):
  """Pagination parameters."""

  limit: int = pydantic.Field(default=10, ge=0)
  offset: int = pydantic.Field(default=0, ge=0)
  search_term: Optional[str] = None
  status_filter: Optional[str] = None


class PaginatedVideoAnalysisSummary(pydantic.BaseModel):
  """A paginated response for video analysis summaries."""

  items: List[VideoAnalysisSummary]
  total_count: int
  limit: int
  offset: int
