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
from typing import Any, Callable, Dict, List

from google.ads.googleads.client import GoogleAdsClient  # type: ignore
from google.ads.googleads.errors import GoogleAdsException  # type: ignore

logger = logging.getLogger(__name__)


class GoogleAdsService:
  """Service class to execute reporting queries against Google Ads API.

  Abstracts GAQL complexities from the controller/route layer.
  """

  def __init__(self, client: GoogleAdsClient, customer_id: str):
    # Sanitize ID immediately upon service instantiation.
    self.customer_id = customer_id.replace("-", "")
    self.client = client
    self.ga_service = client.get_service("GoogleAdsService")
    logger.debug("Service initialized for Customer ID: '%s'.", self.customer_id)

  def get_campaigns(self) -> List[Dict[str, Any]]:
    """Fetches a list of all non-removed campaigns.

    Returns:
      A list of campaign dictionaries.
    """
    logger.info("Fetching campaigns for customer '%s'.", self.customer_id)
    query = (
        "SELECT campaign.id, campaign.name, campaign.status, "
        "campaign.advertising_channel_type "
        "FROM campaign "
        "WHERE campaign.status != 'REMOVED' "
        "ORDER BY campaign.id DESC"
    )
    return self._execute_query(query, self._map_campaign)

  def get_ad_groups(self, campaign_id: str) -> List[Dict[str, Any]]:
    """Fetches Ad Groups for a specific Campaign.

    Args:
      campaign_id: The campaign ID to fetch ad groups for.

    Returns:
      A list of ad group dictionaries.
    """
    logger.info(
        "Fetching ad groups for campaign '%s' (Customer: '%s').",
        campaign_id,
        self.customer_id,
    )
    query = (
        "SELECT ad_group.id, ad_group.name, ad_group.status, campaign.id "
        "FROM ad_group "
        f"WHERE campaign.id = {campaign_id} "
        "AND ad_group.status != 'REMOVED'"
    )
    results = self._execute_query(query, self._map_ad_group)
    for result in results:
      result["customer_id"] = self.customer_id
    return results

  # --- Internal Helpers ---

  def _execute_query(
      self, query: str, mapper_func: Callable[[Any], Dict[str, Any]]
  ) -> List[Dict[str, Any]]:
    """Executes a GAQL search stream and maps results using the provided mapper.

    Args:
      query: The GAQL query string.
      mapper_func: Function to transform a row into a dictionary.

    Returns:
      The list of transformed results.
    """
    try:
      logger.debug("Executing GAQL Query: '%s'", query)
      stream = self.ga_service.search_stream(
          customer_id=self.customer_id, query=query
      )
      results = []
      for batch in stream:
        for row in batch.results:
          results.append(mapper_func(row))
      logger.info(
          "Query executed successfully. Retrieved '%d' rows.", len(results)
      )
      return results
    except GoogleAdsException:
      logger.exception("Google Ads API Error for %s", self.customer_id)
      # Re-raise the original exception so reports.py can catch it and send it
      # to frontend.
      raise
    except Exception:
      logger.exception("Unexpected error executing GAQL query.")
      raise

  # --- Mappers ---

  @staticmethod
  def _map_campaign(row: Any) -> Dict[str, Any]:
    return {
        "id": str(row.campaign.id),
        "name": row.campaign.name,
        "status": row.campaign.status.name,
        "type": row.campaign.advertising_channel_type.name,
    }

  @staticmethod
  def _map_ad_group(row: Any) -> Dict[str, Any]:
    return {
        "id": str(row.ad_group.id),
        "name": row.ad_group.name,
        "status": row.ad_group.status.name,
        "campaign_id": str(row.campaign.id),
    }
