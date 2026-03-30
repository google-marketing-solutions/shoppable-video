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

"""API routes for generating Google Ads reports."""

import logging
from typing import Any, Dict, List

from app.api.dependencies import get_discovery_service
from app.api.dependencies import get_google_ads_service
from app.core.config import settings
from app.services.google_ads import GoogleAdsService
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/accessible-customers")
def get_accessible_customers(
    ga_service: GoogleAdsService = Depends(get_discovery_service),
) -> Dict[str, List[Dict[str, Any]]]:
  """Fetches globally accessible customers based on user token.

  Note:
    To call Ads API, a login-customer-id is needed. However,
    an edge case exists where a user only has access to a sub-MCC or
    sub-CID and not the platform ID. When this happens, the user will be
    prompted to select a customer ID to use for all Ads API calls.

  Args:
      ga_service: The Google Ads service instance.

  Returns:
      A dictionary containing a list of accessible customer details.
  """
  try:
    resource_names = ga_service.list_accessible_customers()
    platform_mcc = settings.GOOGLE_ADS_CUSTOMER_ID

    customers = []
    for resource_name in resource_names:
      # resource_name is typically "customers/1234567890"
      customer_id = int(resource_name.split("/")[-1])
      details = ga_service.get_customer_details(customer_id)

      if details:
        details["is_platform_customer_id"] = customer_id == platform_mcc
        customers.append(details)

    return {"data": customers}
  except Exception as e:
    logger.error("Error fetching accessible customers: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sub-accounts")
def get_sub_accounts(
    exclude_managers: bool = False,
    ga_service: GoogleAdsService = Depends(get_google_ads_service),
) -> Dict[str, List[Dict[str, Any]]]:
  """Lists sub-accounts under the active account context.

  Args:
      exclude_managers: Optional flag to filter out manager accounts.
      ga_service: The Google Ads service instance.

  Returns:
      A list of sub-accounts.
  """
  try:
    logger.info(
        "Fetching sub-accounts for CID: %s (exclude_managers=%s)",
        ga_service.login_customer_id,
        exclude_managers,
    )
    data = ga_service.list_accessible_subaccounts(
        exclude_managers=exclude_managers
    )
    logger.info(
        "Fetched %d sub-accounts for CID: %s",
        len(data),
        ga_service.login_customer_id,
    )
    return {"data": data}
  except Exception as e:
    logger.error("Error fetching sub-accounts: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/campaigns")
def get_campaigns(
    customer_id: int | None = None,
    campaign_types: List[str] = Query(default=["DEMAND_GEN"]),
    ga_service: GoogleAdsService = Depends(get_google_ads_service),
) -> Dict[str, Any]:
  """Fetches all enabled campaigns for the active customer context.

  Args:
      customer_id: Optional customer ID to filter campaigns.
      campaign_types: List of campaign types to filter by.
      ga_service: The contextualized Google Ads service instance.

  Returns:
      A dictionary containing the campaign data.

  Raises:
      HTTPException: If an error occurs during the API call.
  """
  try:
    data = ga_service.get_campaigns(
        customer_id=customer_id, campaign_types=campaign_types
    )
    logger.debug("Fetched campaigns for CID: %s", ga_service.login_customer_id)
    return {"data": data}
  except Exception as e:
    logger.error("Error fetching campaigns: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/ad-groups/{campaign_id}")
def get_ad_groups(
    campaign_id: int,
    customer_id: int | None = None,
    ga_service: GoogleAdsService = Depends(get_google_ads_service),
) -> Any:
  """Fetches ad groups for a specific campaign.

  Args:
      campaign_id: The ID of the campaign.
      customer_id: Optional customer ID to filter ad groups.
      ga_service: The Google Ads service instance.

  Returns:
      A list of ad groups.
  """
  try:
    logger.info(
        "Fetching ad groups for campaign %s and CID: %s (target CID: %s)",
        campaign_id,
        ga_service.login_customer_id,
        customer_id,
    )
    return ga_service.get_ad_groups(campaign_id, customer_id=customer_id)
  except Exception as e:
    logger.error("Error fetching ad groups: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/ad-groups-with-video/{video_id}")
def get_ad_groups_with_video(
    video_id: str,
    customer_id: int | None = None,
    ga_service: GoogleAdsService = Depends(get_google_ads_service),
) -> Dict[str, List[Dict[str, Any]]]:
  """Searches for existing ad groups linked to a video ID in Ads (Demand Gen).

  Args:
      video_id: The YouTube video ID.
      customer_id: Optional customer ID context for search.
      ga_service: The Google Ads service instance.

  Returns:
      A list of linked ad group destinations.
  """
  try:
    logger.info("Checking ad groups for video: %s", video_id)
    data = ga_service.get_ad_groups_with_video(
        video_id, customer_id=customer_id
    )
    return {"data": data}
  except Exception as e:
    logger.error("Error searching video links: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e
