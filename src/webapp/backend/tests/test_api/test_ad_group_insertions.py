"""Integration tests for ad group insertion routes."""

from unittest import mock

from app.api import dependencies
from app.main import app
from app.models import ad_group_insertion as model
from app.models import video as video_model
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


def test_get_all_ad_group_insertion_statuses_success(client, mock_bq_service):
  """Test successful retrieval of all ad group insertion statuses."""
  mock_paginated = model.PaginatedAdGroupInsertionStatus(
      items=[], total_count=0, limit=10, offset=0
  )
  mock_bq_service.get_all_ad_group_insertion_statuses.return_value = (
      mock_paginated
  )

  response = client.get("/api/ad-group-insertions/status?limit=10&offset=0")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == mock_paginated.model_dump(mode="json")

  expected_params = video_model.PaginationParams(limit=10, offset=0)
  mock_bq_service.get_all_ad_group_insertion_statuses.assert_called_once_with(
      expected_params
  )


def test_get_all_ad_group_insertion_statuses_error(client, mock_bq_service):
  """Test retrieval of all ad group insertion statuses fails gracefully."""
  mock_bq_service.get_all_ad_group_insertion_statuses.side_effect = Exception(
      "BQ Error"
  )

  response = client.get("/api/ad-group-insertions/status")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert "BQ Error" in response.json()["detail"]


def test_get_ad_group_insertion_status_success(client, mock_bq_service):
  """Test successful retrieval of status by request UUID."""
  mock_status = []
  mock_bq_service.get_ad_group_insertion_status.return_value = mock_status

  response = client.get("/api/ad-group-insertions/status/req-123")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == mock_status
  mock_bq_service.get_ad_group_insertion_status.assert_called_once_with(
      "req-123"
  )


def test_get_ad_group_insertion_status_error(client, mock_bq_service):
  """Test retrieval of status by request UUID fails gracefully."""
  mock_bq_service.get_ad_group_insertion_status.side_effect = Exception(
      "BQ Error"
  )

  response = client.get("/api/ad-group-insertions/status/req-123")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert "BQ Error" in response.json()["detail"]


def test_get_ad_group_insertion_statuses_for_video_success(
    client, mock_bq_service
):
  """Test successful retrieval of statuses for a specific video."""
  mock_status = []
  mock_bq_service.get_ad_group_insertion_statuses_for_video.return_value = (
      mock_status
  )

  response = client.get("/api/ad-group-insertions/status/video/vid-123")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == mock_status

  # Ensure the line is broken to respect 80 char limit
  mock_method = mock_bq_service.get_ad_group_insertion_statuses_for_video
  mock_method.assert_called_once_with("vid-123")


def test_get_ad_group_insertion_statuses_for_video_error(
    client, mock_bq_service
):
  """Test retrieval of statuses for a specific video fails gracefully."""
  mock_bq_service.get_ad_group_insertion_statuses_for_video.side_effect = (
      Exception("BQ Error")
  )

  response = client.get("/api/ad-group-insertions/status/video/vid-123")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert "BQ Error" in response.json()["detail"]
