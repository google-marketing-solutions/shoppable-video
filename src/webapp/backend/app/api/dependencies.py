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

"""FastAPI dependency-injection functions for auth and service init."""

import functools
import json
import logging
from typing import Annotated, Any, Dict

from app.core.config import settings
from app.core.security import decrypt_token
from app.services import bigquery_service
from app.services import google_ads
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from google.ads.googleads import client

logger = logging.getLogger(__name__)


def get_session_data(request: Request) -> Dict[str, Any]:
  """Retrieves and decrypts session data from the HttpOnly cookie.

  Args:
      request (Request): The incoming HTTP request.

  Returns:
      Dict[str, Any]: The decrypted session payload containing user info and
        refresh token.

  Raises:
      HTTPException: If the cookie is missing or invalid.
  """
  encrypted_token = request.cookies.get("session_token")
  if not encrypted_token:
    raise HTTPException(status_code=401, detail="Not Authenticated")
  try:
    decrypted_payload = decrypt_token(encrypted_token)
    return json.loads(decrypted_payload)
  except Exception as exc:
    logger.error("Session validation failed: %s", exc)
    raise HTTPException(status_code=401, detail="Invalid Session") from exc


def _initialize_ads_client(
    session_data: Dict[str, Any], login_customer_id: str | None = None
) -> client.GoogleAdsClient:
  """Initializes GoogleAdsClient using a refresh token from a session.

  Args:
      session_data (Dict): The decrypted session payload containing the user's
        refresh token.
      login_customer_id (str | None): Optional Google Ads Customer ID to use as
        the `login-customer-id` header. Defines the operating context, allowing
        the app to act on behalf of an MCC or a direct sub-account.

  Returns:
      client.GoogleAdsClient: An authenticated Google Ads API client.
  """
  refresh_token = session_data.get("rt")
  if not refresh_token:
    logger.error("Session data missing refresh token.")
    raise HTTPException(status_code=401, detail="Invalid Session Structure")
  try:
    config = {
        "developer_token": settings.GOOGLE_ADS_DEVELOPER_TOKEN,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }
    if login_customer_id:
      config["login_customer_id"] = login_customer_id.replace("-", "")

    return client.GoogleAdsClient.load_from_dict(config)
  except Exception as e:
    logger.error("Google Ads Client initialization failed: %s", e)
    raise HTTPException(
        status_code=500, detail="Service Configuration Error"
    ) from e


def get_google_ads_service(
    session_data: Annotated[Dict[str, Any], Depends(get_session_data)],
    login_customer_id: Annotated[str | None, Query()] = None,
) -> google_ads.GoogleAdsService:
  """Dependency to provide an initialized GoogleAdsService.

  This dependency manages the dual-path account context:
  1. Default Path (Platform MCC Admin): If no `login_customer_id` is
     requested, the service falls back to the `GOOGLE_ADS_CUSTOMER_ID`.
  2. Fallback Path (Sub-Account User): If a user selects a specific CID
     during discovery, the frontend passes it via the `login_customer_id`
     query parameter.

  Args:
      session_data: The decrypted session payload.
      login_customer_id: The explicit target customer ID provided via
        query params.

  Returns:
      google_ads.GoogleAdsService: The configured service instance.

  Raises:
      HTTPException: If the customer ID is missing or client init fails.
  """
  target_id = login_customer_id or settings.GOOGLE_ADS_CUSTOMER_ID
  if not target_id:
    logger.error("Google Ads Customer ID is not provided or configured.")
    raise HTTPException(
        status_code=500, detail="Google Ads configuration error."
    )

  try:
    logger.info("Initializing Ads Service for CID: %s", target_id)
    ads_client = _initialize_ads_client(session_data, target_id)
    return google_ads.GoogleAdsService(ads_client, login_customer_id=target_id)
  except Exception as e:
    logger.error("Unexpected error during Ads Service initialization: %s", e)
    raise HTTPException(status_code=500, detail="Ads Service failure") from e


def get_discovery_service(
    session_data: Annotated[Dict[str, Any], Depends(get_session_data)],
) -> google_ads.GoogleAdsService:
  """Dependency for account discovery (initializes client WITHOUT a context)."""
  try:
    logger.info("Initializing Ads Discovery Service (No Context)")
    ads_client = _initialize_ads_client(session_data)
    return google_ads.GoogleAdsService(ads_client)
  except Exception as e:
    logger.error("Discovery Service failure: %s", e)
    raise HTTPException(status_code=500, detail="Discovery failure") from e


@functools.lru_cache()
def get_bigquery_service() -> bigquery_service.BigQueryService:
  """Creates and caches a singleton instance of the BigQueryService.

  This ensures that the BigQuery client is reused across requests,
  optimizing connection management.

  Returns:
    bigquery_service.BigQueryService: A BigQueryService instance.
  """
  table_ids = {
      "video_analysis_table_id": settings.VIDEO_ANALYSIS_TABLE_ID,
      "matched_products_table_id": settings.MATCHED_PRODUCTS_TABLE_ID,
      "matched_products_view_id": settings.MATCHED_PRODUCTS_VIEW_ID,
      "candidate_status_table_id": settings.CANDIDATE_STATUS_TABLE_ID,
      "candidate_status_view_id": settings.CANDIDATE_STATUS_VIEW_ID,
      "google_ads_insertion_requests_table_id": (
          settings.GOOGLE_ADS_INSERTION_REQUESTS_TABLE_ID
      ),
      "ad_group_insertion_status_table_id": (
          settings.AD_GROUP_INSERTION_STATUS_TABLE_ID
      ),
      "latest_products_table_id": settings.LATEST_PRODUCTS_TABLE_ID,
  }

  return bigquery_service.BigQueryService(
      project_id=settings.PROJECT_ID,
      dataset_id=settings.DATASET_ID,
      table_ids=table_ids,
  )
