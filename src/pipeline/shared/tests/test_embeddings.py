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

from unittest import mock

from google import genai
from google.genai import types
import pytest
import requests

from src.pipeline.shared import embeddings


class TestMultimodalEmbeddingGenerator:
  """Unit tests for the MultimodalEmbeddingGenerator class."""

  @pytest.fixture
  def mock_genai_client(self):
    """Set up test environment mock GenAI client."""
    return mock.MagicMock(spec=genai.Client)

  def test_initialization(self, mock_genai_client):
    """Tests that the generator initializes correctly."""
    generator = embeddings.MultimodalEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        genai_client=mock_genai_client,
    )

    assert generator.embedding_model_name == 'test-model'
    assert generator.embedding_dimensionality == 128
    assert generator.genai_client == mock_genai_client
    assert generator.http_headers['User-Agent'] == embeddings.USER_AGENT

  def test_upload_image_from_url_success(self, mock_genai_client):
    """Tests successful image upload from URL."""
    generator = embeddings.MultimodalEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        genai_client=mock_genai_client,
    )

    mock_response = mock.MagicMock(spec=requests.Response)
    mock_response.content = b'image_data'
    mock_response.headers = {'content-type': 'image/png'}
    mock_response.raise_for_status.return_value = None

    with mock.patch.object(
        generator.http_session, 'get', return_value=mock_response
    ) as mock_get:
      mock_file_reference = mock.MagicMock(spec=types.File)
      mock_genai_client.files.upload.return_value = mock_file_reference

      result = generator.upload_image_from_url('http://example.com/image.png')

      assert result == mock_file_reference
      mock_get.assert_called_once_with(
          'http://example.com/image.png',
          headers=generator.http_headers,
          timeout=generator.timeout,
      )
      mock_genai_client.files.upload.assert_called_once()

  def test_upload_image_from_url_pull_error(self, mock_genai_client):
    """Tests image upload from URL with a pull error."""
    generator = embeddings.MultimodalEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        genai_client=mock_genai_client,
    )

    with mock.patch.object(
        generator.http_session, 'get', side_effect=requests.RequestException
    ):
      with pytest.raises(embeddings.ImagePullError):
        generator.upload_image_from_url('http://example.com/image.png')

  def test_upload_image_from_url_genai_error(self, mock_genai_client):
    """Tests image upload from URL with a GenAI error."""
    generator = embeddings.MultimodalEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        genai_client=mock_genai_client,
    )

    mock_response = mock.MagicMock(spec=requests.Response)
    mock_response.content = b'image_data'
    mock_response.headers = {'content-type': 'image/png'}

    with mock.patch.object(
        generator.http_session, 'get', return_value=mock_response
    ):
      mock_genai_client.files.upload.side_effect = Exception('GenAI Error')
      with pytest.raises(embeddings.GenerativeAIError):
        generator.upload_image_from_url('http://example.com/image.png')

  def test_normalize_embedding(self, mock_genai_client):
    """Tests embedding normalization."""
    generator = embeddings.MultimodalEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        genai_client=mock_genai_client,
    )

    mock_embedding = mock.MagicMock(spec=types.ContentEmbedding)
    mock_embedding.values = [3.0, 4.0]  # Magnitude is 5.0

    normalized = generator.normalize_embedding(mock_embedding)

    assert isinstance(normalized, list)
    assert normalized == [0.6, 0.8]

  def test_generate_embedding_success(self, mock_genai_client):
    """Tests successful multimodal embedding generation."""
    generator = embeddings.MultimodalEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        genai_client=mock_genai_client,
    )

    mock_embedding = mock.MagicMock(spec=types.ContentEmbedding)
    mock_embedding.values = [1.0, 2.0, 3.0]
    mock_result = mock.MagicMock()
    mock_result.embeddings = [mock_embedding]
    mock_genai_client.models.embed_content.return_value = mock_result

    embedding = generator.generate_embedding('test text', 'test-resource-id')

    assert embedding == mock_embedding
    mock_genai_client.models.embed_content.assert_called_once()
    # Check parts
    call_args = mock_genai_client.models.embed_content.call_args
    assert call_args.kwargs['model'] == 'test-model'
    assert len(call_args.kwargs['contents'].parts) == 1
    assert call_args.kwargs['contents'].parts[0].text == 'test text'

  def test_generate_embedding_with_files_success(self, mock_genai_client):
    """Tests successful multimodal embedding generation with files."""
    generator = embeddings.MultimodalEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        genai_client=mock_genai_client,
    )

    mock_embedding = mock.MagicMock(spec=types.ContentEmbedding)
    mock_embedding.values = [1.0, 2.0, 3.0]
    mock_result = mock.MagicMock()
    mock_result.embeddings = [mock_embedding]
    mock_genai_client.models.embed_content.return_value = mock_result

    mock_file = mock.MagicMock(spec=types.File)
    mock_file.uri = 'gs://test-bucket/image.png'
    mock_file.mime_type = 'image/png'

    embedding = generator.generate_embedding(
        'test text', 'test-resource-id', files=[mock_file]
    )

    assert embedding == mock_embedding
    mock_genai_client.models.embed_content.assert_called_once()
    call_args = mock_genai_client.models.embed_content.call_args
    assert len(call_args.kwargs['contents'].parts) == 2
    assert (
        call_args.kwargs['contents'].parts[0].file_data.file_uri
        == mock_file.uri
    )
    assert call_args.kwargs['contents'].parts[1].text == 'test text'

  def test_generate_embedding_no_embeddings_returned(self, mock_genai_client):
    """Tests embedding generation when no embeddings are returned."""
    generator = embeddings.MultimodalEmbeddingGenerator(
        embedding_model_name='test-model',
        embedding_dimensionality=128,
        genai_client=mock_genai_client,
    )

    mock_result = mock.MagicMock()
    mock_result.embeddings = None
    mock_genai_client.models.embed_content.return_value = mock_result

    with pytest.raises(embeddings.GenerativeAIError):
      generator.generate_embedding('test text', 'test-resource-id')
