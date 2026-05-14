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

"""Unit tests for the FirestoreService component."""

import datetime
from unittest import mock

from app.models import ad_group_insertion
from app.models import candidate
from app.models import video
from app.services import firestore_service
from google.cloud import firestore
import pytest


class MockRegistry:
  """Centralized repository ensuring deterministic identical objects."""

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

      parent_collection_mock = mock.MagicMock()
      parent_doc_mock = mock.MagicMock()
      ref.parent = parent_collection_mock
      parent_collection_mock.parent = parent_doc_mock

      path_segments = path.split("/")
      if len(path_segments) >= 3:
        parent_doc_mock.id = path_segments[-3]

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
      coll.offset.return_value = coll

      self.collections[path] = coll
    return self.collections[path]


def create_mock_snapshot(path, exists=True, data_dictionary=None):
  """Create highly consistent DocumentSnapshots with status values."""
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
  """Fixture to patch base Firestore client linked to path factory."""
  with mock.patch("google.cloud.firestore.Client") as mock_client_class:
    client_instance = mock_client_class.return_value

    client_instance.collection.side_effect = mock_registry.get_collection
    client_instance.collection_group.side_effect = mock_registry.get_collection

    mock_batch = mock.MagicMock(spec=firestore.WriteBatch)
    client_instance.batch.return_value = mock_batch

    # Provide transactional ecosystem with required protected attributes
    # to satisfy @transactional
    mock_tx = mock.MagicMock(spec=firestore.Transaction)
    # pylint: disable=protected-access
    mock_tx._read_only = False
    mock_tx._max_attempts = 1
    mock_tx._id = b"mock-test-boundary"
    # pylint: enable=protected-access
    client_instance.transaction.return_value = mock_tx

    yield client_instance


@pytest.fixture(name="service")
def fixture_service(mock_firestore_client):
  """Build instance of FirestoreService connected to mock ecosystem."""
  return firestore_service.FirestoreService(
      project_id="test-project",
      database_id="mock-firestore-db",
      client=mock_firestore_client,
  )


def test_get_video_analysis_not_found(service, mock_registry):
  """Test that non-existent video root correctly yields None results."""
  video_ref = mock_registry.get_reference("videos/video_123")

  video_ref.get.return_value = create_mock_snapshot(
      "videos/video_123", exists=False
  )

  result = service.get_video_analysis("123")

  assert result is None


def test_get_video_analysis_incomplete_stub(service, mock_registry):
  """Test validation logic that detects processing stubs safely."""
  video_ref = mock_registry.get_reference("videos/video_123")

  stub_data = {"stats_matched_count": 5}
  video_ref.get.return_value = create_mock_snapshot(
      "videos/video_123", exists=True, data_dictionary=stub_data
  )

  result = service.get_video_analysis("123")

  assert result is None


def test_get_video_analysis_success(
    service, mock_firestore_client, mock_registry
):
  """Confirms retrieval correctly reconstructs nested video graph."""
  video_ref = mock_registry.get_reference("videos/video_123")
  video_core_data = {
      "source": "google_ads",
      "video_id": "youtube_123",
      "title": "Mock Title",
      "description": "Mock Desc",
  }
  video_ref.get.return_value = create_mock_snapshot(
      "videos/video_123", data_dictionary=video_core_data
  )

  idp_snapshot = create_mock_snapshot(
      "videos/video_123/identified_products/idp_ABC",
      data_dictionary={
          "title": "Generic Shirt",
          "description": "Test Clothing Item",
          "relevance_reasoning": "Visible",
      },
  )
  video_ref.collection("identified_products").stream.return_value = [
      idp_snapshot
  ]

  matched_products_query = mock_registry.get_collection("matched_products")
  match_snapshot = create_mock_snapshot(
      "videos/video_123/identified_products/idp_ABC/matched_products/offer_XYZ",
      data_dictionary={
          "video_uuid": "123",
          "identified_product_uuid": "ABC",
          "offer_id": "XYZ",
          "candidate_status": "UNREVIEWED",
          "distance": 0.123,
      },
  )
  matched_products_query.where.return_value.stream.return_value = [
      match_snapshot
  ]

  inventory_snapshot = create_mock_snapshot(
      "products/prod_XYZ",
      data_dictionary={
          "offer_id": "XYZ",
          "title": "Blue Nike T-Shirt",
          "brand": "Nike",
          "availability": "in stock",
      },
  )
  mock_firestore_client.get_all.return_value = [inventory_snapshot]

  result = service.get_video_analysis("123")

  assert result.video.uuid == "123"
  assert (
      result.identified_products[0].matched_products[0].matched_product_title
      == "Blue Nike T-Shirt"
  )


