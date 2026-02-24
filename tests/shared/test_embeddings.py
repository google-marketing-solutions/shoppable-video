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

"""Unit tests for the embeddings module."""

import json
import unittest
from unittest import mock

from google.genai import types
import requests
from requests.adapters import HTTPAdapter
from src.pipeline.shared import embeddings


class TestTextEmbeddingGenerator(unittest.TestCase):
  """Unit tests for the TextEmbeddingGenerator class."""

  def setUp(self):
    """Set up test environment."""
    super().setUp()
    self.mock_session = mock.MagicMock(spec=requests.Session)
    self.mock_session.headers = {}

  @mock.patch('requests.Session')
  @mock.patch('requests.adapters.HTTPAdapter')
  @mock.patch('urllib3.util.retry.Retry')
  def test_initialization(
      self, mock_retry_class, mock_http_adapter, mock_session
  ):
    """Tests that the generator initializes correctly."""
    mock_session.return_value = self.mock_session
    mock_adapter_instance = mock.MagicMock(spec=HTTPAdapter)
    mock_http_adapter.return_value = mock_adapter_instance

    generator = embeddings.TextEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        api_key='test-api-key',
    )

    self.assertEqual(generator.embedding_model_name, 'test-model')
    self.assertEqual(generator.embedding_dimensionality, 128)
    self.assertEqual(generator.api_key, 'test-api-key')
    # pylint: disable=protected-access
    expected_url = (
        f'{generator._API_URL}/{generator.embedding_model_name}:embedContent'
    )
    # pylint: enable=protected-access
    self.assertEqual(generator.url, expected_url)
    self.assertDictEqual(
        self.mock_session.headers,
        {
            'Content-Type': 'application/json',
            'x-goog-api-key': 'test-api-key',
        },
    )
    mock_retry_class.assert_called_once_with(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['POST'],
        backoff_jitter=1,
    )
    mock_http_adapter.assert_called_once_with(
        max_retries=mock_retry_class.return_value
    )
    self.mock_session.mount.assert_called_once_with(
        'https://', mock_adapter_instance
    )

  @mock.patch('requests.Session')
  def test_generate_embedding_success(self, mock_session):
    """Tests successful embedding generation."""
    mock_session.return_value = self.mock_session
    mock_response = mock.MagicMock()
    mock_response.json.return_value = {'embedding': {'values': [1.0, 2.0, 3.0]}}
    self.mock_session.post.return_value = mock_response

    generator = embeddings.TextEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        api_key='test-api-key',
    )
    embedding = generator.generate_embedding('test text', 'test-resource-id')

    self.assertIsInstance(embedding, types.ContentEmbedding)
    self.assertEqual(embedding.values, [1.0, 2.0, 3.0])
    expected_data = {
        'content': {'parts': [{'text': 'test text'}]},
        'taskType': 'SEMANTIC_SIMILARITY',
        'outputDimensionality': 128,
    }
    # pylint: disable=protected-access
    expected_url = (
        f'{generator._API_URL}/{generator.embedding_model_name}:embedContent'
    )
    # pylint: enable=protected-access
    self.mock_session.post.assert_called_once_with(
        expected_url,
        data=json.dumps(
            expected_data
        ),  # Asserting the data directly as a JSON string
        timeout=(3.05, 30),
    )
    # To assert the data, we need to capture the call and load the JSON
    _, call_kwargs = self.mock_session.post.call_args
    self.assertEqual(json.loads(call_kwargs['data']), expected_data)

  @mock.patch('requests.Session')
  def test_generate_embedding_http_error(self, mock_session):
    """Tests embedding generation with an HTTP error."""
    mock_session.return_value = self.mock_session
    mock_response = mock.MagicMock()
    mock_response.text = 'Internal Server Error'
    http_error = requests.exceptions.HTTPError(response=mock_response)
    self.mock_session.post.side_effect = http_error

    generator = embeddings.TextEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        api_key='test-api-key',
    )
    with self.assertRaises(embeddings.EmbeddingGenerationError):
      generator.generate_embedding('test text', 'test-resource-id')

  @mock.patch('requests.Session')
  def test_generate_embedding_request_exception(self, mock_session):
    """Tests embedding generation with a request exception."""
    mock_session.return_value = self.mock_session
    self.mock_session.post.side_effect = requests.exceptions.RequestException

    generator = embeddings.TextEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        api_key='test-api-key',
    )
    with self.assertRaises(embeddings.EmbeddingGenerationError):
      generator.generate_embedding('test text', 'test-resource-id')


if __name__ == '__main__':
  unittest.main()
