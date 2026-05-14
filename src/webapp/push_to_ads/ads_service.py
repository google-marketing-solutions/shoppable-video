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

"""Interacts with Google Ads to manage listing group structures."""

from __future__ import annotations
import logging
from typing import List, Optional, Set, Tuple

from google.ads.googleads import client
from google.ads.googleads.v22.services.types import ad_group_criterion_service as agc_service_types
import google.auth
import models
import utils

logger = logging.getLogger(__name__)


class AdsService:
  """Interacts with the Google Ads API to manage product listing groups.

  Attributes:
    customer_id: The active Google Ads customer account ID string.
    client: The underlying Google Ads API client wrapper.
  """

  def __init__(
      self,
      customer_id: str,
      developer_token: Optional[str] = None,
  ):
    """Initializes the Google Ads API client.

    Args:
      customer_id: The Google Ads Customer ID.
      developer_token: The optional developer token.

    Raises:
      ValueError: If customer_id is empty.
    """
    if not customer_id:
      raise ValueError("customer_id must be provided to initialize AdsService")
    self.customer_id = utils.normalize_customer_id(customer_id)

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/adwords"]
    )
    self.client = client.GoogleAdsClient(
        credentials=credentials,
        developer_token=developer_token,
        login_customer_id=self.customer_id,
        use_proto_plus=True,
    )

  def add_offers_to_ad_group(
      self,
      ad_group_id: int,
      campaign_id: int,
      target_products: List[str],
      customer_id: Optional[str] = None,
      strategy: models.ListingGroupStrategy = (
          models.ListingGroupStrategy.PRESERVE
      ),
  ) -> models.AdsMutationResult:
    """Adds product items to a specific Google Ads Ad Group.

    Args:
      ad_group_id: Unique identifier for the target Ad Group.
      campaign_id: Parent Campaign identifier.
      target_products: List of item ID strings.
      customer_id: Optional client account ID override.
      strategy: The desired update strategy.

    Returns:
      Final operation result tracking overall success status.
    """
    effective_customer_id = (
        utils.normalize_customer_id(customer_id)
        if customer_id
        else self.customer_id
    )
    ad_group_id = int(ad_group_id)
    products = []
    error_message = None

    try:
      # 1. Recon current flat state
      root = self._get_listing_group_root(ad_group_id, effective_customer_id)

      # 2. Dispatch flat generation
      operations, early_results, added_offer_ids = self._generate_operations(
          ad_group_id, root, target_products, strategy, effective_customer_id
      )
      products.extend(early_results)

      if not operations:
        return models.AdsMutationResult(
            ad_group_id=ad_group_id,
            campaign_id=campaign_id,
            customer_id=effective_customer_id,
            products=products,
            error_message=None,
        )

      if len(operations) > 10000:
        raise RuntimeError(
            "Payload overflows Google Ads API transactional thresholds."
        )

      ad_group_criterion_service = self.client.get_service(
          "AdGroupCriterionService"
      )
      ad_group_criterion_service.mutate_ad_group_criteria(
          customer_id=effective_customer_id, operations=operations
      )

      for offer_id in added_offer_ids:
        products.append(
            models.ProductResult(
                offer_id=offer_id, status=models.AdGroupInsertionStatus.SUCCESS
            )
        )

    except Exception as e:  # pylint: disable=broad-exception-caught
      logger.exception("Exception executing atomic simplified mutation chain.")
      error_message = utils.extract_error_message(e)
      self._mark_unhandled_offers_failed(products, target_products)

    return models.AdsMutationResult(
        ad_group_id=ad_group_id,
        campaign_id=campaign_id,
        customer_id=effective_customer_id,
        products=products,
        error_message=error_message,
    )

  def _get_listing_group_root(
      self, ad_group_id: int, customer_id: str
  ) -> Optional[models.ListingNode]:
    """Retrieves root node and connects immediate partitioned children.

    Args:
      ad_group_id: ID of the targeted Ad Group.
      customer_id: The customer account ID.

    Returns:
      The discovered root node or None if empty.
    """
    ga_service = self.client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            ad_group_criterion.resource_name,
            ad_group_criterion.listing_group.type,
            ad_group_criterion.listing_group.parent_ad_group_criterion,
            ad_group_criterion.listing_group.case_value.product_item_id.value,
            ad_group_criterion.negative
        FROM ad_group_criterion
        WHERE
            ad_group.id = {int(ad_group_id)}
            AND ad_group_criterion.type = 'LISTING_GROUP'
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    root_node = None
    children = []

    for row in response:
      c = row.ad_group_criterion
      node = models.ListingNode(
          resource_name=c.resource_name,
          node_type=c.listing_group.type_,
          parent_resource_name=c.listing_group.parent_ad_group_criterion,
          case_value=c.listing_group.case_value,
          is_negative=c.negative,
          children=[],
      )
      if not node.parent_resource_name:
        root_node = node
      else:
        children.append(node)

    if root_node:
      root_node.children = [
          child
          for child in children
          if child.parent_resource_name == root_node.resource_name
      ]
      for child in root_node.children:
        if child.case_value and "product_item_id" in child.case_value:
          root_node.partition_dimension = "product_item_id"
          break

    return root_node

  def _generate_operations(
      self,
      ad_group_id: int,
      root: Optional[models.ListingNode],
      target_products: List[str],
      strategy: models.ListingGroupStrategy,
      customer_id: str,
  ) -> Tuple[
      List[agc_service_types.AdGroupCriterionOperation],
      List[models.ProductResult],
      List[str],
  ]:
    """Generates the final list of API operations based on current tree state.

    Args:
      ad_group_id: The target Ad Group ID.
      root: The root node or None.
      target_products: List of item IDs.
      strategy: The update strategy (PURGE or PRESERVE).
      customer_id: The account ID.

    Returns:
      A tuple containing:
      - List of final API operations.
      - List of initial processed product results.
      - List of successfully added offer IDs.

    Raises:
      ValueError: If user tries to PRESERVE a non-item tree structure.
    """
    ad_group_service = self.client.get_service("AdGroupService")
    ad_group_path = ad_group_service.ad_group_path(customer_id, ad_group_id)
    early_results = []
    operations = []

    tree_state = self._evaluate_tree_state(root)

    # Handler Branch 1: Purge or Clean Tree
    if (
        strategy == models.ListingGroupStrategy.PURGE
        or tree_state == models.TreeState.CLEAN
    ):
      if root:
        remove_operation = self.client.get_type("AdGroupCriterionOperation")
        remove_operation.remove = root.resource_name
        operations.append(remove_operation)
      bootstrap_operations, added_offer_ids = self._generate_bootstrap_ops(
          ad_group_path,
          target_products,
          customer_id,
          ad_group_id,
          early_results,
      )
      return operations + bootstrap_operations, early_results, added_offer_ids

    # Handler Branch 2: Preserve Execution
    if tree_state == models.TreeState.PARTITIONED:
      # Clean subdivision keyed by item ID. Perform appends only.
      assert root is not None
      append_operations, added_offer_ids = self._generate_append_ops(
          root, target_products, ad_group_path, early_results
      )
      return append_operations, early_results, added_offer_ids

    else:
      assert root is not None
      raise ValueError(
          "Cannot perform PRESERVE synchronization: The targeted tree is"
          f" already partitioned by '{root.partition_dimension}'. Flat Item ID"
          " insertion is forbidden on non-item hierarchies. Try Strategy:"
          " PURGE."
      )

  def _mark_unhandled_offers_failed(
      self, products_list: List[models.ProductResult], offer_ids: List[str]
  ) -> None:
    """Appends failure results for any requested offers that weren't handled.

    Args:
      products_list: Accumulator list of individual product result items.
      offer_ids: Full list of required items.
    """
    processed = {p.offer_id for p in products_list}
    for offer_id in offer_ids:
      if offer_id not in processed:
        products_list.append(
            models.ProductResult(
                offer_id=offer_id, status=models.AdGroupInsertionStatus.FAILED
            )
        )

  def _evaluate_tree_state(
      self, root: Optional[models.ListingNode]
  ) -> models.TreeState:
    """Evaluates whether the tree needs to be rebuilt or can be appended to.

    Args:
      root: The root node of the tree.

    Returns:
      The state enum (e.g. TreeState.CLEAN, TreeState.DIRTY).
    """
    google_ads_enums = self.client.enums
    if not root or root.node_type == google_ads_enums.ListingGroupTypeEnum.UNIT:
      return models.TreeState.CLEAN
    if root.node_type == google_ads_enums.ListingGroupTypeEnum.SUBDIVISION:
      if root.partition_dimension == "product_item_id":
        return models.TreeState.PARTITIONED
      return models.TreeState.DIRTY
    return models.TreeState.DIRTY

  def _generate_bootstrap_ops(
      self,
      ad_group_path: str,
      target_products: List[str],
      customer_id: str,
      ad_group_id: int,
      early_results: List[models.ProductResult],
  ) -> Tuple[List[agc_service_types.AdGroupCriterionOperation], List[str]]:
    """Generates API operations to construct a tree subdivided by product ID.

    Args:
      ad_group_path: API path of the Ad Group.
      target_products: The list of item IDs.
      customer_id: The customer account ID.
      ad_group_id: The Ad Group ID.
      early_results: List that accumulates processing status results.

    Returns:
      A tuple containing:
      - List of creation operations.
      - List of offer IDs that will be created.
    """
    google_ads_enums = self.client.enums
    ad_group_criterion_service = self.client.get_service(
        "AdGroupCriterionService"
    )
    temp_resource_id = ad_group_criterion_service.ad_group_criterion_path(
        customer_id, str(ad_group_id), "-1"
    )

    creation_operations = []

    # 1. Create the Root Subdivision
    root_operation = self.client.get_type("AdGroupCriterionOperation")
    root_operation.create = {
        "resource_name": temp_resource_id,
        "ad_group": ad_group_path,
        "status": google_ads_enums.AdGroupCriterionStatusEnum.ENABLED,
        "listing_group": {
            "type_": google_ads_enums.ListingGroupTypeEnum.SUBDIVISION
        },
    }
    creation_operations.append(root_operation)

    # 2. Create standard catch-all
    other_operation = self.client.get_type("AdGroupCriterionOperation")
    other_operation.create = {
        "ad_group": ad_group_path,
        "negative": True,
        "listing_group": {
            "type_": google_ads_enums.ListingGroupTypeEnum.UNIT,
            "parent_ad_group_criterion": temp_resource_id,
            "case_value": {"product_item_id": {}},
        },
    }
    creation_operations.append(other_operation)

    # 3. Create Flat Product Units
    product_operations, offers_to_add = (
        self._build_product_criterion_operations(
            target_products, temp_resource_id, ad_group_path, early_results
        )
    )
    creation_operations.extend(product_operations)

    return creation_operations, offers_to_add

  def _generate_append_ops(
      self,
      root: models.ListingNode,
      target_products: List[str],
      ad_group_path: str,
      early_results: List[models.ProductResult],
  ) -> Tuple[List[agc_service_types.AdGroupCriterionOperation], List[str]]:
    """Generates operations to insert products into an existing item partition.

    Args:
      root: The existing partition root node.
      target_products: The list of item IDs.
      ad_group_path: API path of the Ad Group.
      early_results: List for collecting status on existing duplicate items.

    Returns:
      A tuple containing:
      - List of creation operations.
      - List of new offer IDs being added.
    """
    existing_item_ids = set()
    for child in root.children:
      if child.case_value and "product_item_id" in child.case_value:
        current_item_id = child.case_value.product_item_id.value
        if current_item_id:
          existing_item_ids.add(str(current_item_id))

    return self._build_product_criterion_operations(
        target_products,
        root.resource_name,
        ad_group_path,
        early_results,
        existing_item_ids,
    )

  def _build_product_criterion_operations(
      self,
      target_products: List[str],
      parent_resource_name: str,
      ad_group_path: str,
      early_results: List[models.ProductResult],
      existing_item_ids: Optional[Set[str]] = None,
  ) -> Tuple[List[agc_service_types.AdGroupCriterionOperation], List[str]]:
    """Builds unit criteria operations for flat target products.

    Args:
      target_products: Item IDs to generate operations for.
      parent_resource_name: Parent subdivision resource name.
      ad_group_path: API path of the Ad Group.
      early_results: Result accumulator for duplicate/seen cases.
      existing_item_ids: Existing items in partition to avoid duplicates.

    Returns:
      A tuple containing operations to create and offer IDs.
    """
    google_ads_enums = self.client.enums
    creation_operations = []
    offers_to_add = []

    seen_ids = set()
    existing_set = existing_item_ids if existing_item_ids is not None else set()

    for target_item_id in target_products:
      if not target_item_id:
        continue
      if target_item_id in seen_ids:
        early_results.append(
            models.ProductResult(
                target_item_id, models.AdGroupInsertionStatus.ALREADY_PRESENT
            )
        )
        continue
      seen_ids.add(target_item_id)

      if target_item_id in existing_set:
        early_results.append(
            models.ProductResult(
                target_item_id, models.AdGroupInsertionStatus.ALREADY_PRESENT
            )
        )
      else:
        operation = self.client.get_type("AdGroupCriterionOperation")
        operation.create = {
            "ad_group": ad_group_path,
            "status": google_ads_enums.AdGroupCriterionStatusEnum.ENABLED,
            "listing_group": {
                "type_": google_ads_enums.ListingGroupTypeEnum.UNIT,
                "parent_ad_group_criterion": parent_resource_name,
                "case_value": {"product_item_id": {"value": target_item_id}},
            },
        }
        creation_operations.append(operation)
        offers_to_add.append(target_item_id)
        if existing_item_ids is not None:
          existing_item_ids.add(target_item_id)

    return creation_operations, offers_to_add
