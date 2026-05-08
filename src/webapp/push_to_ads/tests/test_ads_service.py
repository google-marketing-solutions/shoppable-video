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

"""Unit tests for the streamlined product listing group AdsService."""

# pylint: disable=protected-access, unused-argument, unused-variable, invalid-name, wrong-import-position

from unittest import mock
import ads_service
import models
import pytest


class MockProtobufMessage:
  """Mocks protobuf message."""

  def __init__(self, dimension_value: str = "product_item_id"):
    self.dimension_value = dimension_value

  def WhichOneof(self, field_name: str) -> str:
    """Allows simulation of standard Google Protobuf WhichOneof inspection."""
    return self.dimension_value


class MockCaseValue:
  """Mocks case value logic."""

  def __init__(self, dimension="product_item_id", item_id="123"):
    self.dimension = dimension
    self.product_item_id = mock.MagicMock()
    self.product_item_id.value = item_id

  def __contains__(self, key):
    """Provides direct native 'in' operator support for the mocked object."""
    return key == self.dimension

  @classmethod
  def pb(cls, instance):
    """Executes type-based conversion from wrapper to raw dummy message."""
    if instance is None:
      return None
    return MockProtobufMessage(instance.dimension)


class MockOperation:
  """Captures complex operation assignments during payload evaluation."""

  def __init__(self):
    self.create = {}
    self.remove = None


@pytest.fixture(name="mock_ads_client")
def fixture_mock_ads_client():
  """Mocks authentication and global Google Ads Client configurations."""
  with mock.patch(
      "google.ads.googleads.client.GoogleAdsClient"
  ) as mock_client_cls, mock.patch(
      "ads_service.google.auth.default"
  ) as mock_auth:

    mock_auth.return_value = (mock.MagicMock(), "mock-project")
    client = mock_client_cls.return_value = mock.MagicMock()

    # Setup Enums
    enums = mock.MagicMock()
    enums.ListingGroupTypeEnum.UNIT = 1
    enums.ListingGroupTypeEnum.SUBDIVISION = 2
    enums.AdGroupCriterionStatusEnum.ENABLED = 1
    client.enums = enums

    # Setup Operation factories
    client.get_type.side_effect = lambda type_name: MockOperation()

    yield client


@pytest.fixture(name="service")
def fixture_service(mock_ads_client):
  """Provides an instantiated AdsService instance targeting standard account."""
  return ads_service.AdsService(customer_id="1234567890")


def test_init_validates_customer_id(mock_ads_client):
  """Tests customer_id validation."""
  with pytest.raises(ValueError, match="customer_id must be provided"):
    ads_service.AdsService(customer_id="")

  # Verify hyphen removal.
  svc = ads_service.AdsService(customer_id="123-456")
  assert svc.customer_id == "123456"


def test_get_listing_group_root_constructs_linkage(service, mock_ads_client):
  """Tests parent-child linkage and dimension extraction."""
  google_ads_svc = mock_ads_client.get_service.return_value

  # Setup parent row.
  parent_row = mock.MagicMock()
  parent_row.ad_group_criterion.resource_name = "res_root"
  parent_row.ad_group_criterion.listing_group.type_ = 2  # SUBDIVISION
  parent_row.ad_group_criterion.listing_group.parent_ad_group_criterion = None
  parent_row.ad_group_criterion.listing_group.case_value = None

  # Setup child node row.
  child_row = mock.MagicMock()
  child_row.ad_group_criterion.resource_name = "res_child"
  child_row.ad_group_criterion.listing_group.type_ = 1  # UNIT
  child_row.ad_group_criterion.listing_group.parent_ad_group_criterion = (
      "res_root"
  )
  child_row.ad_group_criterion.listing_group.case_value = MockCaseValue(
      dimension="product_item_id"
  )

  google_ads_svc.search.return_value = [parent_row, child_row]

  root_node = service._get_listing_group_root(123, "1234567890")

  assert root_node is not None
  assert root_node.resource_name == "res_root"
  assert len(root_node.children) == 1
  assert root_node.children[0].resource_name == "res_child"
  # Node resolved correctly.
  assert root_node.partition_dimension == "product_item_id"


