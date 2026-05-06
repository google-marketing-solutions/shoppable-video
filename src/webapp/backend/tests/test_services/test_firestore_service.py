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
  mock_firestore_client.batch.assert_not_called()


def test_update_candidates_success_no_user_add(
    service, mock_firestore_client, mock_registry
):
  """Tests internal system candidates transition successfully to persistence."""
  req = candidate.Candidate(
      video_analysis_uuid="123",
      identified_product_uuid="ABC",
      candidate_offer_id="XYZ",
      candidate_status=candidate.CandidateStatus(
          status="APPROVED", user="me", is_added_by_user=False
      ),
  )

  path = (
      "videos/video_123/identified_products/idp_ABC/matched_products/offer_XYZ"
  )
  state_snap = create_mock_snapshot(
      path, data_dictionary={"candidate_status": "UNREVIEWED"}
  )
  state_snap.reference = mock_registry.get_reference(path)

  mock_firestore_client.get_all.return_value = [state_snap]
  mock_batch = mock_firestore_client.batch.return_value

  service.update_candidates([req])

  calls = mock_batch.set.call_args_list
  assert len(calls) >= 2


def test_update_candidates_batch_limit_trigger(service, mock_firestore_client):
  """Verifies batch flushes are invoked when exceeding limit bound."""
  candidates_pool = []
  for i in range(5):
    candidates_pool.append(
        candidate.Candidate(
            video_analysis_uuid=f"v_{i}",
            identified_product_uuid=f"i_{i}",
            candidate_offer_id=f"o_{i}",
            candidate_status=candidate.CandidateStatus(
                status="APPROVED", user="t", is_added_by_user=False
            ),
        )
    )

  mock_firestore_client.get_all.return_value = []
  mock_batch = mock_firestore_client.batch.return_value

  original_init = firestore_service.FirestoreBatchManager.__init__

  def mock_init(self, db, limit=2):
    original_init(self, db, limit=limit)

  with mock.patch.object(
      firestore_service.FirestoreBatchManager, "__init__", mock_init
  ):
    service.update_candidates(candidates_pool)

  assert mock_batch.commit.call_count >= 2


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
      video.PaginationParams(limit=10)
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
  path = (
      "videos/video_V1/identified_products/idp_IDP1/matched_products/"
      "offer_PROD1"
  )
  state_snap = create_mock_snapshot(path, data_dictionary={})
  state_snap.reference = mock_registry.get_reference(path)

  mock_firestore_client.get_all.return_value = [state_snap]
  mock_batch = mock_firestore_client.batch.return_value

  service.update_candidates([req])

  assert mock_batch.set.call_count >= 3


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
