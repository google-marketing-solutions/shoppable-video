# Copyright 2025 Google LLC
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

"""Unit tests for FastAPI dependencies."""

from unittest import mock

from app.api import dependencies
from app.core.config import settings
import pytest


@pytest.fixture(name="mock_session_data")
def fixture_mock_session_data():
  return {"rt": "fake_refresh_token"}


def test_initialize_ads_client_with_login_customer_id(mock_session_data):
  """Test client init with login_customer_id."""
  with mock.patch(
      "google.ads.googleads.client.GoogleAdsClient.load_from_dict"
  ) as mock_load:
    # pylint: disable=protected-access
    dependencies._initialize_ads_client(mock_session_data, 1234567890)

    # Verify load_from_dict was called with login_customer_id
    args, _ = mock_load.call_args
    config = args[0]
    assert config["login_customer_id"] == "1234567890"


def test_initialize_ads_client_without_login_customer_id(mock_session_data):
  """Test client init WITHOUT login_customer_id."""
  with mock.patch(
      "google.ads.googleads.client.GoogleAdsClient.load_from_dict"
  ) as mock_load:
    # pylint: disable=protected-access
    dependencies._initialize_ads_client(mock_session_data)

    # Verify load_from_dict was called WITHOUT login_customer_id
    args, _ = mock_load.call_args
    config = args[0]
    assert "login_customer_id" not in config


def test_get_google_ads_service_explicit_customer_id(mock_session_data):
  """Test get_google_ads_service uses provided login_customer_id."""
  mock_client = mock.Mock()
  with mock.patch(
      "google.ads.googleads.client.GoogleAdsClient.load_from_dict",
      return_value=mock_client,
  ) as mock_load:
    service = dependencies.get_google_ads_service(
        mock_session_data, login_customer_id=9998887777
    )

    assert service.login_customer_id == "9998887777"
    assert service.client == mock_client
    args, _ = mock_load.call_args
    assert args[0]["login_customer_id"] == "9998887777"


def test_get_google_ads_service_default_platform_mcc(mock_session_data):
  """Test get_google_ads_service defaults to GOOGLE_ADS_CUSTOMER_ID."""
  mock_client = mock.Mock()
  with mock.patch(
      "google.ads.googleads.client.GoogleAdsClient.load_from_dict",
      return_value=mock_client,
  ) as mock_load:
    with mock.patch.object(settings, "GOOGLE_ADS_CUSTOMER_ID", "1112223333"):
      service = dependencies.get_google_ads_service(mock_session_data)

      assert service.login_customer_id == "1112223333"
      assert service.client == mock_client
      args, _ = mock_load.call_args
      assert args[0]["login_customer_id"] == "1112223333"
