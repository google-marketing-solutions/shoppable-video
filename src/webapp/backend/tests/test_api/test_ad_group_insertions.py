"""Integration tests for ad group insertion routes."""

import datetime
from unittest import mock

from app.api import dependencies
from app.main import app
from app.models import ad_group_insertion as model
from fastapi import status
import pytest


@pytest.fixture(name="mock_fs_service")
def fixture_mock_fs_service():
  """Fixture to provide a mocked Firestore service."""
  return mock.Mock()


@pytest.fixture(name="mock_ga_service")
def fixture_mock_ga_service():
  """Fixture to provide a mocked Google Ads service."""
  mock_service = mock.Mock()
  mock_service.get_ad_groups_metadata.return_value = [{
      "customer_id": 123,
      "customer_name": "Mock Customer",
      "campaign_id": 456,
      "campaign_name": "Mock Campaign",
      "ad_group_id": 789,
      "ad_group_name": "Mock Ad Group",
  }]
  return mock_service


@pytest.fixture(name="mock_session_data")
def fixture_mock_session_data():
  """Fixture to provide mock session data."""
  return {"email": "test@example.com", "rt": "mock_refresh_token"}


@pytest.fixture(name="override_dependencies", autouse=True)
def fixture_override_dependencies(
    mock_fs_service, mock_ga_service, mock_session_data
):
  """Fixture to override FastAPI dependencies for testing."""
  app.dependency_overrides[dependencies.get_session_data] = (
      lambda: mock_session_data
  )
  app.dependency_overrides[dependencies.get_firestore_service] = (
      lambda: mock_fs_service
  )
  app.dependency_overrides[dependencies.get_google_ads_service] = (
      lambda: mock_ga_service
  )
  yield
  app.dependency_overrides.clear()


def test_get_all_ad_group_insertion_statuses_success(client, mock_fs_service):
  """Test successful retrieval of all ad group insertion statuses."""
  mock_paginated = model.PaginatedAdGroupInsertionStatus(
      items=[], total_count=0, limit=10, offset=0
  )
  mock_fs_service.get_all_ad_group_insertion_statuses.return_value = (
      mock_paginated
  )

  response = client.get("/api/ad-group-insertions/status?limit=10&offset=0")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == mock_paginated.model_dump(mode="json")

  expected_params = model.AdGroupPaginationParams(limit=10, offset=0)
  mock_fs_service.get_all_ad_group_insertion_statuses.assert_called_once_with(
      expected_params
  )


def test_get_all_ad_group_insertion_statuses_with_enrichment(
    client, mock_fs_service, mock_ga_service
):
  """Test retrieval with user filter and entity enrichment."""
  mock_entity = model.AdsEntityStatus(
      customer_id=123,
      campaign_id=456,
      ad_group_id=789,
      products=[],
  )
  mock_item = model.AdGroupInsertionStatus(
      request_uuid="req-123",
      video_analysis_uuid="vid-123",
      submitting_user="test@example.com",
      status="SUCCESS",
      ads_entities=[mock_entity],
      timestamp=datetime.datetime.now(datetime.timezone.utc),
  )
  mock_paginated = model.PaginatedAdGroupInsertionStatus(
      items=[mock_item], total_count=1, limit=10, offset=0
  )
  mock_fs_service.get_all_ad_group_insertion_statuses.return_value = (
      mock_paginated
  )

  response = client.get(
      "/api/ad-group-insertions/status",
      params={"limit": 10, "offset": 0, "user_filter": "test@example.com"},
  )

  assert response.status_code == status.HTTP_200_OK
  data = response.json()
  assert len(data["items"]) == 1
  entity_data = data["items"][0]["ads_entities"][0]
  assert entity_data["customer_name"] == "Mock Customer"
  assert entity_data["campaign_name"] == "Mock Campaign"
  assert entity_data["ad_group_name"] == "Mock Ad Group"

  expected_params = model.AdGroupPaginationParams(
      limit=10, offset=0, user_filter="test@example.com"
  )
  mock_fs_service.get_all_ad_group_insertion_statuses.assert_called_once_with(
      expected_params
  )
  mock_ga_service.get_ad_groups_metadata.assert_called_once_with(
      [789], customer_id=123
  )


def test_get_ad_group_insertion_status_success(client, mock_fs_service):
  """Test successful retrieval of status by request UUID."""
  mock_status = []
  mock_fs_service.get_ad_group_insertion_status.return_value = mock_status

  response = client.get("/api/ad-group-insertions/status/req-123")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == mock_status
  mock_fs_service.get_ad_group_insertion_status.assert_called_once_with(
      "req-123"
  )


def test_get_ad_group_insertion_statuses_for_video_success(
    client, mock_fs_service
):
  """Test successful retrieval of statuses for a specific video."""
  mock_status = []
  mock_fs_service.get_ad_group_insertion_statuses_for_video.return_value = (
      mock_status
  )

  response = client.get("/api/ad-group-insertions/status/video/vid-123")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == mock_status

  # Ensure the line is broken to respect 80 char limit
  mock_method = mock_fs_service.get_ad_group_insertion_statuses_for_video
  mock_method.assert_called_once_with("vid-123")