def test_get_video_analysis_summary_success(service, mock_registry):
  """Test paginated summary accumulation and stub bypassing."""
  count_mock = mock.MagicMock()
  count_mock.value = 1
  mock_registry.get_collection("videos").count.return_value.get.return_value = [
      [count_mock]
  ]

  valid_snap = create_mock_snapshot(
      "videos/video_1",
      data_dictionary={
          "source": "gcs",
          "video_id": "vid_1",
          "stats_identified_count": 1,
      },
  )
  coll = mock_registry.get_collection("videos")
  ordered = coll.order_by.return_value
  ordered.offset.return_value.limit.return_value.stream.return_value = [
      valid_snap
  ]

  response = service.get_video_analysis_summary(
      video.PaginationParams(limit=10)
  )

  assert response.total_count == 1
  assert len(response.items) == 1


def test_update_candidates_empty(service, mock_firestore_client):
  service.update_candidates([])
  mock_firestore_client.transaction.assert_not_called()


def test_update_candidates_transaction_success(
    service, mock_firestore_client, mock_registry
):
  """Test ACID transactional propagation and state machine logic.

  Args:
    service: FirestoreService instance.
    mock_firestore_client: Mocked Firestore client.
    mock_registry: MockRegistry instance.
  """
  mock_tx = mock_firestore_client.transaction.return_value

  vid_uuid = "vid123"
  video_ref = mock_registry.get_reference(f"videos/video_{vid_uuid}")

  # Initial historical baseline state
  video_ref.get.return_value = create_mock_snapshot(
      video_ref.path,
      data_dictionary={
          "stats_approved_count": 10,
          "stats_matched_count": 17,
          "active_pushes": {},
          "has_successful_push": False,
      },
  )

  req = candidate.Candidate(
      video_analysis_uuid=vid_uuid,
      identified_product_uuid="candA",
      candidate_offer_id="offX",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="robot", is_added_by_user=False
      ),
  )

  cand_path = (
      f"videos/video_{vid_uuid}/identified_products/idp_candA/"
      "matched_products/offer_offX"
  )
  state_snap = create_mock_snapshot(
      cand_path, data_dictionary={"candidate_status": "UNREVIEWED"}
  )
  state_snap.reference = mock_registry.get_reference(cand_path)
  mock_firestore_client.get_all.return_value = [state_snap]

  # Execution
  service.update_candidates([req])

  # Verify absolute transaction alignment
  mock_firestore_client.transaction.assert_called_once()
  video_ref.get.assert_called_once_with(transaction=mock_tx)

  # Check cumulative final set writes dispatched
  final_writes = {
      call.args[0]: call.args[1] for call in mock_tx.set.call_args_list
  }

  # Verify video updates: Approved 10->11, Unreviewed 2->1, and Waterfall hit.
  assert video_ref in final_writes
  v_data = final_writes[video_ref]
  assert v_data["stats_approved_count"] == 11
  assert v_data["status"] == "Ready to Push"


def test_update_candidates_transaction_chunking(
    service, mock_firestore_client, mock_registry
):
  """Test transaction handles execute iterative chunks per video boundary.

  Args:
    service: FirestoreService instance.
    mock_firestore_client: Mocked Firestore client.
    mock_registry: MockRegistry instance.
  """
  candidates_pool = []
  # Populate pool with 105 candidates belonging to the same target video
  for i in range(105):
    candidates_pool.append(
        candidate.Candidate(
            video_analysis_uuid="target_vid",
            identified_product_uuid=f"i_{i}",
            candidate_offer_id=f"o_{i}",
            candidate_status=candidate.CandidateStatus(
                status="APPROVED", user="t", is_added_by_user=False
            ),
        )
    )

  video_ref = mock_registry.get_reference("videos/video_target_vid")
  video_ref.get.side_effect = [
      create_mock_snapshot(video_ref.path, data_dictionary={}),
      create_mock_snapshot(
          video_ref.path,
          data_dictionary={
              "stats_approved_count": 100,
              "stats_matched_count": 100,
          },
      ),
  ]

  mock_firestore_client.get_all.return_value = []

  service.update_candidates(candidates_pool)

  # With a transaction_chunk_size of 100, 105 items MUST fire 2 separate
  # transactions
  assert mock_firestore_client.transaction.call_count == 2

  # Verify that the second transaction correctly accumulated the counts
  mock_tx = mock_firestore_client.transaction.return_value
  video_set_calls = [
      call for call in mock_tx.set.call_args_list if call.args[0] == video_ref
  ]
  assert len(video_set_calls) == 2
  args, _ = video_set_calls[-1]
  final_video_data = args[1]
  assert final_video_data["stats_approved_count"] == 105
  assert final_video_data["stats_matched_count"] == 105


