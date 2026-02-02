"""Service for interacting with the Google Ads API.

This module provides the AdsService class, which handles interactions with the
Google Ads API, including fetching ad groups, managing listing groups, and
updating ad criteria.
"""

import logging
import os
from typing import List, Optional, Set, Tuple

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logger = logging.getLogger(__name__)


class AdsService:
  """Handles interactions with the Google Ads API."""

  def __init__(self):
    """Initializes the AdsService with a GoogleAdsClient.

    Raises:
      Exception: If the Google Ads client cannot be loaded from the environment.
      ValueError: If the GOOGLE_ADS_CUSTOMER_ID environment variable is not set.
    """
    try:
      client_config = {
          "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
          "client_id": os.getenv("GOOGLE_CLIENT_ID"),
          "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
          "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
          "login_customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
          "use_proto_plus": (
              os.getenv("GOOGLE_ADS_USE_PROTO_PLUS", "true").lower() == "true"
          ),
      }
      logger.info(
          "Initializing Google Ads client with config keys: %s",
          list(client_config.keys())
      )
      self.client = GoogleAdsClient.load_from_dict(client_config)

    except (ValueError, TypeError) as e:
      logger.warning(
          "Failed to load Google Ads client from dict, trying env/yaml: %s", e
      )
      try:
        self.client = GoogleAdsClient.load_from_env()
      except Exception as env_e:
        logger.error("Failed to load Google Ads client from env: %s", env_e)
        raise env_e

    self.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
    if not self.customer_id:
      raise ValueError("GOOGLE_ADS_CUSTOMER_ID environment variable is not set")

  def get_listing_group_root(
      self, ad_group_id: int, customer_id: Optional[str] = None
  ) -> Tuple[Optional[str], Optional[int]]:
    """Finds the resource name and type of root listing group node for ad group.

    Args:
      ad_group_id: The ID of the ad group.
      customer_id: Optional customer ID override.

    Returns:
      A tuple containing (resource_name, listing_group_type).
      Returns (None, None) if no root listing group is found.
    """
    cid = customer_id or self.customer_id
    ga_service = self.client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            ad_group_criterion.resource_name,
            ad_group_criterion.listing_group.type,
            ad_group_criterion.listing_group.parent_ad_group_criterion
        FROM ad_group_criterion
        WHERE
            ad_group.id = {ad_group_id}
            AND ad_group_criterion.type = 'LISTING_GROUP'
            AND ad_group_criterion.listing_group.parent_ad_group_criterion IS NULL
    """

    response = ga_service.search(customer_id=cid, query=query)
    for row in response:
      return (
          row.ad_group_criterion.resource_name,
          row.ad_group_criterion.listing_group.type_
      )

    return (None, None)

  def get_existing_offers(
      self, ad_group_id: int, parent_resource_name: str,
      customer_id: Optional[str] = None
  ) -> Set[str]:
    """Fetches the set of product offer IDs that are already children of the given parent node.

    Args:
      ad_group_id: The ID of the ad group.
      parent_resource_name: The resource name of the parent listing group.
      customer_id: Optional customer ID override.

    Returns:
      A set of existing offer IDs.
    """
    cid = customer_id or self.customer_id
    ga_service = self.client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            ad_group_criterion.listing_group.case_value.product_item_id.value
        FROM ad_group_criterion
        WHERE
            ad_group.id = {ad_group_id}
            AND ad_group_criterion.type = 'LISTING_GROUP'
            AND ad_group_criterion.listing_group.parent_ad_group_criterion = '{parent_resource_name}'
    """

    existing_offers = set()
    response = ga_service.search(customer_id=cid, query=query)
    for row in response:
      case_value = row.ad_group_criterion.listing_group.case_value
      if (case_value and "product_item_id" in case_value and
          case_value.product_item_id.value):
        existing_offers.add(case_value.product_item_id.value)

    return existing_offers

  def _handle_root_node(
      self,
      ad_group_id: int,
      root_resource_name: Optional[str],
      root_type: Optional[int],
      cpc_bid_micros: int,
      customer_id: str,
  ) -> Tuple[Optional[str], List[object], bool]:
    """Handles the root listing group node logic.

    Args:
      ad_group_id: The ID of the ad group.
      root_resource_name: The resource name of the existing root, if any.
      root_type: The type of the existing root, if any.
      cpc_bid_micros: The CPC bid in micros.
      customer_id: The customer ID.

    Returns:
      A tuple of (effective_root_resource_name, operations, is_new_root).
    """
    operations = []
    effective_root_resource_name = root_resource_name
    is_new_root = False

    if (not root_resource_name or
        root_type == self.client.enums.ListingGroupTypeEnum.UNIT):

      is_new_root = True

      if root_resource_name:
        logger.info("Root listing group is UNIT. Recreating as SUBDIVISION.")
        op_remove = self.client.get_type("AdGroupCriterionOperation")
        op_remove.remove = root_resource_name
        operations.append(op_remove)
      else:
        logger.info("No root listing group found for Ad Group %s. "
                    "Creating new root as SUBDIVISION.", ad_group_id)

      ad_group_criterion_service = self.client.get_service(
          "AdGroupCriterionService"
      )
      temp_root_id = -1
      effective_root_resource_name = (
          ad_group_criterion_service.ad_group_criterion_path(
              customer_id, str(ad_group_id), str(temp_root_id)
          )
      )

      op_root = self.client.get_type("AdGroupCriterionOperation")
      crit_root = op_root.create
      crit_root.resource_name = effective_root_resource_name
      crit_root.ad_group = self.client.get_service(
          "AdGroupService"
      ).ad_group_path(customer_id, ad_group_id)
      crit_root.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
      crit_root.listing_group.type = (
          self.client.enums.ListingGroupTypeEnum.SUBDIVISION)
      operations.append(op_root)

      op_other = self.client.get_type("AdGroupCriterionOperation")
      criterion_other = op_other.create
      criterion_other.ad_group = self.client.get_service(
          "AdGroupService"
      ).ad_group_path(customer_id, ad_group_id)
      criterion_other.status = (
          self.client.enums.AdGroupCriterionStatusEnum.ENABLED)
      criterion_other.listing_group.type = (
          self.client.enums.ListingGroupTypeEnum.UNIT
      )
      criterion_other.listing_group.parent_ad_group_criterion = (
          effective_root_resource_name
      )
      criterion_other.listing_group.case_value.product_item_id = (
          self.client.get_type("ProductItemIdInfo")
      )
      criterion_other.cpc_bid_micros = cpc_bid_micros
      operations.append(op_other)

    return effective_root_resource_name, operations, is_new_root

  def _create_offer_operation(
      self,
      ad_group_id: int,
      offer_id: str,
      root_resource_name: str,
      cpc_bid_micros: int,
      customer_id: str,
  ) -> object:
    """Creates an operation to add an offer to the ad group."""
    operation = self.client.get_type("AdGroupCriterionOperation")
    criterion = operation.create
    criterion.ad_group = self.client.get_service(
        "AdGroupService"
    ).ad_group_path(customer_id, ad_group_id)
    criterion.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
    criterion.cpc_bid_micros = cpc_bid_micros

    listing_group = criterion.listing_group
    listing_group.type = self.client.enums.ListingGroupTypeEnum.UNIT
    listing_group.parent_ad_group_criterion = root_resource_name

    case_value = listing_group.case_value
    case_value.product_item_id.value = offer_id

    return operation

  def add_offers_to_ad_group(
      self, ad_group_id: int, offer_ids: List[str],
      customer_id: Optional[str] = None,
      cpc_bid_micros: Optional[int] = None
  ):
    """Adds the given offer IDs as unit nodes to the root listing group of the ad group.

    If the root listing group is a UNIT, it will be removed and recreated as a
    SUBDIVISION.

    Args:
      ad_group_id: The ID of the target ad group.
      offer_ids: A list of product offer IDs to add.
      customer_id: Optional customer ID override.
      cpc_bid_micros: Optional CPC bid in micros. Defaults to 10000 (0.01
        currency units) if not provided.

    Raises:
      GoogleAdsException: If the API request fails.
    """
    cid = customer_id or self.customer_id
    effective_cpc_bid_micros = (
        cpc_bid_micros if cpc_bid_micros is not None else 10000
    )

    root_resource_name, root_type = self.get_listing_group_root(
        ad_group_id, cid
    )
    logger.debug("Root resource: %s, Type: %s", root_resource_name, root_type)

    effective_root, root_ops, is_new_root = self._handle_root_node(
        ad_group_id,
        root_resource_name,
        root_type,
        effective_cpc_bid_micros,
        cid,
    )

    operations = list(root_ops)

    if is_new_root:
      existing_offers = set()
    else:
      existing_offers = self.get_existing_offers(
          ad_group_id, effective_root, cid
      )
      logger.info("Found %d existing offers in Ad Group %s",
                  len(existing_offers), ad_group_id)

    offer_ids = list(set(offer_ids))

    for offer_id in offer_ids:
      if offer_id in existing_offers:
        logger.debug("Offer %s already exists in Ad Group %s, skipping.",
                     offer_id, ad_group_id)
        continue

      operations.append(self._create_offer_operation(
          ad_group_id, offer_id, effective_root, effective_cpc_bid_micros, cid
      ))

    if not operations:
      logger.info("No offers to add for Ad Group %s", ad_group_id)
      return

    ad_group_criterion_service = self.client.get_service(
        "AdGroupCriterionService"
    )
    try:
      response = ad_group_criterion_service.mutate_ad_group_criteria(
          customer_id=cid, operations=operations
      )
      logger.info("Successfully mutated %d criteria for Ad Group %s",
                  len(response.results), ad_group_id)
    except GoogleAdsException as ex:
      logger.error(
          "Request with ID '%s' failed with status '%s' and includes the "
          "following errors:",
          ex.request_id, ex.error.code().name
      )
      for error in ex.failure.errors:
        logger.error("\tError with message '%s'.", error.message)
        if error.location:
          for field_path_element in error.location.field_path_elements:
            logger.error("\t\tOn field: %s", field_path_element.field_name)
      raise
