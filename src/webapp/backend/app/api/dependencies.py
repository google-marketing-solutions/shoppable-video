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

"""FastAPI dependency-injection functions for auth and service init."""

import functools
import json
import logging
from typing import Annotated, Any, Dict

from app.core import config
from app.core import security
from app.services import firestore_service
from app.services import google_ads
import fastapi
from google.ads.googleads import client

logger = logging.getLogger(__name__)


def get_session_data(request: fastapi.Request) -> Dict[str, Any]:
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
    raise fastapi.HTTPException(status_code=401, detail="Not Authenticated")
  try:
    decrypted_payload = security.decrypt_token(encrypted_token)
    return json.loads(decrypted_payload)
  except Exception as e:
    logger.error("Session validation failed: %s", e)
    raise fastapi.HTTPException(
        status_code=401, detail="Invalid Session"
    ) from e


def _initialize_ads_client(
    session_data: Dict[str, Any], login_customer_id: int | None = None
) -> client.GoogleAdsClient:
  """Initializes GoogleAdsClient using a refresh token from a session.

  Args:
      session_data (Dict): The decrypted session payload containing the user's
        refresh token.
      login_customer_id (int | None): Optional Google Ads Customer ID to use as
        the `login-customer-id` header. Defines the operating context, allowing
        the app to act on behalf of an MCC or a direct sub-account.

  Returns:
      client.GoogleAdsClient: An authenticated Google Ads API client.
  """
  refresh_token = session_data.get("rt")
  if not refresh_token:
    logger.error("Session data missing refresh token.")
    raise fastapi.HTTPException(
        status_code=401, detail="Invalid Session Structure"
    )
  try:
    configuration_dictionary = {
        "developer_token": config.settings.GOOGLE_ADS_DEVELOPER_TOKEN,
        "client_id": config.settings.GOOGLE_CLIENT_ID,
        "client_secret": config.settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }
    if login_customer_id:
      configuration_dictionary["login_customer_id"] = str(login_customer_id)

    return client.GoogleAdsClient.load_from_dict(configuration_dictionary)
  except Exception as e:
    logger.error("Google Ads Client initialization failed: %s", e)
    raise fastapi.HTTPException(
        status_code=500, detail="Service Configuration Error"
    ) from e


def get_google_ads_service(
    session_data: Annotated[Dict[str, Any], fastapi.Depends(get_session_data)],
    login_customer_id: Annotated[int | None, fastapi.Query()] = None,
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
  target_id = login_customer_id or config.settings.GOOGLE_ADS_CUSTOMER_ID
  if not target_id:
    logger.error("Google Ads Customer ID is not provided or configured.")
    raise fastapi.HTTPException(
        status_code=500, detail="Google Ads configuration error."
    )

  try:
    logger.info("Initializing Ads Service for CID: %s", target_id)
    google_ads_client = _initialize_ads_client(session_data, target_id)
    return google_ads.GoogleAdsService(
        google_ads_client, login_customer_id=target_id
    )
  except Exception as e:
    logger.error("Unexpected error during Ads Service initialization: %s", e)
    raise fastapi.HTTPException(
        status_code=500, detail="Ads Service failure"
    ) from e


def get_discovery_service(
    session_data: Annotated[Dict[str, Any], fastapi.Depends(get_session_data)],
) -> google_ads.GoogleAdsService:
  """Dependency for account discovery (initializes client WITHOUT a context)."""
  try:
    logger.info("Initializing Ads Discovery Service (No Context)")
    google_ads_client = _initialize_ads_client(session_data)
    return google_ads.GoogleAdsService(google_ads_client)
  except Exception as e:
    logger.error("Discovery Service failure: %s", e)
    raise fastapi.HTTPException(
        status_code=500, detail="Discovery failure"
    ) from e


@functools.lru_cache()
def get_firestore_service() -> firestore_service.FirestoreService:
  """Creates and caches a singleton instance of the FirestoreService.

  Returns:
    firestore_service.FirestoreService: A FirestoreService instance.
  """
  return firestore_service.FirestoreService(
      project_id=config.settings.PROJECT_ID,
      database_id=config.settings.FIRESTORE_DATABASE,
  )
