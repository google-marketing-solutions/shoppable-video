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

"""This module defines data models for Ad Group Insertion Status."""

import datetime
from typing import Optional, List
import pydantic


class ProductInsertionStatus(pydantic.BaseModel):
  """Represents the status of a product insertion.

  Attributes:
    offer_id: The ID of the offer.
    status: The status of the product insertion.
  """
  offer_id: str
  status: str


class AdsEntityStatus(pydantic.BaseModel):
  """Represents the status of an Ads entity insertion.

  Attributes:
    customer_id: The Google Ads Customer ID.
    campaign_id: The Google Ads Campaign ID.
    ad_group_id: The Google Ads Ad Group ID.
    products: The list of products in this ad group.
    error_message: Optional error message if the insertion failed.
  """
  customer_id: int
  campaign_id: int
  ad_group_id: int
  products: List[ProductInsertionStatus]
  error_message: Optional[str] = None


class AdGroupInsertionStatus(pydantic.BaseModel):
  """Represents the status of an Ad Group insertion request.

  Attributes:
    request_uuid: The UUID of the request.
    video_analysis_uuid: The UUID of the video analysis.
    status: The overall status of the request.
    ads_entities: The list of Ads entities involved.
    timestamp: The timestamp of the status record.
  """
  request_uuid: str
  video_analysis_uuid: str
  status: str
  ads_entities: List[AdsEntityStatus]
  timestamp: datetime.datetime


class PaginatedAdGroupInsertionStatus(pydantic.BaseModel):
  """A paginated response for Ad Group insertion statuses."""
  items: List[AdGroupInsertionStatus]
  total_count: int
  limit: int
  offset: int
