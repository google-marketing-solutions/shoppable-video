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

import datetime
import enum
from typing import List, Optional

import pydantic


class Video(pydantic.BaseModel):
  video_location: str
  video_id: str
  gcs_uri: Optional[str] = None
  md5_hash: Optional[str] = None


class MatchedProduct(pydantic.BaseModel):
  matched_product_offer_id: str
  matched_product_title: str
  matched_product_brand: str
  timestamp: datetime.datetime
  distance: float


class IdentifiedProduct(pydantic.BaseModel):
  title: str
  description: str
  relevance_reasoning: str
  product_uuid: str
  matched_products: List[MatchedProduct]


class VideoAnalysis(pydantic.BaseModel):
  video_analysis_uuid: str
  source: str
  video: Video
  identified_products: List[IdentifiedProduct]


class Status(str, enum.Enum):
  PENDING = "Pending"
  COMPLETED = "Completed"
  FAILED = "Failed"
  DISAPPROVED = "Disapproved"
  UNREVIEWED = "Unreviewed"


class CandidateStatus(pydantic.BaseModel):
  video_analysis_uuid: str
  candidate_offer_id: str
  status: Status