def test_insert_submission_requests_success(service, mock_firestore_client):
  """Verifies atomic ingestion logic registers internal jobs successfully."""
  mock_batch = mock_firestore_client.batch.return_value

  req = candidate.SubmissionMetadata(
      request_uuid="R",
      video_uuid="V",
      offer_ids="A,B",
      destinations=[
          candidate.Destination(customer_id=1, campaign_id=2, ad_group_id=3)
      ],
      submitting_user="u",
      cpc=1.0,
  )
  service.insert_submission_requests([req])
  assert mock_batch.set.call_count == 2


def test_get_ad_group_insertion_statuses_for_video_success(
    service, mock_firestore_client, mock_registry
):
  """Confirms single-video lookup recovers target deployment status."""
  dpath = "ads_insertions/req_ALPHA/deployments/deploy_A"
  deploy_snap = create_mock_snapshot(
      dpath,
      data_dictionary={
          "customer_id": 123,
          "campaign_id": 456,
          "ad_group_id": 789,
          "offers": {"P": {"status": "X"}},
      },
  )

  deploy_snap.reference = mock_registry.get_reference(dpath)

  mock_registry.get_collection(
      "deployments"
  ).where.return_value.stream.return_value = [deploy_snap]

  time_val = datetime.datetime.now(datetime.timezone.utc)
  p_snap = create_mock_snapshot(
      "ads_insertions/req_ALPHA",
      data_dictionary={"status": "COMPLETED", "timestamp": time_val},
  )
  mock_firestore_client.get_all.return_value = [p_snap]

  v_ref = mock_registry.get_reference("videos/video_V123")
  v_ref.get.return_value = create_mock_snapshot(
      "videos/video_V123", exists=False
  )

  res = service.get_ad_group_insertion_statuses_for_video("V123")

  assert len(res) == 1
  assert res[0].status == "COMPLETED"


def test_get_all_ad_group_insertion_statuses_success(service, mock_registry):
  """Tests pagination loop aggregates deployment logs cleanly."""
  c_obj = mock.MagicMock()
  c_obj.value = 1
  mock_registry.get_collection(
      "ads_insertions"
  ).count.return_value.get.return_value = [[c_obj]]

  t_val = datetime.datetime.now(datetime.timezone.utc)
  req_snap = create_mock_snapshot(
      "ads_insertions/req_X",
      data_dictionary={"video_uuid": "V", "status": "P", "timestamp": t_val},
  )
  coll = mock_registry.get_collection("ads_insertions")
  ordered = coll.order_by.return_value
  ordered.offset.return_value.limit.return_value.stream.return_value = [
      req_snap
  ]

  dpath = "ads_insertions/req_X/deployments/deploy_Y"
  d_snap = create_mock_snapshot(
      dpath,
      data_dictionary={
          "customer_id": 1,
          "campaign_id": 2,
          "ad_group_id": 3,
          "offers": {"I": {"status": "S"}},
      },
  )
  d_snap.reference = mock_registry.get_reference(dpath)

  mock_registry.get_collection(
      "deployments"
  ).where.return_value.stream.return_value = [d_snap]

  final = service.get_all_ad_group_insertion_statuses(
      ad_group_insertion.AdGroupPaginationParams(limit=10)
  )
  assert len(final.items) == 1


def test_get_ad_group_insertion_status_not_found(service, mock_registry):
  target_doc_ref = mock_registry.get_reference("ads_insertions/req_NONE")

  missing_snapshot = create_mock_snapshot(
      "ads_insertions/req_NONE", exists=False
  )

  target_doc_ref.get.return_value = missing_snapshot

  output = service.get_ad_group_insertion_status("NONE")
  assert not output