def test_evaluate_tree_state_cases(service, mock_ads_client):
  """Tests tree state evaluation."""
  enums = mock_ads_client.enums

  # Case: CLEAN.
  assert service._evaluate_tree_state(None) == models.TreeState.CLEAN
  unit_root = models.ListingNode(
      resource_name="root", node_type=enums.ListingGroupTypeEnum.UNIT
  )
  assert service._evaluate_tree_state(unit_root) == models.TreeState.CLEAN

  # Case: PARTITIONED.
  partitioned_root = models.ListingNode(
      resource_name="root",
      node_type=enums.ListingGroupTypeEnum.SUBDIVISION,
      partition_dimension="product_item_id",
  )
  assert (
      service._evaluate_tree_state(partitioned_root)
      == models.TreeState.PARTITIONED
  )

  # Case: DIRTY.
  dirty_root = models.ListingNode(
      resource_name="root",
      node_type=enums.ListingGroupTypeEnum.SUBDIVISION,
      partition_dimension="product_brand",  # Invalid for simple tree
  )
  assert service._evaluate_tree_state(dirty_root) == models.TreeState.DIRTY


def test_generate_bootstrap_ops_payload_formatting(service, mock_ads_client):
  """Tests bootstrap payload composition."""
  google_ads_enums = mock_ads_client.enums
  ag_crit_svc = mock_ads_client.get_service.return_value
  ag_crit_svc.ad_group_criterion_path.return_value = "temp_root_id"

  products = ["product_a", "product_a", "product_b"]
  early_results = []

  ops, added_ids = service._generate_bootstrap_ops(
      "ag/path", products, "1234", 10, early_results
  )

  # Verify ops count.
  assert len(ops) == 4  # 1 Subdivision + 1 Other + 2 Flat Units
  assert len(added_ids) == 2
  assert len(early_results) == 1
  assert (
      early_results[0].status == models.AdGroupInsertionStatus.ALREADY_PRESENT
  )

  # Verify deep structure.
  root_op = ops[0]
  assert root_op.create["resource_name"] == "temp_root_id"
  assert (
      root_op.create["listing_group"]["type_"]
      == google_ads_enums.ListingGroupTypeEnum.SUBDIVISION
  )

  other_op = ops[1]
  assert other_op.create["negative"]
  assert (
      other_op.create["listing_group"]["parent_ad_group_criterion"]
      == "temp_root_id"
  )
  assert "product_item_id" in other_op.create["listing_group"]["case_value"]


def test_generate_append_ops_handling(service, mock_ads_client):
  """Tests append operations."""
  google_ads_enums = mock_ads_client.enums

  # Setup parent node.
  root = models.ListingNode(
      resource_name="res_root",
      node_type=google_ads_enums.ListingGroupTypeEnum.SUBDIVISION,
  )
  existing_child = models.ListingNode(
      resource_name="res_101",
      node_type=google_ads_enums.ListingGroupTypeEnum.UNIT,
      case_value=MockCaseValue(dimension="product_item_id", item_id="101"),
  )
  root.children.append(existing_child)

  input_items = ["101", "102", "102"]
  early_results = []

  ops, added_ids = service._generate_append_ops(
      root, input_items, "ag/path", early_results
  )

  assert len(ops) == 1
  assert added_ids == ["102"]
  assert len(early_results) == 2  # 1 local duplicate, 1 server collision

  assert (
      ops[0].create["listing_group"]["parent_ad_group_criterion"] == "res_root"
  )
  assert (
      ops[0].create["listing_group"]["case_value"]["product_item_id"]["value"]
      == "102"
  )


