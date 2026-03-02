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
from typing import Any, Dict

from app.api.dependencies import get_google_ads_service
from app.services.google_ads import GoogleAdsService
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/campaigns/{customer_id}")
def get_campaigns(
    customer_id: str,
    ga_service: GoogleAdsService = Depends(get_google_ads_service),
) -> Dict[str, Any]:
  """Fetches all enabled campaigns for a given customer_id.

  Args:
      customer_id: The ID of the customer to fetch campaigns for.
      ga_service: The Google Ads service instance.

  Returns:
      A dictionary containing the campaign data.

  Raises:
      HTTPException: If an error occurs during the API call.
  """
  try:
    data = ga_service.get_campaigns()
    # TODO(blakegoodwin): Standardize how customer ID is handled.
    logger.debug("Fetched campaigns: %s", customer_id)
    return {"data": data}
  except Exception as e:
    logger.error("Error fetching campaigns: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/ad-groups/{campaign_id}")
def get_ad_groups(
    campaign_id: str,
    ga_service: GoogleAdsService = Depends(get_google_ads_service),
) -> Any:
  """Fetches ad groups for a specific campaign.

  Args:
      campaign_id: The ID of the campaign.
      ga_service: The Google Ads service instance.

  Returns:
      A list of ad groups.
  """
  try:
    return ga_service.get_ad_groups(campaign_id)
  except Exception as e:
    logger.error("Error fetching ad groups: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e