def test_firestore_batch_manager_auto_commit(
    mock_firestore_client, mock_registry
):
  """Ensures .set() triggers automatic commit upon hitting the limit."""
  mgr = firestore_service.FirestoreBatchManager(mock_firestore_client, limit=1)
  mock_batch = mock_firestore_client.batch.return_value

  test_ref = mock_registry.get_reference("videos/v1")
  mgr.set(test_ref, {"foo": "bar"})

  assert mock_batch.commit.call_count == 1


def test_firestore_batch_manager_reserve_early_flush(
    mock_firestore_client,
):
  """Ensures .reserve() flushes active batch if space hits limit."""
  mgr = firestore_service.FirestoreBatchManager(mock_firestore_client, limit=5)
  mock_batch = mock_firestore_client.batch.return_value

  mgr.count = 4
  mgr.reserve(2)  # 4 + 2 > 5

  assert mock_batch.commit.call_count == 1
  assert mgr.count == 0


def test_update_candidates_with_user_addition(
    service, mock_firestore_client, mock_registry
):
  """Verifies execution path creating new products when added by user."""
  req = candidate.Candidate(
      video_analysis_uuid="V1",
      identified_product_uuid="IDP1",
      candidate_offer_id="PROD1",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="u1", is_added_by_user=True
      ),
  )
  mock_tx = mock_firestore_client.transaction.return_value
  video_ref = mock_registry.get_reference("videos/video_V1")
  video_ref.get.return_value = create_mock_snapshot(
      video_ref.path, data_dictionary={}
  )

  path = (
      "videos/video_V1/identified_products/idp_IDP1/"
      "matched_products/offer_PROD1"
  )
  state_snap = create_mock_snapshot(path, data_dictionary={})
  state_snap.reference = mock_registry.get_reference(path)

  mock_firestore_client.get_all.return_value = [state_snap]

  service.update_candidates([req])

  # Confirm set writes for both candidate AND the user product global catalog
  assert mock_tx.set.call_count >= 2


def test_insert_submission_requests_with_destinations(
    service, mock_firestore_client
):
  """Covers automatic reservation for parent and children blocks."""
  mock_batch = mock_firestore_client.batch.return_value
  req = candidate.SubmissionMetadata(
      request_uuid="R1",
      video_uuid="V1",
      offer_ids="O1",
      submitting_user="u1",
      destinations=[
          candidate.Destination(customer_id=1, campaign_id=2, ad_group_id=3),
          candidate.Destination(customer_id=4, campaign_id=5, ad_group_id=6),
      ],
  )
  service.insert_submission_requests([req])

  assert mock_batch.set.call_count == 3


def test_calculate_candidate_deltas_new_approved():
  """Test behavior when the candidate is new and approved."""
  cand = candidate.Candidate(
      video_analysis_uuid="V1",
      identified_product_uuid="IDP1",
      candidate_offer_id="O1",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="u1", is_added_by_user=False
      ),
  )
  # pylint: disable=protected-access
  delta_approved, delta_matched = firestore_service._calculate_candidate_deltas(
      cand, None
  )
  # pylint: enable=protected-access
  assert delta_approved == 1
  assert delta_matched == 1


def test_calculate_candidate_deltas_new_unreviewed():
  """Test behavior when the candidate is new and unreviewed."""
  cand = candidate.Candidate(
      video_analysis_uuid="V1",
      identified_product_uuid="IDP1",
      candidate_offer_id="O1",
      candidate_status=candidate.CandidateStatus(
          status="UNREVIEWED", user="u1", is_added_by_user=False
      ),
  )
  # pylint: disable=protected-access
  delta_approved, delta_matched = firestore_service._calculate_candidate_deltas(
      cand, None
  )
  # pylint: enable=protected-access
  assert delta_approved == 0
  assert delta_matched == 1


