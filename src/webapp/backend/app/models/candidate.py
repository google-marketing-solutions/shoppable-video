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

"""This module defines data models for candidate-related records."""

import datetime
import enum
from typing import Optional
import pydantic


class Status(str, enum.Enum):
  APPROVED = "APPROVED"
  DISAPPROVED = "DISAPPROVED"
  UNREVIEWED = "UNREVIEWED"


class Destination(pydantic.BaseModel):
  """Represents a destination for approval."""

  ad_group_id: str
  campaign_id: str
  customer_id: str
  ad_group_name: Optional[str] = None


class SubmissionMetadata(pydantic.BaseModel):
  """Represents additional metadata for submission status.

  Attributes:
    request_uuid: The UUID of the submission request.
    video_uuid: The UUID of the video.
    offer_ids: Comma-separated list of offer IDs.
    destinations: List of destinations where the product is submitted.
    submitting_user: The email of the user who submitted the request.
  """

  request_uuid: Optional[str] = None
  video_uuid: Optional[str] = None
  offer_ids: Optional[str] = None
  destinations: Optional[list[Destination]] = None
  submitting_user: Optional[str] = None


class CandidateStatus(pydantic.BaseModel):
  """Represents a candidate status for a matched product.

  Attributes:
    status: the status of the candidate (approved, disapproved, etc.)
    user: the email of the user who modified the candidate.
    is_added_by_user: if the candidate was added by a user (not automatically
      identified by the pipeline)
    modified_timestamp: a timestamp marking when the status was modified.
  """

  status: Status
  user: Optional[str] = None
  is_added_by_user: Optional[bool] = False
  modified_timestamp: Optional[datetime.datetime] = None


class Candidate(pydantic.BaseModel):
  """Represents a candidate product to be added to a product group."""

  video_analysis_uuid: str
  identified_product_uuid: str
  candidate_offer_id: str
  candidate_status: CandidateStatus
