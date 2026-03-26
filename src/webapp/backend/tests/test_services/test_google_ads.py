"""Unit tests for google_ads service."""

from unittest import mock

from app.services import google_ads
import pytest


@pytest.fixture(name="mock_ads_client")
def fixture_mock_ads_client():
  return mock.Mock()


@pytest.fixture(name="service")
def fixture_service(mock_ads_client):
  return google_ads.GoogleAdsService(
      client=mock_ads_client, login_customer_id=123456
  )


def test_init_success(mock_ads_client):
  """Test successful initialization of GoogleAdsService."""
  svc = google_ads.GoogleAdsService(
      client=mock_ads_client, login_customer_id=123456
  )
  assert svc.client == mock_ads_client
  assert svc.login_customer_id == 123456
  assert svc.ga_service == mock_ads_client.get_service("GoogleAdsService")


def test_list_accessible_customers_success(service, mock_ads_client):
  """Test retrieving globally accessible customer resource names."""
  mock_customer_service = mock_ads_client.get_service.return_value
  mock_response = mock.Mock()
  mock_response.resource_names = ["customers/123", "customers/456"]
  mock_customer_service.list_accessible_customers.return_value = mock_response

  result = service.list_accessible_customers()

  assert result == ["customers/123", "customers/456"]
  mock_ads_client.get_service.assert_any_call("CustomerService")


def test_get_campaigns_success(service, mock_ads_client):
  """Test retrieving campaigns."""
  mock_service = mock_ads_client.get_service.return_value
  mock_row = mock.Mock()
  mock_row.customer.id = 123456
  mock_row.campaign.id = 111
  mock_row.campaign.name = "Test Campaign"
  mock_row.campaign.status.name = "ENABLED"
  mock_row.campaign.advertising_channel_type.name = "SEARCH"

  mock_batch = mock.Mock()
  mock_batch.results = [mock_row]
  mock_service.search_stream.return_value = [mock_batch]

  result = service.get_campaigns()

  assert len(result) == 1
  expected = {
      "customer_id": 123456,
      "id": 111,
      "name": "Test Campaign",
      "status": "ENABLED",
      "type": "SEARCH",
  }
  assert result[0] == expected

  # Verify GAQL and customer ID
  mock_service.search_stream.assert_called_once()
  _, kwargs = mock_service.search_stream.call_args
  assert kwargs["customer_id"] == "123456"
  assert "SELECT customer.id, campaign.id" in kwargs["query"]


def test_execute_query_exception(service, mock_ads_client):
  """Test _execute_query handles Exception by raising it."""
  mock_service = mock_ads_client.get_service.return_value
  mock_service.search_stream.side_effect = Exception("API Error")

  with pytest.raises(Exception, match="API Error"):
    service.get_campaigns()

  mock_service.search_stream.assert_called_once()


def test_list_accessible_subaccounts_success(service, mock_ads_client):
  """Test retrieving accessible sub-accounts."""
  mock_service = mock_ads_client.get_service.return_value
  mock_row = mock.Mock()
  mock_row.customer_client.id = 777
  mock_row.customer_client.descriptive_name = "Sub Account"
  mock_row.customer_client.manager = False
  mock_row.customer_client.level = 1

  mock_batch = mock.Mock()
  mock_batch.results = [mock_row]
  mock_service.search_stream.return_value = [mock_batch]

  result = service.list_accessible_subaccounts()

  assert len(result) == 1
  expected = {
      "customer_id": 777,
      "descriptive_name": "Sub Account",
      "is_manager": False,
      "level": 1,
  }
  assert result[0] == expected

  # Verify GAQL and customer ID
  mock_service.search_stream.assert_called_once()
  _, kwargs = mock_service.search_stream.call_args
  assert kwargs["customer_id"] == "123456"
  assert "WHERE customer_client.level > 0" in kwargs["query"]


def test_get_customer_details_success(service, mock_ads_client):
  """Test retrieving customer details."""
  mock_service = mock_ads_client.get_service.return_value

  # Mock for the details query
  mock_details_row = mock.Mock()
  mock_details_row.customer.id = 999
  mock_details_row.customer.descriptive_name = "Test Account"
  mock_details_row.customer.manager = True
  mock_details_batch = mock.Mock()
  mock_details_batch.results = [mock_details_row]

  mock_service.search_stream.return_value = [mock_details_batch]

  result = service.get_customer_details(999)

  expected = {
      "customer_id": 999,
      "descriptive_name": "Test Account",
      "is_manager": True,
  }
  assert result == expected

  mock_service.search_stream.assert_called_once()
  _, kwargs1 = mock_service.search_stream.call_args
  assert kwargs1["customer_id"] == "999"


def test_get_customer_details_not_found(service, mock_ads_client):
  """Test retrieving customer details handles empty results/errors."""
  mock_service = mock_ads_client.get_service.return_value
  mock_service.search_stream.side_effect = Exception("API Error")

  result = service.get_customer_details(999)

  assert not result


def test_get_campaigns_with_custom_customer_id(service, mock_ads_client):
  """Test retrieving campaigns with a specific target_customer_id."""
  mock_service = mock_ads_client.get_service.return_value
  mock_row = mock.Mock()
  mock_row.customer.id = 999888777
  mock_row.campaign.id = 222
  mock_row.campaign.name = "Custom Account Campaign"
  mock_row.campaign.status.name = "ENABLED"
  mock_row.campaign.advertising_channel_type.name = "SEARCH"

  mock_batch = mock.Mock()
  mock_batch.results = [mock_row]
  mock_service.search_stream.return_value = [mock_batch]

  # Call with an explicit target customer ID
  result = service.get_campaigns(customer_id=999888777)

  assert len(result) == 1
  assert result[0]["id"] == 222
  assert result[0]["customer_id"] == 999888777

  # Verify the call used the custom ID
  mock_service.search_stream.assert_called_once()
  _, kwargs = mock_service.search_stream.call_args
  assert kwargs["customer_id"] == "999888777"