def test_calculate_candidate_deltas_status_changed_to_rejected():
  """Test behavior when status changes from APPROVED to REJECTED."""
  cand = candidate.Candidate(
      video_analysis_uuid="V1",
      identified_product_uuid="IDP1",
      candidate_offer_id="O1",
      candidate_status=candidate.CandidateStatus(
          status="DISAPPROVED", user="u1", is_added_by_user=False
      ),
  )
  snapshot = create_mock_snapshot(
      "videos/video_V1/identified_products/idp_IDP1/matched_products/offer_O1",
      data_dictionary={"candidate_status": "APPROVED"},
  )
  # pylint: disable=protected-access
  delta_approved, delta_matched = firestore_service._calculate_candidate_deltas(
      cand, snapshot
  )
  # pylint: enable=protected-access
  assert delta_approved == -1
  assert delta_matched == 0


def test_calculate_candidate_deltas_no_change():
  """Test behavior when status does not change (APPROVED -> APPROVED)."""
  cand = candidate.Candidate(
      video_analysis_uuid="V1",
      identified_product_uuid="IDP1",
      candidate_offer_id="O1",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="u1", is_added_by_user=False
      ),
  )
  snapshot = create_mock_snapshot(
      "videos/video_V1/identified_products/idp_IDP1/matched_products/offer_O1",
      data_dictionary={"candidate_status": "APPROVED"},
  )
  # pylint: disable=protected-access
  delta_approved, delta_matched = firestore_service._calculate_candidate_deltas(
      cand, snapshot
  )
  # pylint: enable=protected-access
  assert delta_approved == 0
  assert delta_matched == 0


def test_derive_video_status_push_in_progress():
  """Test that 'Push in Progress' takes priority."""
  active_pushes = {"req_1": "timestamp"}
  status = firestore_service._derive_video_status(active_pushes, False, 0)  # pylint: disable=protected-access
  assert status == "Push in Progress"


def test_derive_video_status_push_complete():
  """Test that 'Push Complete' is returned when a successful push exists."""
  active_pushes = {}
  status = firestore_service._derive_video_status(active_pushes, True, 0)  # pylint: disable=protected-access
  assert status == "Push Complete"


def test_derive_video_status_needs_review():
  """Test fallback to 'Needs Review'."""
  active_pushes = {}
  status = firestore_service._derive_video_status(active_pushes, False, 0)  # pylint: disable=protected-access
  assert status == "Needs Review"


def test_update_candidates_transaction_multiple_candidates(
    service, mock_firestore_client, mock_registry
):
  """Test updating multiple candidates for a video in a single transaction.

  Args:
    service: FirestoreService instance.
    mock_firestore_client: Mocked Firestore client.
    mock_registry: MockRegistry instance.
  """
  mock_tx = mock_firestore_client.transaction.return_value

  vid_uuid = "vid123"
  video_ref = mock_registry.get_reference(f"videos/video_{vid_uuid}")
  video_ref.get.return_value = create_mock_snapshot(
      video_ref.path,
      data_dictionary={
          "stats_approved_count": 0,
          "stats_matched_count": 0,
          "active_pushes": {},
          "has_successful_push": False,
      },
  )

  req1 = candidate.Candidate(
      video_analysis_uuid=vid_uuid,
      identified_product_uuid="candA",
      candidate_offer_id="offX",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="robot", is_added_by_user=False
      ),
  )
  req2 = candidate.Candidate(
      video_analysis_uuid=vid_uuid,
      identified_product_uuid="candB",
      candidate_offer_id="offY",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="robot", is_added_by_user=False
      ),
  )

  cand1_path = (
      f"videos/video_{vid_uuid}/identified_products/idp_candA/"
      "matched_products/offer_offX"
  )
  cand2_path = (
      f"videos/video_{vid_uuid}/identified_products/idp_candB/"
      "matched_products/offer_offY"
  )

  snap1 = create_mock_snapshot(cand1_path, exists=False, data_dictionary={})
  snap1.reference = mock_registry.get_reference(cand1_path)
  snap2 = create_mock_snapshot(cand2_path, exists=False, data_dictionary={})
  snap2.reference = mock_registry.get_reference(cand2_path)

  mock_firestore_client.get_all.return_value = [snap1, snap2]

  service.update_candidates([req1, req2])

  final_writes = {
      call.args[0]: call.args[1] for call in mock_tx.set.call_args_list
  }

  assert video_ref in final_writes
  v_data = final_writes[video_ref]
  assert v_data["stats_approved_count"] == 2
  assert v_data["stats_matched_count"] == 2
  assert v_data["status"] == "Ready to Push"


