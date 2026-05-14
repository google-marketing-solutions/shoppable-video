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

"""Routes for managing Ad Group Insertion Status."""

import logging
from typing import Sequence

from app.api import dependencies
from app.models import ad_group_insertion
from app.services import firestore_service
from app.services import google_ads
import fastapi

logger = logging.getLogger(__name__)

router = fastapi.APIRouter(
    dependencies=[fastapi.Depends(dependencies.get_session_data)]
)


def _enrich_ads_entities(
    items: Sequence[ad_group_insertion.AdGroupInsertionStatus],
    ga_service: google_ads.GoogleAdsService,
) -> None:
  """Enriches Ads entities with human-readable names from Google Ads API."""
  # Group ad group IDs by customer ID
  ag_by_customer = {}
  for item in items:
    for entity in item.ads_entities:
      if entity.customer_id and entity.ad_group_id:
        if entity.customer_id not in ag_by_customer:
          ag_by_customer[entity.customer_id] = set()
        ag_by_customer[entity.customer_id].add(entity.ad_group_id)

  # Fetch metadata and build cache
  cache = {}
  for cust_id, ag_ids in ag_by_customer.items():
    try:
      metadata = ga_service.get_ad_groups_metadata(
          list(ag_ids), customer_id=cust_id
      )
      for md in metadata:
        cache[(cust_id, md.get("ad_group_id"))] = md
    except Exception as e:  # pylint: disable=broad-except
      logger.warning("Failed to fetch metadata for customer %s: %s", cust_id, e)

  # Attach metadata to entities
  for item in items:
    for entity in item.ads_entities:
      md = cache.get((entity.customer_id, entity.ad_group_id))
      if md:
        entity.customer_name = md.get("customer_name")
        entity.campaign_name = md.get("campaign_name")
        entity.ad_group_name = md.get("ad_group_name")


@router.get(
    "/status",
    response_model=ad_group_insertion.PaginatedAdGroupInsertionStatus,
)
def get_all_ad_group_insertion_statuses(
    pagination: ad_group_insertion.AdGroupPaginationParams = fastapi.Depends(),
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
    ga_service: google_ads.GoogleAdsService = fastapi.Depends(
        dependencies.get_google_ads_service
    ),
):
  """Retrieves all Ad Group insertion statuses with pagination.

  Args:
    pagination: Pagination parameters (limit, offset, user_filter).
    fs_service: The Firestore service instance.
    ga_service: The Google Ads service instance.

  Returns:
    A paginated list of Ad Group insertion status records.
  """
  paginated_status = fs_service.get_all_ad_group_insertion_statuses(pagination)
  _enrich_ads_entities(paginated_status.items, ga_service)
  return paginated_status


@router.get(
    "/status/{request_uuid}",
    response_model=Sequence[ad_group_insertion.AdGroupInsertionStatus],
)
def get_ad_group_insertion_status(
    request_uuid: str,
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
    ga_service: google_ads.GoogleAdsService = fastapi.Depends(
        dependencies.get_google_ads_service
    ),
):
  """Retrieves the status of an Ad Group insertion request.

  Args:
    request_uuid: The UUID of the request.
    fs_service: The Firestore service instance.
    ga_service: The Google Ads service instance.

  Returns:
    A list of Ad Group insertion status records.
  """
  statuses = fs_service.get_ad_group_insertion_status(request_uuid)
  _enrich_ads_entities(statuses, ga_service)
  return statuses


@router.get(
    "/status/video/{video_uuid}",
    response_model=Sequence[ad_group_insertion.AdGroupInsertionStatus],
)
def get_ad_group_insertion_statuses_for_video(
    video_uuid: str,
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
    ga_service: google_ads.GoogleAdsService = fastapi.Depends(
        dependencies.get_google_ads_service
    ),
):
  """Retrieves the Ad Group insertion statuses for a specific video.

  Args:
    video_uuid: The UUID of the video.
    fs_service: The Firestore service instance.
    ga_service: The Google Ads service instance.

  Returns:
    A list of Ad Group insertion status records.
  """
  statuses = fs_service.get_ad_group_insertion_statuses_for_video(video_uuid)
  _enrich_ads_entities(statuses, ga_service)
  return statuses
