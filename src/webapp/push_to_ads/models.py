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

"""Defines data models and enumerations for Google Ads listing hierarchies."""

from __future__ import annotations
import dataclasses
import enum
from typing import List, Optional
from google.ads.googleads.v22.common.types.criteria import ListingDimensionInfo


class AdGroupInsertionStatus(enum.StrEnum):
  """Standardized statuses for tracking ad group and product insertions."""

  SUCCESS = "SUCCESS"
  FAILED = "FAILED"
  ALREADY_PRESENT = "ALREADY_PRESENT"
  PENDING = "PENDING"
  PROCESSING = "PROCESSING"
  PARTIAL_SUCCESS = "PARTIAL_SUCCESS"


class VideoPushStatus(enum.StrEnum):
  """Statuses for tracking video push operations."""

  IN_PROGRESS = "Push in Progress"
  COMPLETE = "Push Complete"
  READY = "Ready to Push"
  NEEDS_REVIEW = "Needs Review"


class ListingGroupStrategy(enum.Enum):
  """Defines update strategy for Listing Group structures.

  Attributes:
    PURGE: Fully demolishes all existing child tree structures from the root
      before bootstrapping a brand new partition set.
    PRESERVE: Safely traverses and retains existing valid partition divisions
  """

  PURGE = "PURGE"
  PRESERVE = "PRESERVE"


class TreeState(enum.Enum):
  """Specifies the status of the existing listing partition tree.

  Attributes:
    CLEAN: No prior partitioned children exist below the root.
    PARTITIONED: Top-level tree successfully established via item-IDs.
    DIRTY: Tree has unrecognized partition dimensions or corrupted depth.
  """

  CLEAN = "CLEAN"
  PARTITIONED = "PARTITIONED"
  DIRTY = "DIRTY"


@dataclasses.dataclass
class ListingNode:
  """Represents a node within the listing tree.

  Attributes:
    resource_name: The unique identifier path within the Google Ads API.
    node_type: Integer representing GoogleAds ListingGroupTypeEnum value.
    parent_resource_name: The resource name of node directly above in hierarchy.
    case_value: The underlying proto message instance defining node condition.
    is_negative: Boolean status dictating if node is explicitly excluded.
    children: A collection of ListingNode instances placed topologically below.
    depth: Numeric scalar representation of distance from relative tree root.
    partition_dimension: Label representing the active dimension constraint.
    partition_index: The integer tier (level/index offset 0-4) on node.
  """

  resource_name: str
  node_type: int
  parent_resource_name: Optional[str] = None
  case_value: Optional[ListingDimensionInfo] = None
  is_negative: bool = False
  children: List["ListingNode"] = dataclasses.field(default_factory=list)
  depth: int = 0
  partition_dimension: Optional[str] = None
  partition_index: Optional[int] = None


@dataclasses.dataclass
class ProductResult:
  """Stores the status of a single product identifier.

  Attributes:
    offer_id: Targeted item identifier.
    status: Descriptive processing outcome (e.g., SUCCESS, ALREADY_PRESENT).
  """

  offer_id: str
  status: AdGroupInsertionStatus


@dataclasses.dataclass
class DeploymentResult:
  """Calculates metrics from a single batch deployment.

  Attributes:
    success_count: Total count of items accepted by pipeline.
    total_count: Total count of targeted inputs submitted.
  """

  success_count: int
  total_count: int


@dataclasses.dataclass
class AdsMutationResult:
  """Wraps final insertion feedback after committing to API.

  Attributes:
    ad_group_id: The target ID where insertions executed.
    campaign_id: Primary parent identifier context.
    customer_id: Primary login client account context.
    products: Iteration containing discrete status summaries for each product.
    error_message: Terminal error description if batch-level fault occurred.
  """

  ad_group_id: int
  campaign_id: int
  customer_id: str
  products: List[ProductResult]
  error_message: Optional[str] = None