def test_update_candidates_counts_floor(
    service, mock_firestore_client, mock_registry
):
  """Test that counts do not drop below zero."""
  mock_tx = mock_firestore_client.transaction.return_value

  vid_uuid = "vid123"
  video_ref = mock_registry.get_reference(f"videos/video_{vid_uuid}")
  video_ref.get.return_value = create_mock_snapshot(
      video_ref.path,
      data_dictionary={
          "stats_approved_count": 0,
          "stats_matched_count": 0,
          "active_pushes": {},
          "has_successful_push": False,
      },
  )

  req = candidate.Candidate(
      video_analysis_uuid=vid_uuid,
      identified_product_uuid="candA",
      candidate_offer_id="offX",
      candidate_status=candidate.CandidateStatus(
          status="DISAPPROVED", user="robot", is_added_by_user=False
      ),
  )

  cand_path = (
      f"videos/video_{vid_uuid}/identified_products/idp_candA/"
      "matched_products/offer_offX"
  )
  state_snap = create_mock_snapshot(
      cand_path, data_dictionary={"candidate_status": "APPROVED"}
  )
  state_snap.reference = mock_registry.get_reference(cand_path)
  mock_firestore_client.get_all.return_value = [state_snap]

  service.update_candidates([req])

  final_writes = {
      call.args[0]: call.args[1] for call in mock_tx.set.call_args_list
  }

  assert video_ref in final_writes
  v_data = final_writes[video_ref]
  assert v_data["stats_approved_count"] == 0  # Floor applied
  assert v_data["stats_matched_count"] == 0


def test_update_candidates_missing_video_doc(
    service, mock_firestore_client, mock_registry
):
  """Test behavior when the video document does not exist yet."""
  mock_tx = mock_firestore_client.transaction.return_value

  vid_uuid = "vid123"
  video_ref = mock_registry.get_reference(f"videos/video_{vid_uuid}")

  # Simulate missing video doc
  video_ref.get.return_value = create_mock_snapshot(
      video_ref.path, exists=False, data_dictionary={}
  )

  req = candidate.Candidate(
      video_analysis_uuid=vid_uuid,
      identified_product_uuid="candA",
      candidate_offer_id="offX",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="robot", is_added_by_user=False
      ),
  )

  cand_path = (
      f"videos/video_{vid_uuid}/identified_products/idp_candA/"
      "matched_products/offer_offX"
  )
  state_snap = create_mock_snapshot(cand_path, exists=False, data_dictionary={})
  state_snap.reference = mock_registry.get_reference(cand_path)
  mock_firestore_client.get_all.return_value = [state_snap]

  service.update_candidates([req])

  final_writes = {
      call.args[0]: call.args[1] for call in mock_tx.set.call_args_list
  }

  assert video_ref in final_writes
  v_data = final_writes[video_ref]
  assert v_data["stats_approved_count"] == 1
  assert v_data["stats_matched_count"] == 1
  assert v_data["status"] == "Ready to Push"


def test_update_candidates_deduplication(
    service, mock_firestore_client, mock_registry
):
  """Test that duplicate candidates in input list are deduplicated."""
  mock_tx = mock_firestore_client.transaction.return_value

  vid_uuid = "vid123"
  video_ref = mock_registry.get_reference(f"videos/video_{vid_uuid}")
  video_ref.get.return_value = create_mock_snapshot(
      video_ref.path, data_dictionary={}
  )

  req1 = candidate.Candidate(
      video_analysis_uuid=vid_uuid,
      identified_product_uuid="candA",
      candidate_offer_id="offX",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="robot", is_added_by_user=False
      ),
  )
  req2 = candidate.Candidate(
      video_analysis_uuid=vid_uuid,
      identified_product_uuid="candA",
      candidate_offer_id="offX",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="robot", is_added_by_user=False
      ),
  )

  cand_path = (
      f"videos/video_{vid_uuid}/identified_products/idp_candA/"
      "matched_products/offer_offX"
  )
  state_snap = create_mock_snapshot(cand_path, exists=False, data_dictionary={})
  state_snap.reference = mock_registry.get_reference(cand_path)
  mock_firestore_client.get_all.return_value = [state_snap]

  service.update_candidates([req1, req2])

  # Count calls directly from call_args_list to avoid masking duplicate calls
  cand_set_count = sum(
      1 for call in mock_tx.set.call_args_list if call.args[0].path == cand_path
  )
  assert cand_set_count == 1

  # Also assert video document counts are not doubled
  final_writes = {
      call.args[0]: call.args[1] for call in mock_tx.set.call_args_list
  }
  assert video_ref in final_writes
  v_data = final_writes[video_ref]
  assert v_data["stats_approved_count"] == 1
  assert v_data["stats_matched_count"] == 1


