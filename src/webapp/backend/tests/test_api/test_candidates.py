"""Integration tests for candidate routes."""

from unittest import mock

from app.api import dependencies
from app.main import app
from app.models import candidate as candidate_model
from fastapi import status
import pytest


@pytest.fixture(name="mock_bq_service")
def fixture_mock_bq_service():
  """Fixture to provide a mocked BigQuery service."""
  return mock.Mock()


@pytest.fixture(name="mock_session_data")
def fixture_mock_session_data():
  """Fixture to provide mock session data."""
  return {"email": "test@example.com", "rt": "mock_refresh_token"}


@pytest.fixture(name="override_dependencies", autouse=True)
def fixture_override_dependencies(mock_bq_service, mock_session_data):
  """Fixture to override FastAPI dependencies for testing."""
  app.dependency_overrides[dependencies.get_session_data] = (
      lambda: mock_session_data
  )
  app.dependency_overrides[dependencies.get_bigquery_service] = (
      lambda: mock_bq_service
  )
  yield
  app.dependency_overrides.clear()


def test_update_candidates_success(client, mock_bq_service):
  """Test successful update of candidates."""
  candidate_data = {
      "video_analysis_uuid": "va-123",
      "identified_product_uuid": "ip-123",
      "candidate_offer_id": "offer-1",
      "candidate_status": {
          "status": "APPROVED",
          "user": "test@example.com",
          "is_added_by_user": False,
      },
  }

  response = client.post("/api/candidates/update", json=[candidate_data])

  assert response.status_code == status.HTTP_201_CREATED
  assert response.json() == {"message": "1 Candidate updated successfully"}

  # Validate the mock was called correctly
  mock_bq_service.update_candidates.assert_called_once()
  args, _ = mock_bq_service.update_candidates.call_args
  assert len(args[0]) == 1
  assert isinstance(args[0][0], candidate_model.Candidate)
  assert args[0][0].video_analysis_uuid == "va-123"


def test_update_candidates_error(client, mock_bq_service):
  """Test update of candidates fails gracefully."""
  candidate_data = {
      "video_analysis_uuid": "va-123",
      "identified_product_uuid": "ip-123",
      "candidate_offer_id": "offer-1",
      "candidate_status": {
          "status": "APPROVED",
          "user": "test@example.com",
          "is_added_by_user": False,
      },
  }

  mock_bq_service.update_candidates.side_effect = Exception("BQ Error")

  response = client.post("/api/candidates/update", json=[candidate_data])

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert "BQ Error" in response.json()["detail"]


def test_insert_submission_requests_success(client, mock_bq_service):
  """Test successful insertion of submission requests."""
  request_data = {
      "request_uuid": "req-123",
      "video_uuid": "vid-123",
      "offer_ids": "offer-1,offer-2",
      "destinations": [{
          "ad_group_id": "ag-1",
          "campaign_id": "camp-1",
          "customer_id": "cust-1",
          "ad_group_name": "Test AG",
      }],
      "submitting_user": "test@example.com",
      "cpc": 1.5,
  }

  response = client.post(
      "/api/candidates/submission-requests", json=[request_data]
  )

  assert response.status_code == status.HTTP_201_CREATED
  assert response.json() == {
      "message": "1 Submission Request inserted successfully"
  }

  expected_request = candidate_model.SubmissionMetadata(
      request_uuid="req-123",
      video_uuid="vid-123",
      offer_ids="offer-1,offer-2",
      destinations=[
          candidate_model.Destination(
              ad_group_id="ag-1",
              campaign_id="camp-1",
              customer_id="cust-1",
              ad_group_name="Test AG",
          )
      ],
      submitting_user="test@example.com",
      cpc=1.5,
  )
  mock_bq_service.insert_submission_requests.assert_called_once_with(
      [expected_request]
  )


def test_insert_submission_requests_error(client, mock_bq_service):
  """Test insertion of submission requests fails gracefully."""
  request_data = {
      "request_uuid": "req-123",
      "video_uuid": "vid-123",
      "offer_ids": "offer-1,offer-2",
      "destinations": [{
          "ad_group_id": "ag-1",
          "campaign_id": "camp-1",
          "customer_id": "cust-1",
      }],
      "submitting_user": "test@example.com",
  }

  mock_bq_service.insert_submission_requests.side_effect = Exception("BQ Error")

  response = client.post(
      "/api/candidates/submission-requests", json=[request_data]
  )

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert "BQ Error" in response.json()["detail"]


def test_insert_submission_requests_multi_destinations(client, mock_bq_service):
  """Test successful insertion of multi-destination submission requests."""
  request_data = {
      "request_uuid": "req-123",
      "video_uuid": "vid-123",
      "offer_ids": "offer-1",
      "destinations": [
          {
              "ad_group_id": "ag-1",
              "campaign_id": "camp-1",
              "customer_id": "cust-1",
              "ad_group_name": "Test AG 1",
          },
          {
              "ad_group_id": "ag-2",
              "campaign_id": "camp-2",
              "customer_id": "cust-2",
              "ad_group_name": "Test AG 2",
          },
      ],
      "submitting_user": "test@example.com",
      "cpc": 1.5,
  }

  response = client.post(
      "/api/candidates/submission-requests", json=[request_data]
  )

  assert response.status_code == status.HTTP_201_CREATED

  expected_request = candidate_model.SubmissionMetadata(
      request_uuid="req-123",
      video_uuid="vid-123",
      offer_ids="offer-1",
      destinations=[
          candidate_model.Destination(
              ad_group_id="ag-1",
              campaign_id="camp-1",
              customer_id="cust-1",
              ad_group_name="Test AG 1",
          ),
          candidate_model.Destination(
              ad_group_id="ag-2",
              campaign_id="camp-2",
              customer_id="cust-2",
              ad_group_name="Test AG 2",
          ),
      ],
      submitting_user="test@example.com",
      cpc=1.5,
  )
  mock_bq_service.insert_submission_requests.assert_called_once_with(
      [expected_request]
  )
