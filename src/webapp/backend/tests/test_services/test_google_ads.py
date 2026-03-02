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
      client=mock_ads_client, customer_id="123456"
  )


def test_init_success(mock_ads_client):
  """Test successful initialization of GoogleAdsService."""
  svc = google_ads.GoogleAdsService(
      client=mock_ads_client, customer_id="123456"
  )
  assert svc.client == mock_ads_client
  assert svc.customer_id == "123456"
  assert svc.ga_service == mock_ads_client.get_service("GoogleAdsService")


def test_get_campaigns_success(service, mock_ads_client):
  """Test retrieving campaigns."""
  mock_service = mock_ads_client.get_service.return_value
  mock_row = mock.Mock()
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
      "id": "111",
      "name": "Test Campaign",
      "status": "ENABLED",
      "type": "SEARCH",
  }
  assert result[0] == expected

  # Verify GAQL and customer ID
  mock_service.search_stream.assert_called_once()
  _, kwargs = mock_service.search_stream.call_args
  assert kwargs["customer_id"] == "123456"
  assert "SELECT campaign.id, campaign.name, campaign.status" in kwargs["query"]


def test_execute_query_exception(service, mock_ads_client):
  """Test _execute_query handles Exception by raising it."""
  mock_service = mock_ads_client.get_service.return_value
  mock_service.search_stream.side_effect = Exception("API Error")

  with pytest.raises(Exception, match="API Error"):
    service.get_campaigns()

  mock_service.search_stream.assert_called_once()
