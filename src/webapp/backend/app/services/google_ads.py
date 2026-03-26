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

"""Service layer for Google Ads API interactions."""

import logging
from typing import Any, Callable, Dict, List, Optional

from google.ads.googleads.client import GoogleAdsClient  # type: ignore
from google.ads.googleads.errors import GoogleAdsException  # type: ignore

logger = logging.getLogger(__name__)


class GoogleAdsService:
  """Service class to execute reporting queries against Google Ads API.

  Abstracts GAQL complexities from the controller/route layer.
  """

  def __init__(
      self, client: GoogleAdsClient, login_customer_id: Optional[int] = None
  ):
    self.login_customer_id = login_customer_id
    self.client = client
    self.ga_service = client.get_service("GoogleAdsService")
    logger.debug(
        "Service initialized with login-customer-id: '%s'.",
        self.login_customer_id,
    )

  def list_accessible_customers(self) -> List[str]:
    """Lists all customer resource names directly accessible by the token.

    This uses CustomerService.list_accessible_customers and does NOT
    require a starting customer_id context.

    Returns:
      A list of resource names (e.g. ["customers/123", "customers/456"]).
    """
    logger.info("Listing globally accessible customers for the current token.")
    customer_service = self.client.get_service("CustomerService")
    try:
      response = customer_service.list_accessible_customers()
      return list(response.resource_names)
    except GoogleAdsException:
      logger.exception("Failed to list accessible customers.")
      raise

  def list_accessible_subaccounts(
      self, customer_id: Optional[int] = None
  ) -> List[Dict[str, Any]]:
    """Lists all sub-accounts (CIDs) under the provided customer ID.

    Args:
      customer_id: Optional customer ID to list sub-accounts for. Defaults to
        the service's login_customer_id.

    Returns:
      A list of dictionaries with customer metadata.
    """
    logger.info("Listing accessible sub-accounts.")
    query = (
        "SELECT customer_client.id, "
        "customer_client.descriptive_name, "
        "customer_client.level, "
        "customer_client.manager "
        "FROM customer_client "
        "WHERE customer_client.level > 0"
    )
    return self._execute_query(
        query, self._map_customer_client, customer_id=customer_id
    )

  def get_customer_details(self, customer_id: int) -> Dict[str, Any]:
    """Fetches descriptive name and manager status for a specific customer ID.

    Args:
      customer_id: The customer ID to query (e.g., 1234567890).

    Returns:
      A dict with customer metadata, or empty dict if not found/accessible.
    """
    logger.info("Fetching details for customer '%s'.", customer_id)
    query = (
        "SELECT customer.id, "
        "customer.descriptive_name, "
        "customer.manager "
        "FROM customer "
        "LIMIT 1"
    )

    try:
      results = self._execute_query(
          query, self._map_customer_details, customer_id=customer_id
      )
      return results[0] if results else {}
    except Exception as e:  # pylint: disable=broad-except
      logger.warning("Could not fetch details for %s: %s", customer_id, e)
      return {}

  def get_campaigns(
      self, customer_id: Optional[int] = None
  ) -> List[Dict[str, Any]]:
    """Fetches a list of all non-removed campaigns.

    Args:
      customer_id: Optional target customer ID to query. Defaults to the
        service's login_customer_id.

    Returns:
      A list of campaign dictionaries.
    """
    logger.info("Fetching campaigns for customer context.")
    query = (
        "SELECT customer.id, campaign.id, campaign.name, campaign.status, "
        "campaign.advertising_channel_type "
        "FROM campaign "
        "WHERE campaign.status != 'REMOVED' "
        "ORDER BY campaign.id DESC"
    )
    return self._execute_query(
        query, self._map_campaign, customer_id=customer_id
    )

  def get_ad_groups(
      self, campaign_id: int, customer_id: Optional[int] = None
  ) -> List[Dict[str, Any]]:
    """Fetches Ad Groups for a specific Campaign.

    Args:
      campaign_id: The campaign ID to fetch ad groups for.
      customer_id: Optional target customer ID to query. Defaults to the
        service's login_customer_id.

    Returns:
      A list of ad group dictionaries.
    """
    logger.info("Fetching ad groups for campaign '%s'.", campaign_id)
    query = (
        "SELECT customer.id, ad_group.id, ad_group.name, ad_group.status, "
        "campaign.id "
        "FROM ad_group "
        f"WHERE campaign.id = {campaign_id} "
        "AND ad_group.status != 'REMOVED'"
    )
    return self._execute_query(
        query, self._map_ad_group, customer_id=customer_id
    )

  def _execute_query(
      self,
      query: str,
      mapper_func: Callable[[Any], Dict[str, Any]],
      customer_id: Optional[int] = None,
  ) -> List[Dict[str, Any]]:
    """Executes a GAQL search stream using the provided or default customer ID.

    Args:
      query: The GAQL query string.
      mapper_func: Function to transform a row into a dictionary.
      customer_id: Optional target customer ID. Defaults to login_customer_id.

    Returns:
      The list of transformed results.
    """
    target_id = str(customer_id or self.login_customer_id)
    try:
      logger.debug("Executing GAQL Query for '%s': '%s'", target_id, query)
      stream = self.ga_service.search_stream(customer_id=target_id, query=query)
      results = []
      for batch in stream:
        for row in batch.results:
          results.append(mapper_func(row))
      logger.info(
          "Query executed successfully for '%s'. Retrieved '%d' rows.",
          target_id,
          len(results),
      )
      return results
    except GoogleAdsException:
      logger.exception("Google Ads API Error for %s", target_id)
      raise
    except Exception:
      logger.exception("Unexpected error executing GAQL query.")
      raise

  # --- Mappers ---

  @staticmethod
  def _map_campaign(row: Any) -> Dict[str, Any]:
    return {
        "customer_id": int(row.customer.id),
        "id": int(row.campaign.id),
        "name": row.campaign.name,
        "status": row.campaign.status.name,
        "type": row.campaign.advertising_channel_type.name,
    }

  @staticmethod
  def _map_ad_group(row: Any) -> Dict[str, Any]:
    return {
        "customer_id": int(row.customer.id),
        "id": int(row.ad_group.id),
        "name": row.ad_group.name,
        "status": row.ad_group.status.name,
        "campaign_id": int(row.campaign.id),
    }

  @staticmethod
  def _map_customer_client(row: Any) -> Dict[str, Any]:
    return {
        "customer_id": int(row.customer_client.id),
        "descriptive_name": row.customer_client.descriptive_name,
        "is_manager": row.customer_client.manager,
        "level": row.customer_client.level,
    }

  @staticmethod
  def _map_customer_details(row: Any) -> Dict[str, Any]:
    return {
        "customer_id": int(row.customer.id),
        "descriptive_name": row.customer.descriptive_name,
        "is_manager": row.customer.manager,
    }
