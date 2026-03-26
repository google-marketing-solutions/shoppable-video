"""Unit tests for bigquery_service."""

import datetime
from unittest import mock
from app.models import candidate as candidate_model
from app.models import video as video_model
from app.services import bigquery_service
import pytest


@pytest.fixture(name="mock_bq_client")
def fixture_mock_bq_client():
  with mock.patch("google.cloud.bigquery.Client") as mock_client:
    yield mock_client.return_value


@pytest.fixture(name="service")
def fixture_service(mock_bq_client):
  """Create a BigQueryService instance for testing."""
  # Mocking _load_queries to avoid filesystem dependency
  with mock.patch.object(bigquery_service.BigQueryService, "_load_queries"):
    table_ids = {
        "video_analysis_table_id": "video_analysis",
        "matched_products_table_id": "matched_products",
        "matched_products_view_id": "matched_products_view",
        "candidate_status_table_id": "candidate_status",
        "candidate_status_view_id": "candidate_status_view",
        "google_ads_insertion_requests_table_id": "submission_requests",
        "ad_group_insertion_status_table_id": "insertion_status",
    }
    svc = bigquery_service.BigQueryService(
        project_id="test-project",
        dataset_id="test_dataset",
        table_ids=table_ids,
        client=mock_bq_client,
    )
    svc.queries = {
        "get_video_analysis": "SELECT * FROM video_analysis",
        "get_video_analysis_summary": "SELECT * FROM summary",
        "get_all_ad_group_insertion_statuses": "SELECT * FROM statuses",
        "get_ad_groups_for_video": (
            "SELECT * FROM ad_groups WHERE customer_id={customer_id}"
        ),
        "get_campaigns_for_video": (
            "SELECT campaign_id FROM campaigns WHERE customer_id={customer_id}"
        ),
    }
    return svc


def test_init_missing_table_ids(mock_bq_client):
  """Test that initialization fails if required table_ids are missing."""
  table_ids = {"video_analysis_table_id": "video_analysis"}
  with pytest.raises(ValueError, match="Missing required table IDs"):
    bigquery_service.BigQueryService(
        project_id="test-project",
        dataset_id="test_dataset",
        table_ids=table_ids,
        client=mock_bq_client,
    )


def test_get_video_analysis_not_found(service, mock_bq_client):
  """Test get_video_analysis when no results are found."""
  mock_query_job = mock.Mock()
  mock_query_job.result.return_value = []
  mock_bq_client.query.return_value = mock_query_job

  result = service.get_video_analysis("nonexistent-uuid")

  assert result is None
  mock_bq_client.query.assert_called_once()


def test_get_video_analysis_success(service, mock_bq_client):
  """Test get_video_analysis when results are found."""
  mock_query_job = mock.Mock()
  mock_row = {
      "video": {
          "uuid": "vid-1",
          "source": "google_ads",
          "video_id": "yt-1",
          "metadata": None,
          "gcs_uri": None,
          "md5_hash": None,
      },
      "identified_products": [],
  }
  mock_query_job.result.return_value = [mock_row]
  mock_bq_client.query.return_value = mock_query_job

  result = service.get_video_analysis("vid-1")

  assert result is not None
  assert result.video.uuid == "vid-1"
  mock_bq_client.query.assert_called_once()
  args, kwargs = mock_bq_client.query.call_args
  assert args[0] == "SELECT * FROM video_analysis"
  assert len(kwargs["job_config"].query_parameters) == 1


def test_get_video_analysis_summary_success(service, mock_bq_client):
  """Test get_video_analysis_summary when results are found."""
  mock_query_job = mock.Mock()
  mock_row = {
      "video": {
          "uuid": "vid-1",
          "source": "google_ads",
          "video_id": "yt-1",
          "metadata": None,
          "gcs_uri": None,
          "md5_hash": None,
      },
      "identified_products_count": 5,
      "matched_products_count": 3,
      "approved_products_count": 1,
      "disapproved_products_count": 0,
      "unreviewed_products_count": 2,
      "total_count": 100,
  }
  mock_query_job.result.return_value = [mock_row]
  mock_bq_client.query.return_value = mock_query_job

  params = video_model.PaginationParams(limit=10, offset=0)
  result = service.get_video_analysis_summary(params)

  assert result is not None
  assert result.total_count == 100
  assert len(result.items) == 1
  assert result.items[0].video.uuid == "vid-1"
  mock_bq_client.query.assert_called_once()


