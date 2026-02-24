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

"""Embedding Generation Module."""

import json
import logging
from typing import Any

from google.genai import types
import requests
import requests.adapters
from urllib3.util import retry


class EmbeddingError(Exception):
  """Base exception for embedding-related errors."""


class EmbeddingGenerationError(EmbeddingError):
  """Exception raised for errors during embedding generation."""


class TextEmbeddingGenerator:
  """Text Embedding Generator class."""

  _API_URL = 'https://generativelanguage.googleapis.com/v1beta/models'

  def __init__(
      self,
      embedding_model_name: str,
      embedding_dimensionality: int,
      api_key: str,
  ):
    """Initializes the TextEmbeddingGenerator."""

    self.embedding_model_name = embedding_model_name
    self.embedding_dimensionality = embedding_dimensionality
    self.api_key = api_key

    self.url = f'{self._API_URL}/{self.embedding_model_name}:embedContent'
    self.headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': self.api_key,
    }

    retry_strategy = retry.Retry(
        total=5,  # High retry count to survive rate limit windows
        backoff_factor=2,  # Wait 2s, 4s, 8s, 16s, 32s...
        status_forcelist=[
            429,  # Rate Limit Exceeded (CRITICAL for Gemini)
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
        ],
        allowed_methods=['POST'],
        backoff_jitter=1,
    )
    self.adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
    self.session = requests.Session()
    self.session.headers.update(self.headers)
    self.session.mount('https://', self.adapter)

  def generate_embedding(
      self, text: str, resource_id: Any
  ) -> types.ContentEmbedding:
    """Returns the embedding for the given text."""

    logging.info(
        'Generating embedding for resource %s',
        resource_id,
        extra={
            'json_fields': {
                'resource_id': resource_id,
                'text_to_embed': text,
            }
        },
    )
    data = {
        'content': {'parts': [{'text': text}]},
        'taskType': 'SEMANTIC_SIMILARITY',
        'outputDimensionality': self.embedding_dimensionality,
    }
    try:
      response = self.session.post(
          self.url, data=json.dumps(data), timeout=(3.05, 30)
      )
      response.raise_for_status()  # Raise an exception for error responses
      response_json = response.json()
      embedding = types.ContentEmbedding(
          values=response_json['embedding']['values']
      )
      return embedding
    except requests.exceptions.HTTPError as e:
      raise EmbeddingGenerationError(
          f'HTTP error generating embedding for resource {resource_id}: {e}. '
          f'Response: {e.response.text}'
      ) from e
    except requests.exceptions.RequestException as e:
      raise EmbeddingGenerationError(
          f'Request error generating embedding for resource {resource_id}: {e}'
      ) from e
