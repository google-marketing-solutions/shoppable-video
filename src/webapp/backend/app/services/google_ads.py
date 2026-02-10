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

  def get_rsa_ads(self) -> List[Dict[str, Any]]:
    """Fetches Responsive Search Ads.

    Returns:
      A list of RSA ad dictionaries.
    """
    logger.info("Fetching RSA ads for customer '%s'.", self.customer_id)
    query = (
        "SELECT ad_group.name, ad_group_ad.status, "
        "ad_group_ad.ad.responsive_search_ad.headlines "
        "FROM ad_group_ad "
        "WHERE ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD' "
        "AND ad_group_ad.status != 'REMOVED' "
        "LIMIT 50"
    )
    return self._execute_query(query, self._map_rsa)

  def get_disapproved_ads(self) -> List[Dict[str, Any]]:
    """Fetches Disapproved Ads and their policy topics.

    Returns:
      A list of disapproved ads with reasons.
    """
    logger.info("Fetching disapproved ads for customer '%s'.", self.customer_id)
    query = (
        "SELECT ad_group_ad.ad.id, ad_group.name, "
        "ad_group_ad.policy_summary.review_status, "
        "ad_group_ad.policy_summary.approval_status, "
        "ad_group_ad.policy_summary.policy_topic_entries "
        "FROM ad_group_ad "
        "WHERE ad_group_ad.policy_summary.approval_status = 'DISAPPROVED' "
        "LIMIT 50"
    )
    return self._execute_query(query, self._map_disapproved)

  def get_categories(self) -> List[Dict[str, Any]]:
    """Fetches Constant Categories (Language Constants).

    Returns:
      A list of language constants.
    """
    logger.info("Fetching categories for customer '%s'.", self.customer_id)
    query = (
        "SELECT language_constant.id, language_constant.name, "
        "language_constant.code "
        "FROM language_constant "
        "WHERE language_constant.targetable = TRUE "
        "LIMIT 20"
    )
    return self._execute_query(query, self._map_category)

  def get_ad_group_cpc_bid(self, ad_group_id: str, campaign_id: str) -> int:
    """Fetches the Default Max CPC bid (micros) for a specific Ad Group.

    Args:
        ad_group_id: The ID of the ad group to fetch the CPC bid for.
        campaign_id: The ID of the campaign the ad group belongs to.

    Returns:
        The cpc_bid_micros value (int). Returns 0 if not found or not set.
    """
    logger.info(
        "Fetching CPC bid for Ad Group '%s' in Campaign '%s' (Customer '%s').",
        ad_group_id,
        campaign_id,
        self.customer_id,
    )
    query = (
        "SELECT ad_group.cpc_bid_micros "
        "FROM ad_group "
        f"WHERE ad_group.id = {ad_group_id} "
        f"AND campaign.id = {campaign_id}"
    )
    results = self._execute_query(
        query, lambda row: {"cpc_bid_micros": row.ad_group.cpc_bid_micros}
    )

    if not results:
      logger.warning("Ad Group '%s' not found or has no CPC bid.", ad_group_id)
      return 0

    return results[0].get("cpc_bid_micros", 0)

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
  def _map_rsa(row: Any) -> Dict[str, Any]:
    ad = row.ad_group_ad.ad.responsive_search_ad
    return {
        "ad_group": row.ad_group.name,
        "status": row.ad_group_ad.status.name,
        "headlines": [h.text for h in ad.headlines],
    }

  @staticmethod
  def _map_disapproved(row: Any) -> Dict[str, Any]:
    policy_summary = row.ad_group_ad.policy_summary
    reason = "Unknown"
    if policy_summary.policy_topic_entries:
      reason = policy_summary.policy_topic_entries[0].topic

    return {
        "ad_id": str(row.ad_group_ad.ad.id),
        "ad_group": row.ad_group.name,
        "review_status": policy_summary.review_status.name,
        "approval_status": policy_summary.approval_status.name,
        "reason": reason,
    }

  @staticmethod
  def _map_category(row: Any) -> Dict[str, Any]:
    return {
        "id": str(row.language_constant.id),
        "name": row.language_constant.name,
    }
