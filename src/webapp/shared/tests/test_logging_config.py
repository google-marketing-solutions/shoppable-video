# Copyright 2026 Google LLC
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

"""Unit tests for the centralized logging configuration module."""

import logging
import os
from unittest import mock

import logging_config


@mock.patch.dict(os.environ, {}, clear=True)
@mock.patch("logging.basicConfig")
@mock.patch("dotenv.load_dotenv")
def test_configure_logging_local(mock_dotenv, mock_config):
  """Verifies fallback stream handler is configured for local environments."""
  # Ensure environment variables are NOT indicating cloud
  logging_config.configure_logging()

  mock_dotenv.assert_called_once()

  # Check basicConfig calls
  mock_config.assert_called_once()
  kwargs = mock_config.call_args[1]

  assert kwargs["level"] == "INFO"
  assert kwargs["force"]
  assert len(kwargs["handlers"]) == 1
  assert isinstance(kwargs["handlers"][0], logging.StreamHandler)


@mock.patch.dict(os.environ, {"K_SERVICE": "test-service"}, clear=True)
@mock.patch("logging.basicConfig")
@mock.patch("dotenv.load_dotenv")
@mock.patch("logging_config.StructuredLogHandler")
def test_configure_logging_cloud(mock_handler_cls, mock_dotenv, mock_config):
  """Verifies StructuredLogHandler is deployed in Cloud environment."""
  mock_handler_instance = mock.MagicMock()
  mock_handler_cls.return_value = mock_handler_instance

  logging_config.configure_logging()

  mock_dotenv.assert_called_once()
  mock_config.assert_called_once()

  kwargs = mock_config.call_args[1]
  assert kwargs["level"] == "INFO"
  assert kwargs["handlers"] == [mock_handler_instance]


@mock.patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=True)
@mock.patch("logging.basicConfig")
@mock.patch("dotenv.load_dotenv")
def test_configure_logging_custom_level(mock_dotenv, mock_config):
  """Verifies custom log levels are respected."""
  del mock_dotenv  # Satisfy pylint
  logging_config.configure_logging()

  kwargs = mock_config.call_args[1]
  assert kwargs["level"] == "DEBUG"
