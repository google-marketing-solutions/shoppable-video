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

"""Unit tests for the AdsInsertionProcessor component."""

# pylint: disable=protected-access, unused-argument, unused-variable, invalid-name, wrong-import-position, redefined-outer-name

from unittest import mock
import ads_service
import google.api_core.exceptions
from google.cloud import firestore
import models
import processor
import pytest


class MockRegistry:
  """Mocks repository for test objects."""

  def __init__(self):
    self.references = {}
    self.collections = {}

  def get_reference(self, path):
    """Creates a DocumentReference mock tied to path factory."""
    if path not in self.references:
      ref = mock.MagicMock(spec=firestore.DocumentReference)
      ref.path = path
      ref.id = path.split("/")[-1]

      ref.collection.side_effect = lambda cid: self.get_collection(
          f"{path}/{cid}"
      )
      self.references[path] = ref
    return self.references[path]

  def get_collection(self, path):
    """Creates a CollectionReference mock tied to path factory."""
    if path not in self.collections:
      coll = mock.MagicMock(spec=firestore.CollectionReference)
      coll.path = path
      coll.id = path.split("/")[-1]

      coll.document.side_effect = lambda did: self.get_reference(
          f"{path}/{did}"
      )

      coll.where.return_value = coll
      coll.order_by.return_value = coll
      coll.limit.return_value = coll

      self.collections[path] = coll
    return self.collections[path]


def create_mock_snapshot(path, exists=True, data_dictionary=None):
  """Creates mock snapshot."""
  snapshot = mock.MagicMock(spec=firestore.DocumentSnapshot)
  type(snapshot).exists = mock.PropertyMock(return_value=exists)

  snapshot.id = path.split("/")[-1]
  snapshot.to_dict.return_value = data_dictionary or {}

  return snapshot


@pytest.fixture(name="mock_registry")
def fixture_mock_registry():
  return MockRegistry()


@pytest.fixture(name="mock_firestore_client")
def fixture_mock_firestore_client(mock_registry):
  """Fixture that intercepts firestore interaction factory calls."""
  client = mock.MagicMock(spec=firestore.Client)
  client.collection.side_effect = mock_registry.get_collection
  return client


@pytest.fixture(name="mock_ads_service")
def fixture_mock_ads_service():
  """Mocks instance interaction with external Google Ads API interface."""
  return mock.MagicMock(spec=ads_service.AdsService)


@pytest.fixture(name="processor")
def fixture_processor(mock_firestore_client, mock_ads_service):
  """Constructs target processor object using injected mocks."""
  return processor.AdsInsertionProcessor(
      firestore_client=mock_firestore_client,
      ads_service=mock_ads_service,
      worker_id="test-worker-uuid",
  )


def test_get_pending_insertion_empty(processor, mock_registry):
  """Tests empty queue handling."""
  coll = mock_registry.get_collection("ads_insertions")
  query_mock = coll.where.return_value.order_by.return_value.limit.return_value
  query_mock.stream.return_value = []

  result = processor.get_pending_insertion()
  assert result is None


def test_get_pending_insertion_success(processor, mock_registry):
  """Tests lock delegation."""
  path = "ads_insertions/req_123"
  doc_ref = mock_registry.get_reference(path)

  snap = create_mock_snapshot(path)
  snap.reference = doc_ref

  coll = mock_registry.get_collection("ads_insertions")
  query_mock = coll.where.return_value.order_by.return_value.limit.return_value
  query_mock.stream.return_value = [snap]

  with mock.patch("processor.transactional_lease") as mock_lease:
    mock_lease.return_value = True
    result = processor.get_pending_insertion()

    assert result == doc_ref
    mock_lease.assert_called_once()


def test_validate_deployment_missing_fields(processor, mock_registry):
  """Tests corrupted map validation."""
  ref = mock_registry.get_reference("d/1")
  data = {"campaign_id": 1}  # missing ad_group_id

  result = processor._validate_deployment(ref, data)
  assert not result


def test_process_deployment_validation_trigger_failure_map(
    processor, mock_registry
):
  """Tests recovery on failed validation."""
  path = "ads_insertions/r1/deployments/d1"
  ref = mock_registry.get_reference(path)

  bad_data = {"campaign_id": 1, "offers": {"o_1": {}}}
  snap = create_mock_snapshot(path, data_dictionary=bad_data)
  snap.reference = ref

  processor.process_deployment(snap)

  # Verifies DocumentRef received updates to Firestore
  ref.update.assert_called_once()


