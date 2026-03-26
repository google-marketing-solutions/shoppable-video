"""Integration tests for reports routes."""

from unittest import mock

from app.api import dependencies
from app.core.config import settings
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
  app.dependency_overrides[dependencies.get_discovery_service] = (
      lambda: mock_ga_service
  )
  yield
  app.dependency_overrides.clear()


def test_get_accessible_customers_success(client, mock_ga_service):
  """Test successful retrieval of accessible customers."""
  mock_ga_service.list_accessible_customers.return_value = [
      "customers/111",
      "customers/222",
      "customers/333",
  ]
  # Mock that:
  # 111 is the platform MCC itself.
  # 222 is managed by 111 (Platform MCC).
  # 333 is not managed by 111.
  with mock.patch.object(settings, "GOOGLE_ADS_CUSTOMER_ID", "111"):
    mock_ga_service.get_customer_details.side_effect = [
        {"customer_id": "111", "descriptive_name": "Acc 1", "is_manager": True},
        {
            "customer_id": "222",
            "descriptive_name": "Acc 2",
            "is_manager": False,
        },
        {
            "customer_id": "333",
            "descriptive_name": "Acc 3",
            "is_manager": False,
        },
    ]

    response = client.get("/api/reports/accessible-customers")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert len(data) == 3

    assert data[0]["customer_id"] == "111"
    assert data[0]["is_platform_customer_id"]
    assert "managers" not in data[0]

    assert data[1]["customer_id"] == "222"
    assert not data[1]["is_platform_customer_id"]
    assert "managers" not in data[1]

    assert data[2]["customer_id"] == "333"
    assert not data[2]["is_platform_customer_id"]
    assert "managers" not in data[2]

    mock_ga_service.list_accessible_customers.assert_called_once_with()
    mock_ga_service.get_customer_details.assert_has_calls([
        mock.call("111"),
        mock.call("222"),
        mock.call("333"),
    ])


def test_get_accessible_customers_error(client, mock_ga_service):
  """Test retrieval of accessible customers handles errors."""
  mock_ga_service.list_accessible_customers.side_effect = Exception("API Error")

  response = client.get("/api/reports/accessible-customers")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert response.json()["detail"] == "API Error"
  mock_ga_service.list_accessible_customers.assert_called_once_with()


def test_get_sub_accounts_success(client, mock_ga_service):
  """Test successful retrieval of sub-accounts."""
  mock_ga_service.login_customer_id = 123456
  mock_data = [
      {"customer_id": 111, "descriptive_name": "Acc 1", "is_manager": False},
      {"customer_id": 222, "descriptive_name": "Acc 2", "is_manager": False},
  ]
  mock_ga_service.list_accessible_subaccounts.return_value = mock_data

  response = client.get("/api/reports/sub-accounts?login_customer_id=123456")

  assert response.status_code == status.HTTP_200_OK
  assert response.json() == {"data": mock_data}
  mock_ga_service.list_accessible_subaccounts.assert_called_once_with()


def test_get_sub_accounts_error(client, mock_ga_service):
  """Test retrieval of sub-accounts handles errors."""
  mock_ga_service.login_customer_id = 123456
  mock_ga_service.list_accessible_subaccounts.side_effect = Exception(
      "API Error"
  )

  response = client.get("/api/reports/sub-accounts?login_customer_id=123456")

  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert response.json()["detail"] == "API Error"
  mock_ga_service.list_accessible_subaccounts.assert_called_once_with()


def test_get_campaigns_success(client, mock_ga_service):
  """Test successful retrieval of campaigns."""
  mock_data = [{"id": "123", "name": "Campaign 1"}]
  mock_ga_service.get_campaigns.return_value = mock_data

  response = client.get("/api/reports/campaigns?login_customer_id=customer-1")
  assert response.status_code == status.HTTP_200_OK
  assert response.json() == {"data": mock_data}
  mock_ga_service.get_campaigns.assert_called_once_with(customer_id=None)


def test_get_campaigns_with_filter_success(client, mock_ga_service):
  """Test successful retrieval of campaigns with customer_id filter."""
  mock_data = [{"id": "123", "name": "Campaign 1"}]
  mock_ga_service.get_campaigns.return_value = mock_data

  response = client.get(
      "/api/reports/campaigns?login_customer_id=customer-1&customer_id=sub-1"
  )
  assert response.status_code == status.HTTP_200_OK
  assert response.json() == {"data": mock_data}
  mock_ga_service.get_campaigns.assert_called_once_with(customer_id="sub-1")


def test_get_campaigns_error(client, mock_ga_service):
  """Test retrieval of campaigns fails gracefully."""
  mock_ga_service.get_campaigns.side_effect = Exception("API Error")

  response = client.get("/api/reports/campaigns?login_customer_id=customer-1")
  assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
  assert response.json()["detail"] == "API Error"
  mock_ga_service.get_campaigns.assert_called_once_with(customer_id=None)


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