def test_generate_operations_routing_behaviors(service):
  """Tests operation routing logic."""
  service._evaluate_tree_state = mock.MagicMock()
  service._generate_bootstrap_ops = mock.MagicMock(return_value=([], []))
  service._generate_append_ops = mock.MagicMock(return_value=([], []))

  root_node = models.ListingNode(resource_name="legacy_root", node_type=2)

  # Case: PURGE strategy.
  service._evaluate_tree_state.return_value = models.TreeState.CLEAN
  operations, _, _ = service._generate_operations(
      123, root_node, [], models.ListingGroupStrategy.PURGE, "account1"
  )
  assert (
      len(operations) == 1
  )  # Mock returned 0 boots, should only see remove operation
  assert operations[0].remove == "legacy_root"

  # Case: PRESERVE with DIRTY state.
  service._evaluate_tree_state.return_value = models.TreeState.DIRTY
  with pytest.raises(
      ValueError, match="Cannot perform PRESERVE synchronization"
  ):
    service._generate_operations(
        123, root_node, [], models.ListingGroupStrategy.PRESERVE, "account1"
    )


def test_add_offers_to_ad_group_high_level_flow(service, mock_ads_client):
  """Tests add_offers_to_ad_group success path."""
  service._get_listing_group_root = mock.MagicMock(return_value=None)
  service._generate_operations = mock.MagicMock(
      return_value=([MockOperation()], [], ["new_item_id"])
  )

  products = ["new_item_id"]
  final_result = service.add_offers_to_ad_group(1, 1, products)

  assert final_result.error_message is None
  assert len(final_result.products) == 1
  assert (
      final_result.products[0].status == models.AdGroupInsertionStatus.SUCCESS
  )
  svc = mock_ads_client.get_service.return_value
  svc.mutate_ad_group_criteria.assert_called_once()


def test_add_offers_to_ad_group_threshold_limits(service):
  """Tests operation threshold violation."""
  service._get_listing_group_root = mock.MagicMock(return_value=None)
  # Simulate massive bulk return pushing past 10,000 count rule
  service._generate_operations = mock.MagicMock(
      return_value=([MockOperation()] * 10001, [], [])
  )

  products = ["bulk_target"]
  final_result = service.add_offers_to_ad_group(1, 1, products)

  assert (
      "overflows Google Ads API transactional thresholds"
      in final_result.error_message
  )
  assert final_result.products[0].status == models.AdGroupInsertionStatus.FAILED


def test_add_offers_to_ad_group_fault_recovery(service, mock_ads_client):
  """Tests exception recovery."""
  service._get_listing_group_root = mock.MagicMock(
      side_effect=RuntimeError("Simulated API crash")
  )

  products = ["crash_target"]
  final_result = service.add_offers_to_ad_group(1, 1, products)

  assert "Simulated API crash" in final_result.error_message
  assert final_result.products[0].offer_id == "crash_target"
  assert final_result.products[0].status == models.AdGroupInsertionStatus.FAILED


def test_add_offers_early_return_optimization(service, mock_ads_client):
  """Tests early return optimization."""
  # Setup mock yielding 0 operations.
  service._get_listing_group_root = mock.MagicMock(return_value=None)
  service._generate_operations = mock.MagicMock(
      return_value=(
          [],
          [
              models.ProductResult(
                  offer_id="existing",
                  status=models.AdGroupInsertionStatus.ALREADY_PRESENT,
              )
          ],
          [],
      )
  )
  products = ["existing"]

  result = service.add_offers_to_ad_group(123, 456, products)

  # Verify mutate is skipped.
  mock_service = mock_ads_client.get_service.return_value
  mock_service.mutate_ad_group_criteria.assert_not_called()
  assert len(result.products) == 1


def test_evaluate_tree_state_unknown_fallback(service):
  """Tests fallback for invalid node."""
  # Construct valid node but override enum to unknown
  bad_node = models.ListingNode(
      resource_name="unknown_path",
      parent_resource_name="",
      node_type=99,  # Bogus numerical enumeration to force fallback
      case_value={},
  )
  state = service._evaluate_tree_state(bad_node)
  # Ensure fallback to DIRTY.
  assert state == models.TreeState.DIRTY


def test_build_operations_empty_item_id_skip(service, mock_ads_client):
  """Tests skipped empty item ID."""
  # Explicitly pass a target product with blank item_id
  bad_target = ""

  # Build list with valid AND invalid items
  target_products = [bad_target]

  # Verify 0 operations created.
  operations, added_ids = service._build_product_criterion_operations(
      target_products, "parent_res", "path/to/adgroup", []
  )
  assert len(operations) == 0
  assert len(added_ids) == 0