def test_process_deployment_ads_success(
    processor, mock_registry, mock_ads_service
):
  """Tests successful mutation lifecycle."""
  path = "ads_insertions/r1/deployments/d1"
  ref = mock_registry.get_reference(path)

  valid_data = {
      "customer_id": "123",
      "campaign_id": 456,
      "ad_group_id": 789,
      "offers": {"o_1": {"cpc_bid_micros": 1000}},
  }
  snap = create_mock_snapshot(path, data_dictionary=valid_data)
  snap.reference = ref

  # Mock successful response.
  mock_ads_service.add_offers_to_ad_group.return_value = (
      models.AdsMutationResult(
          ad_group_id=789,
          campaign_id=456,
          customer_id="123",
          products=[
              models.ProductResult(
                  offer_id="o_1", status=models.AdGroupInsertionStatus.SUCCESS
              )
          ],
          error_message=None,
      )
  )

  processor.process_deployment(snap)

  mock_ads_service.add_offers_to_ad_group.assert_called_once()
  ref.update.assert_called_once()


def test_process_deployment_ads_api_exception(
    processor, mock_registry, mock_ads_service
):
  """Tests exception containment."""
  path = "ads_insertions/r1/deployments/d1"
  ref = mock_registry.get_reference(path)

  valid_data = {
      "customer_id": "123",
      "campaign_id": 456,
      "ad_group_id": 789,
      "offers": {"o_1": {}},
  }
  snap = create_mock_snapshot(path, data_dictionary=valid_data)
  snap.reference = ref

  mock_ads_service.add_offers_to_ad_group.side_effect = Exception("API Crash")

  processor.process_deployment(snap)

  ref.update.assert_called_once()
  # verify update was mapped as error via string checking if possible
  args, _ = ref.update.call_args
  payload = args[0]
  assert any("Fatal" in str(v) for v in payload.values())


def test_run_loop_continuous_drain_to_empty(processor, mock_registry):
  """Tests loop persistence."""

  r1 = mock_registry.get_reference("ads_insertions/r1")

  with mock.patch.object(processor, "get_pending_insertion") as mock_get:
    # Return one insertion, then return None causing the loop logic to break
    mock_get.side_effect = [r1, None]

    d_path = "ads_insertions/r1/deployments/d1"
    d_snap = create_mock_snapshot(d_path)
    # Fetch the precise registry collection and set its return stream
    r1_coll = mock_registry.get_collection("ads_insertions/r1/deployments")
    r1_coll.stream.return_value = [d_snap]

    with mock.patch.object(processor, "process_deployment") as mock_proc:
      mock_proc.return_value = models.DeploymentResult(
          success_count=1, total_count=1
      )
      with mock.patch.object(processor, "_finalize_job_state") as mock_final:

        processor.run()

        mock_proc.assert_called_once()
        mock_final.assert_called_once_with(r1, success_count=1, total_count=1)


def test_run_fault_isolation_across_jobs(processor, mock_registry):
  """Tests loop boundary protection."""
  r1 = mock_registry.get_reference("ads_insertions/r1")
  r2 = mock_registry.get_reference("ads_insertions/r2")

  with mock.patch.object(processor, "get_pending_insertion") as mock_get:
    # Return two insertions, then None.
    mock_get.side_effect = [r1, r2, None]

    d1_snap = create_mock_snapshot("ads_insertions/r1/deployments/d1")
    r1_coll = mock_registry.get_collection("ads_insertions/r1/deployments")
    r1_coll.stream.return_value = [d1_snap]

    d2_snap = create_mock_snapshot("ads_insertions/r2/deployments/d2")
    r2_coll = mock_registry.get_collection("ads_insertions/r2/deployments")
    r2_coll.stream.return_value = [d2_snap]

    with mock.patch.object(processor, "process_deployment") as mock_proc:
      # Force FIRST run to crash, SECOND run succeeds with DeploymentResult.
      mock_proc.side_effect = [
          Exception("Fail R1"),
          models.DeploymentResult(success_count=1, total_count=1),
      ]

      with mock.patch.object(processor, "_finalize_job_state") as mock_final:
        processor.run()

        # Both finalize calls occurred, indicating processing did not abort!
        assert mock_final.call_count == 2

        # Verify first finalizer was error call, second was normal success
        calls = mock_final.call_args_list
        # Call 1 args
        assert "Fail R1" in str(calls[0][1].get("error_message"))
        # Call 2 args (Success)
        assert calls[1][1].get("error_message") is None


def test_transactional_lease_logic(mock_registry):
  """Tests lease logic."""

  path = "ads_insertions/req_lease"
  doc_ref = mock_registry.get_reference(path)
  transaction = mock.MagicMock()
  transaction._read_only = False

  # Scenario A: Document does not exist
  snap_missing = create_mock_snapshot(path, exists=False)
  doc_ref.get = mock.MagicMock(return_value=snap_missing)
  assert not processor.transactional_lease(
      transaction, doc_ref, "worker_1", mock.MagicMock()
  )

  # Scenario B: Document is SUCCESS (not leaseable)
  snap_success = create_mock_snapshot(
      path, data_dictionary={"status": models.AdGroupInsertionStatus.SUCCESS}
  )
  doc_ref.get = mock.MagicMock(return_value=snap_success)
  assert not processor.transactional_lease(
      transaction, doc_ref, "worker_1", mock.MagicMock()
  )

  # Scenario C: Document is PENDING (leaseable)
  snap_pending = create_mock_snapshot(
      path, data_dictionary={"status": models.AdGroupInsertionStatus.PENDING}
  )
  doc_ref.get = mock.MagicMock(return_value=snap_pending)
  assert processor.transactional_lease(
      transaction, doc_ref, "worker_1", mock.MagicMock()
  )
  transaction.update.assert_called_once()