def test_get_ad_groups_for_video(service, mock_bq_client):
  """Test get_ad_groups_for_video returns mapped dictionaries."""
  mock_query_job = mock.Mock()
  mock_row = {"ad_group_id": 123, "name": "Test Ad Group"}
  mock_query_job.result.return_value = [mock_row]
  mock_bq_client.query.return_value = mock_query_job

  result = service.get_ad_groups_for_video("yt-1", 1234567890)

  assert len(result) == 1
  assert result[0] == {"ad_group_id": 123, "name": "Test Ad Group"}
  mock_bq_client.query.assert_called_once()
  args, _ = mock_bq_client.query.call_args
  assert "customer_id=1234567890" in args[0]


def test_get_campaigns_for_video(service, mock_bq_client):
  """Test get_campaigns_for_video returns list of strings."""
  mock_query_job = mock.Mock()
  mock_row1 = {"campaign_id": 111}
  mock_row2 = {"campaign_id": 222}
  mock_row3 = {"campaign_id": None}  # Should be filtered out
  mock_query_job.result.return_value = [mock_row1, mock_row2, mock_row3]
  mock_bq_client.query.return_value = mock_query_job

  result = service.get_campaigns_for_video("yt-1", 1234567890)

  assert len(result) == 2
  assert result == [111, 222]
  mock_bq_client.query.assert_called_once()


def test_insert_submission_requests(service, mock_bq_client):
  """Test inserting submission requests."""
  destinations = [
      candidate_model.Destination(customer_id=3, campaign_id=2, ad_group_id=1)
  ]
  request = candidate_model.SubmissionMetadata(
      request_uuid="req-1",
      video_uuid="vid-1",
      offer_ids="offer-1",
      destinations=destinations,
      submitting_user="user@example.com",
      cpc=1.5,
  )

  mock_bq_client.insert_rows_json.return_value = []
  service.insert_submission_requests([request])
  mock_bq_client.insert_rows_json.assert_called_once()

  # Check that the correct table ID was requested
  mock_bq_client.dataset.assert_called_with("test_dataset")
  mock_bq_client.dataset.return_value.table.assert_called_with(
      "submission_requests"
  )
  args, _ = mock_bq_client.insert_rows_json.call_args

  expected_subset = {
      "request_uuid": "req-1",
      "video_uuid": "vid-1",
      "offer_ids": ["offer-1"],
      "submitting_user": "user@example.com",
      "cpc": 1.5,
      "cpc_bid_micros": 1500000,
      "destinations": [{
          "adgroup_id": 1,
          "campaign_id": 2,
          "ads_customer_id": 3,
      }],
  }

  inserted_rows = args[1]
  assert len(inserted_rows) == 1
  row = inserted_rows[0]

  for key, val in expected_subset.items():
    assert row[key] == val

  assert "timestamp" in row
  datetime.datetime.fromisoformat(row.pop("timestamp"))


def test_update_candidates_valid(service, mock_bq_client):
  """Test updating candidate statuses."""
  candidates = [
      candidate_model.Candidate(
          video_analysis_uuid="va-1",
          identified_product_uuid="ip-1",
          candidate_offer_id="offer-1",
          candidate_status=candidate_model.CandidateStatus(
              status=candidate_model.Status.APPROVED,
              user="user@example.com",
              is_added_by_user=False,
          ),
      )
  ]

  mock_bq_client.insert_rows_json.return_value = []
  service.update_candidates(candidates)
  mock_bq_client.insert_rows_json.assert_called_once()

  # Check that the correct table ID was requested
  mock_bq_client.dataset.assert_called_with("test_dataset")
  mock_bq_client.dataset.return_value.table.assert_called_with(
      "candidate_status"
  )
  args, _ = mock_bq_client.insert_rows_json.call_args

  # Verify inserted row content via dict comparison
  inserted_rows = args[1]
  assert len(inserted_rows) == 1
  row = inserted_rows[0]

  # We check most fields via dict comparison,
  # handling the dynamic timestamp separately
  expected_subset = {
      "video_analysis_uuid": "va-1",
      "identified_product_uuid": "ip-1",
      "candidate_offer_id": "offer-1",
      "status": "APPROVED",
      "user": "user@example.com",
      "is_added_by_user": False,
  }

  # Verify subset matches
  for key, val in expected_subset.items():
    assert row[key] == val

  # Verify timestamp presence and format
  assert "modified_timestamp" in row
  datetime.datetime.fromisoformat(row.pop("modified_timestamp"))


def test_get_all_ad_group_insertion_statuses_empty(service, mock_bq_client):
  """Test get_all_ad_group_insertion_statuses when no results are found."""
  mock_query_job = mock.Mock()
  mock_query_job.result.return_value = []
  mock_bq_client.query.return_value = mock_query_job

  params = video_model.PaginationParams(limit=10, offset=0)
  result = service.get_all_ad_group_insertion_statuses(params)

  assert result is not None
  assert result.total_count == 0
  assert len(result.items) == 0
  mock_bq_client.query.assert_called_once()
