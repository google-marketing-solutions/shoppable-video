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

from app.api.dependencies import get_authenticated_client
from app.services.google_ads import GoogleAdsService

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from google.ads.googleads.client import GoogleAdsClient  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/campaigns/{customer_id}")
def get_campaigns(
    customer_id: str,
    client: GoogleAdsClient = Depends(get_authenticated_client),
) -> Dict[str, Any]:
  """Fetches all enabled campaigns for a given customer_id.

  Args:
      customer_id: The ID of the customer to fetch campaigns for.
      client: The Google Ads client instance.

  Returns:
      A dictionary containing the campaign data.

  Raises:
      HTTPException: If an error occurs during the API call.
  """
  try:
    service = GoogleAdsService(client, customer_id)
    data = service.get_campaigns()
    return {"data": data}
  except Exception as e:
    logger.error("Error fetching campaigns: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/rsa/{customer_id}")
def get_rsa_ads(
    customer_id: str,
    client: GoogleAdsClient = Depends(get_authenticated_client),
) -> Dict[str, Any]:
  """Fetches Responsive Search Ads (RSA).

  Args:
      customer_id: The ID of the customer to fetch RSA ads for.
      client: The Google Ads client instance.

  Returns:
      A dictionary containing the RSA ads data.

  Raises:
      HTTPException: If an error occurs during the API call.
  """
  try:
    service = GoogleAdsService(client, customer_id)
    data = service.get_rsa_ads()
    return {"data": data}
  except Exception as e:
    logger.error("Error fetching RSA ads: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/disapproved/{customer_id}")
def get_disapproved_ads(
    customer_id: str,
    client: GoogleAdsClient = Depends(get_authenticated_client),
) -> Dict[str, Any]:
  """Fetches Disapproved Ads and their policy topics.

  Args:
      customer_id: The ID of the customer to fetch disapproved ads for.
      client: The Google Ads client instance.

  Returns:
      A dictionary containing the disapproved ads data.

  Raises:
      HTTPException: If an error occurs during the API call.
  """
  try:
    service = GoogleAdsService(client, customer_id)
    data = service.get_disapproved_ads()
    return {"data": data}
  except Exception as e:
    logger.error("Error fetching disapproved ads: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/categories/{customer_id}")
def get_categories(
    customer_id: str,
    client: GoogleAdsClient = Depends(get_authenticated_client),
) -> Dict[str, Any]:
  """Fetches Constant Categories.

  Args:
      customer_id: The ID of the customer to fetch categories for.
      client: The Google Ads client instance.

  Returns:
      A dictionary containing the categories data.

  Raises:
      HTTPException: If an error occurs during the API call.
  """
  try:
    service = GoogleAdsService(client, customer_id)
    data = service.get_categories()
    return {"data": data}
  except Exception as e:
    logger.error("Error fetching categories: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e
