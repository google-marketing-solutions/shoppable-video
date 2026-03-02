"""Integration tests for reports routes."""

from unittest import mock

from app.api import dependencies
from app.main import app
from fastapi import status
import pytest


@pytest.fixture(name="mock_ga_service")
def fixture_mock_ga_service():
  """Fixture to provide a mocked Google Ads service."""
  return mock.Mock()


@pytest.fixture(name="mock_session_data")
def fixture_mock_session_data():
  """Fixture to provide mock session data."""
  return {"email": "test@example.com", "rt": "mock_refresh_token"}


@pytest.fixture(name="override_dependencies", autouse=True)
def fixture_override_dependencies(mock_ga_service, mock_session_data):
  """Fixture to override FastAPI dependencies for testing."""
  app.dependency_overrides[dependencies.get_session_data] = (
      lambda: mock_session_data
  )
  app.dependency_overrides[dependencies.get_google_ads_service] = (
      lambda: mock_ga_service
  )
  yield
  app.dependency_overrides.clear()


def test_get_campaigns_success(client, mock_ga_service):
  """Test successful retrieval of campaigns."""
  mock_data = [{"id": "123", "name": "Campaign 1"}]
  mock_ga_service.get_campaigns.return_value = mock_data

  response = client.get("/api/reports/campaigns/customer-1")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == {"data": mock_data}
  mock_ga_service.get_campaigns.assert_called_once_with()


def test_get_campaigns_error(client, mock_ga_service):
  """Test retrieval of campaigns fails gracefully."""
  mock_ga_service.get_campaigns.side_effect = Exception("API Error")

  response = client.get("/api/reports/campaigns/customer-1")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert response.json()["detail"] == "API Error"
  mock_ga_service.get_campaigns.assert_called_once_with()


def test_get_ad_groups_success(client, mock_ga_service):
  """Test successful retrieval of ad groups."""
  mock_data = [{"id": "ag-1", "name": "Ad Group 1"}]
  mock_ga_service.get_ad_groups.return_value = mock_data

  response = client.get("/api/reports/ad-groups/campaign-1")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == mock_data
  mock_ga_service.get_ad_groups.assert_called_once_with("campaign-1")


def test_get_ad_groups_error(client, mock_ga_service):
  """Test retrieval of ad groups fails gracefully."""
  mock_ga_service.get_ad_groups.side_effect = Exception("API Error")

  response = client.get("/api/reports/ad-groups/campaign-1")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert response.json()["detail"] == "API Error"
  mock_ga_service.get_ad_groups.assert_called_once_with("campaign-1")
