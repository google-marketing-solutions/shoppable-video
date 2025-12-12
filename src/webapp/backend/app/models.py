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

"""This module defines data models for video analysis records."""
import enum
from typing import List
from pydantic import BaseModel


class Video(BaseModel):
  video_id: str
  gcs_uri: str


class MatchedProduct(BaseModel):
  offer_id: str
  rank: int


class IdentifiedProduct(BaseModel):
  title: str
  description: str
  color_pattern_style_usage: str
  category: str
  subcategory: str
  image_timestamp_ms: int
  matched_product: List[MatchedProduct]


class VideoAnnotation(BaseModel):
  video: Video
  identified_product: List[IdentifiedProduct]


class Status(str, enum.Enum):
  PENDING = "Pending"
  COMPLETED = "Completed"
  FAILED = "Failed"
  DISAPPROVED = "Disapproved"
  UNREVIEWED = "Unreviewed"


class CandidateStatus(BaseModel):
  video_id: str
  candidate_offer_id: str
  status: Status