def test_get_pending_insertion_contention(processor, mock_registry):
  """Tests lock contention recovery."""
  path = "ads_insertions/req_contention"
  doc_ref = mock_registry.get_reference(path)
  snap = create_mock_snapshot(path)
  snap.reference = doc_ref

  coll = mock_registry.get_collection("ads_insertions")
  # Simulate finding document on check 1, then empty sets to exit outer
  # while loop
  query_mock = coll.where.return_value.order_by.return_value.limit.return_value
  query_mock.stream.side_effect = [[snap], [], [], []]

  with mock.patch("processor.transactional_lease") as mock_lease:
    # Force a contention exception using exact API exception type
    mock_lease.side_effect = google.api_core.exceptions.Aborted(
        "Firestore Contention Exception"
    )
    result = processor.get_pending_insertion()
    # Verify the exception was caught and None returned gracefully
    assert result is None
    assert mock_lease.call_count == 1


def test_finalize_job_state_outcomes(processor, mock_registry):
  """Tests state calculation."""

  path = "ads_insertions/req_final"
  req_ref = mock_registry.get_reference(path)

  # Scenario A: Exception caught during processing
  processor._finalize_job_state(req_ref, error_message="Terminal Worker Crash")
  args, _ = req_ref.update.call_args
  assert args[0]["status"] == models.AdGroupInsertionStatus.FAILED
  assert "Terminal Worker Crash" in args[0]["error_message"]

  # Scenario B: 100% Success
  processor._finalize_job_state(req_ref, success_count=5, total_count=5)
  args, _ = req_ref.update.call_args
  assert args[0]["status"] == models.AdGroupInsertionStatus.SUCCESS

  # Scenario C: Partial Success
  processor._finalize_job_state(req_ref, success_count=3, total_count=5)
  args, _ = req_ref.update.call_args
  assert args[0]["status"] == models.AdGroupInsertionStatus.PARTIAL_SUCCESS

  # Scenario D: 0% Success / Failed
  processor._finalize_job_state(req_ref, success_count=0, total_count=5)
  args, _ = req_ref.update.call_args
  assert args[0]["status"] == models.AdGroupInsertionStatus.FAILED


def test_validate_empty_offers(processor):
  """Tests empty field payload rejection."""

  path = "ads_insertions/req_empty/deployments/d1"
  invalid_snap = create_mock_snapshot(
      path,
      data_dictionary={
          "campaign_id": "123",
          "ad_group_id": "456",
          "customer_id": "789",
          "offers": {},
      },
  )
  # Validate deployment returns False on empty offers explicitly
  res = processor._validate_deployment(invalid_snap, invalid_snap.to_dict())
  assert not res


def test_process_deployment_missing_snapshot(processor):
  """Tests missing entry handling."""
  path = "ads_insertions/req_miss/deployments/d1"
  missing_snap = create_mock_snapshot(path, exists=False)
  # Should immediately return zeroed deployment result instead of proceeding
  res = processor.process_deployment(missing_snap)
  assert res.success_count == 0
  assert res.total_count == 0


def test_map_results_partial_failure(processor):
  """Tests outcome routing."""

  product_results = [
      models.ProductResult(
          offer_id="p1", status=models.AdGroupInsertionStatus.SUCCESS
      ),
      models.ProductResult(
          offer_id="p2", status=models.AdGroupInsertionStatus.FAILED
      ),
  ]
  mut_res = models.AdsMutationResult(
      ad_group_id=123,
      campaign_id=456,
      customer_id="789",
      products=product_results,
      error_message="Global API Error",
  )
  # Must pass fake client to resolve field_path calls
  processor.firestore_client = mock.MagicMock()
  # Set side effect to simulate basic dot-notated field path for assertions
  processor.firestore_client.field_path.side_effect = lambda *args: ".".join(
      args
  )

  updates = processor._map_results_to_updates(mut_res, ["p1", "p2"])
  # Ensure partial failure propagated explicitly using aggregated error message
  assert updates["offers.p1.status"] == models.AdGroupInsertionStatus.SUCCESS
  assert updates["offers.p2.status"] == models.AdGroupInsertionStatus.FAILED
  assert updates["offers.p2.error_message"] == "Fatal: Global API Error"
