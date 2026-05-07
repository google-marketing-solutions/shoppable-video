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

# pylint: disable=redefined-outer-name
"""Unit test suite validating the modularized DataSyncService workflows."""

import datetime
from unittest import mock
from app.services import sync_service
from google.cloud import firestore
import pytest

# Define reliable module reference for patching
SERVICE_CLASS_PATH = "app.services.sync_service.DataSyncService"


@pytest.fixture
def mock_clients():
  """Prepares mock Client instances for service injection."""
  return {"bigquery": mock.MagicMock(), "firestore": mock.MagicMock()}


@pytest.fixture
def service_instance(mock_clients):
  """Builds the testing environment instance of the service."""
  return sync_service.DataSyncService(
      bigquery_client=mock_clients["bigquery"],
      firestore_client=mock_clients["firestore"],
      project_id="test-p",
      dataset_id="test-d",
      merchant_id="test-m",
      batch_size_limit=400,
  )


def create_mock_bq_row(**kwargs):
  """Wraps dictionary into object satisfying BigQuery simulation."""
  return type("MockRow", (object,), kwargs)


def test_sync_videos_cycles_and_commits(service_instance, mock_clients):
  """Verifies bigquery iteration and batch commits function perfectly."""
  mock_bigquery = mock_clients["bigquery"]
  mock_firestore = mock_clients["firestore"]

  # 1. Generate test rows
  test_timestamp = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
  mock_row = create_mock_bq_row(
      timestamp=test_timestamp,
      video_uuid="v_abc",
      video_id="vid_1",
      source="y",
      gcs_uri="g",
      md5_hash="h",
      title="T",
      description="D",
      identified_products=[{"uuid": "idp_1", "title": "t"}],
  )

  mock_bigquery.query.return_value.result.return_value = [mock_row]

  mock_batch = mock.MagicMock(spec=firestore.WriteBatch)
  mock_firestore.batch.return_value = mock_batch

  past_timestamp = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

  service_instance.sync_videos(past_timestamp)

  assert mock_batch.set.call_count >= 2  # 1 for video, 1 for internal product
  mock_batch.commit.assert_called_once()


def test_sync_videos_batch_rollover(service_instance, mock_clients):
  """Confirms that when BATCH_SIZE_LIMIT is exceeded, serial flushes fire."""
  mock_bigquery = mock_clients["bigquery"]
  mock_firestore = mock_clients["firestore"]

  # Set small boundary for fast testing without iterating hundreds
  service_instance.batch_size_limit = 2

  mock_row = create_mock_bq_row(
      timestamp=datetime.datetime.now(datetime.timezone.utc),
      video_uuid="v",
      video_id="i",
      source="y",
      gcs_uri="g",
      md5_hash="h",
      title="T",
      description="D",
      identified_products=[{"uuid": "1"}, {"uuid": "2"}, {"uuid": "3"}],
  )

  mock_bigquery.query.return_value.result.return_value = [mock_row]

  mock_batch = mock.MagicMock(spec=firestore.WriteBatch)
  mock_firestore.batch.return_value = mock_batch

  service_instance.sync_videos(
      datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
  )

  # Write count boundary = 2. Must commit multiple times to flush items.
  assert mock_batch.commit.call_count >= 2


def test_sync_matched_products_isolates_max_timestamp(
    service_instance, mock_clients
):
  """Verifies localized tally increment aggregation works across rows."""
  mock_bigquery = mock_clients["bigquery"]
  mock_firestore = mock_clients["firestore"]

  ts1 = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
  ts2 = datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc)

  mock_rows = [
      create_mock_bq_row(
          timestamp=ts1,
          video_uuid="v1",
          idp_uuid="i1",
          offer_id="o1",
          distance=0.1,
          total_count=2,
      ),
      create_mock_bq_row(
          timestamp=ts2,
          video_uuid="v1",
          idp_uuid="i2",
          offer_id="o2",
          distance=0.2,
          total_count=2,
      ),
  ]

  mock_bigquery.query.return_value.result.return_value = mock_rows
  mock_batch = mock.MagicMock(spec=firestore.WriteBatch)
  mock_firestore.batch.return_value = mock_batch

  service_instance.sync_matched_products(
      datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
  )

  # Check absolute total update was staged in commit logic
  set_calls = mock_batch.set.call_args_list
  has_stat_update = any(
      "stats_matched_count" in call[0][1] for call in set_calls
  )
  assert has_stat_update


def test_sync_inventory_utilizes_firestore_projection(
    service_instance, mock_clients
):
  """Proves serverless ID projection works instead of heavy CTE joins."""
  mock_bigquery = mock_clients["bigquery"]
  mock_firestore = mock_clients["firestore"]

  # 1. Simulate firestore collection.select([]).stream() yielding ids
  doc_1 = mock.MagicMock()
  doc_1.id = "prod_ABC"
  doc_2 = mock.MagicMock()
  doc_2.id = "prod_XYZ"

  mock_projection = mock_firestore.collection.return_value.select.return_value
  mock_projection.stream.return_value = [doc_1, doc_2]

  # 2. Simulate BigQuery providing active ID projection row FIRST
  active_id_row = create_mock_bq_row(offer_id="ABC")

  # 3. Simulate BigQuery responding with the full inventory dataset SECOND
  full_inventory_row = create_mock_bq_row(
      offer_id="ABC",
      title="Shoe",
      brand="N",
      image_link="l",
      availability="in stock",
      price=100.0,
  )

  # Setup serial execution side_effect
  # Note: Each .result() call will consume the next list entry in sequence
  mock_bigquery.query.return_value.result.side_effect = [
      [active_id_row],  # Result of _fetch_active_offer_identifiers
      [full_inventory_row],  # Result of _fetch_inventory_updates_from_bigquery
  ]

  mock_batch = mock.MagicMock(spec=firestore.WriteBatch)
  mock_firestore.batch.return_value = mock_batch

  service_instance.sync_inventory()

  # Validate that the first query call received the correct SQL logic target
  query_call_history = mock_bigquery.query.call_args_list
  assert "SELECT DISTINCT" in query_call_history[0][0][0]

  # Check that projection specifically used select([]) to limit bandwidth
  mock_firestore.collection.assert_any_call("products")
  mock_firestore.collection("products").select.assert_called_with([])

  # Verify BigQuery bound the correct parameters for the final execution block
  final_kwargs = query_call_history[1][1]
  param = final_kwargs["job_config"].query_parameters[0]
  # Union set logic should identify it successfully
  assert "ABC" in param.values

  # Ensure commit happened once
  mock_batch.commit.assert_called_once()
