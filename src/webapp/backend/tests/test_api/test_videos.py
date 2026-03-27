"""Integration tests for video analysis routes."""

from unittest import mock

from app.api import dependencies
from app.core.config import settings
from app.main import app
from app.models import video as video_model
from fastapi import status
import pytest


@pytest.fixture(name="mock_bq_service")
def fixture_mock_bq_service():
  """Fixture to provide a mocked BigQuery service."""
  return mock.Mock()


@pytest.fixture(name="mock_ga_service")
def fixture_mock_ga_service():
  """Fixture to provide a mocked Google Ads service."""
  return mock.Mock()


@pytest.fixture(name="mock_session_data")
def fixture_mock_session_data():
  """Fixture to provide mock session data."""
  return {"email": "test@example.com", "rt": "mock_refresh_token"}


@pytest.fixture(name="override_dependencies", autouse=True)
def fixture_override_dependencies(
    mock_bq_service, mock_session_data, mock_ga_service
):
  """Fixture to override FastAPI dependencies for testing."""
  app.dependency_overrides[dependencies.get_session_data] = (
      lambda: mock_session_data
  )
  app.dependency_overrides[dependencies.get_bigquery_service] = (
      lambda: mock_bq_service
  )
  app.dependency_overrides[dependencies.get_google_ads_service] = (
      lambda: mock_ga_service
  )
  yield
  app.dependency_overrides.clear()


def test_get_video_analysis_summary_success(client, mock_bq_service):
  """Test successful retrieval of video analysis summaries."""
  mock_summary = video_model.PaginatedVideoAnalysisSummary(
      items=[], total_count=0, limit=10, offset=0
  )
  mock_bq_service.get_video_analysis_summary.return_value = mock_summary

  response = client.get("/api/videos/analysis/summary?limit=10&offset=0")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == mock_summary.model_dump(mode="json")

  expected_params = video_model.PaginationParams(limit=10, offset=0)
  mock_bq_service.get_video_analysis_summary.assert_called_once_with(
      expected_params
  )


def test_get_video_analysis_summary_error(client, mock_bq_service):
  """Test retrieval of video analysis summaries fails gracefully."""
  mock_bq_service.get_video_analysis_summary.side_effect = Exception(
      "API Error"
  )

  response = client.get("/api/videos/analysis/summary?limit=10&offset=0")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert "API Error" in response.json()["detail"]


def test_get_video_analysis_by_id_success(client, mock_bq_service):
  """Test successful retrieval of a video analysis record by ID."""
  mock_analysis = video_model.VideoAnalysis(
      video=video_model.Video(uuid="vid-1", source="google_ads"),
      identified_products=[],
  )
  mock_bq_service.get_video_analysis.return_value = mock_analysis

  response = client.get("/api/videos/analysis/vid-1")

  assert response.status_code == status.HTTP_200_OK
  assert response.json()["video"]["uuid"] == "vid-1"

  mock_bq_service.get_video_analysis.assert_called_once_with("vid-1")


def test_get_video_analysis_by_id_not_found(client, mock_bq_service):
  """Test retrieval of a non-existent video analysis record."""
  mock_bq_service.get_video_analysis.return_value = None

  response = client.get("/api/videos/analysis/nonexistent")

  assert response.status_code == status.HTTP_404_NOT_FOUND
  assert response.json()["detail"] == "Record not found"

  mock_bq_service.get_video_analysis.assert_called_once_with("nonexistent")


def test_get_video_analysis_by_id_error(client, mock_bq_service):
  """Test retrieval of a video analysis record by ID fails gracefully."""
  mock_bq_service.get_video_analysis.side_effect = Exception("API Error")

  response = client.get("/api/videos/analysis/vid-1")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert "API Error" in response.json()["detail"]


def test_get_ad_groups_for_video_success(
    client, mock_bq_service, mock_ga_service
):
  """Test successful retrieval of ad groups for a video."""
  mock_analysis = video_model.VideoAnalysis(
      video=video_model.Video(
          uuid="vid-1", source="google_ads", video_id="yt-1"
      ),
      identified_products=[],
  )
  mock_bq_service.get_video_analysis.return_value = mock_analysis
  mock_bq_service.get_campaigns_for_video.return_value = ["camp-1"]

  mock_ga_service.get_ad_groups.return_value = [
      {"id": "ag-1", "name": "Ad Group 1"}
  ]

  original_customer_id = settings.GOOGLE_ADS_CUSTOMER_ID
  settings.GOOGLE_ADS_CUSTOMER_ID = 999888777

  try:
    response = client.get("/api/videos/analysis/vid-1/ad-groups")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{"id": "ag-1", "name": "Ad Group 1"}]

    mock_bq_service.get_video_analysis.assert_called_once_with("vid-1")
    mock_bq_service.get_campaigns_for_video.assert_called_once_with(
        "yt-1", "test-customer-id"
    )
    mock_ga_service.get_ad_groups.assert_called_once_with("camp-1")
  finally:
    settings.GOOGLE_ADS_CUSTOMER_ID = original_customer_id


def test_get_ad_groups_for_video_not_found(client, mock_bq_service):
  """Test retrieval of ad groups fails if video analysis is missing."""
  mock_bq_service.get_video_analysis.return_value = None

  response = client.get("/api/videos/analysis/vid-1/ad-groups")

  assert response.status_code == status.HTTP_404_NOT_FOUND
  assert response.json()["detail"] == "Video Analysis or Video ID not found"
  mock_bq_service.get_video_analysis.assert_called_once_with("vid-1")


def test_get_ad_groups_for_video_error(client, mock_bq_service):
  """Test retrieval of ad groups handles API errors gracefully."""
  mock_analysis = video_model.VideoAnalysis(
      video=video_model.Video(
          uuid="vid-1", source="google_ads", video_id="yt-1"
      ),
      identified_products=[],
  )
  mock_bq_service.get_video_analysis.return_value = mock_analysis
  mock_bq_service.get_campaigns_for_video.side_effect = Exception("API Error")

  response = client.get("/api/videos/analysis/vid-1/ad-groups")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert "API Error" in response.json()["detail"]