def test_update_candidates_multiple_videos(
    service, mock_firestore_client, mock_registry
):
  """Test that candidates from multiple videos trigger separate transactions."""
  req1 = candidate.Candidate(
      video_analysis_uuid="vid1",
      identified_product_uuid="candA",
      candidate_offer_id="offX",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="robot", is_added_by_user=False
      ),
  )
  req2 = candidate.Candidate(
      video_analysis_uuid="vid2",
      identified_product_uuid="candB",
      candidate_offer_id="offY",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="robot", is_added_by_user=False
      ),
  )

  video_ref1 = mock_registry.get_reference("videos/video_vid1")
  video_ref1.get.return_value = create_mock_snapshot(
      video_ref1.path, data_dictionary={}
  )

  video_ref2 = mock_registry.get_reference("videos/video_vid2")
  video_ref2.get.return_value = create_mock_snapshot(
      video_ref2.path, data_dictionary={}
  )

  snap1 = create_mock_snapshot(
      "videos/video_vid1/identified_products/idp_candA/"
      "matched_products/offer_offX",
      exists=False,
  )
  snap1.reference = mock_registry.get_reference(
      "videos/video_vid1/identified_products/idp_candA/"
      "matched_products/offer_offX"
  )
  snap2 = create_mock_snapshot(
      "videos/video_vid2/identified_products/idp_candB/"
      "matched_products/offer_offY",
      exists=False,
  )
  snap2.reference = mock_registry.get_reference(
      "videos/video_vid2/identified_products/idp_candB/"
      "matched_products/offer_offY"
  )
  mock_firestore_client.get_all.return_value = [snap1, snap2]

  service.update_candidates([req1, req2])

  assert mock_firestore_client.transaction.call_count == 2


def test_calculate_candidate_deltas_transition_to_approved():
  """Test behavior when status changes from UNREVIEWED to APPROVED."""
  cand = candidate.Candidate(
      video_analysis_uuid="V1",
      identified_product_uuid="IDP1",
      candidate_offer_id="O1",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="u1", is_added_by_user=False
      ),
  )
  snapshot = create_mock_snapshot(
      "videos/video_V1/identified_products/idp_IDP1/matched_products/offer_O1",
      data_dictionary={"candidate_status": "UNREVIEWED"},
  )
  # pylint: disable=protected-access
  delta_approved, delta_matched = firestore_service._calculate_candidate_deltas(
      cand, snapshot
  )
  # pylint: enable=protected-access
  assert delta_approved == 1
  assert delta_matched == 0


def test_calculate_candidate_deltas_snapshot_missing_status():
  """Test fallback to UNREVIEWED when snapshot lacks status."""
  cand = candidate.Candidate(
      video_analysis_uuid="V1",
      identified_product_uuid="IDP1",
      candidate_offer_id="O1",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="u1", is_added_by_user=False
      ),
  )
  snapshot = create_mock_snapshot(
      "videos/video_V1/identified_products/idp_IDP1/matched_products/offer_O1",
      data_dictionary={},
  )
  # pylint: disable=protected-access
  delta_approved, delta_matched = firestore_service._calculate_candidate_deltas(
      cand, snapshot
  )
  # pylint: enable=protected-access
  assert delta_approved == 1
  assert delta_matched == 0


def test_derive_video_status_ready_to_push():
  """Test that 'Ready to Push' is returned when approved count > 0."""
  active_pushes = {}
  status = firestore_service._derive_video_status(active_pushes, False, 5)  # pylint: disable=protected-access
  assert status == "Ready to Push"


def test_derive_video_status_priority_waterfall():
  """Test priority: Active Pushes > Successful Push > Has Approved."""
  active_pushes = {"req_1": "timestamp"}
  status = firestore_service._derive_video_status(active_pushes, True, 5)  # pylint: disable=protected-access
  assert status == "Push in Progress"

  active_pushes = {}
  status = firestore_service._derive_video_status(active_pushes, True, 5)  # pylint: disable=protected-access
  assert status == "Push Complete"
