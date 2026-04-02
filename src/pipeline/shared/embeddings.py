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

import io
import logging
from typing import Any

from google import genai
from google.genai import types

import numpy as np
import requests


USER_AGENT = (  # Default requests user agent can cause 403 errors.
    'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible;'
    ' GoogleOther) Chrome/W.X.Y.Z Safari/537.36'
)
REQUEST_TIMEOUT = 30


class Error(Exception):
  """Generic Error class for module."""


class GenerativeAIError(Error):
  """Error interacting with Gemini API."""


class ImagePullError(Error):
  """Error downloading an image."""


class QuotaExceededError(Error):
  """Error when total utilization exceeds the threshold."""


class EmbeddingError(Error):
  """Base exception for embedding-related errors."""


class EmbeddingGenerationError(EmbeddingError):
  """Exception raised for errors during embedding generation."""


class MultimodalEmbeddingGenerator:
  """Multimodal Embedding Generator class."""

  def __init__(
      self,
      embedding_model_name: str,
      embedding_dimensionality: int,
      genai_client: genai.Client | None = None,
      user_agent: str = USER_AGENT,
      timeout: int = REQUEST_TIMEOUT,
  ):
    """Initializes the MultimodalEmbeddingGenerator."""

    self.genai_client = genai_client or genai.Client()
    self.embedding_model_name = embedding_model_name
    self.embedding_dimensionality = embedding_dimensionality

    self.http_session = requests.Session()
    self.http_headers = {
        'User-Agent': user_agent,
    }
    self.timeout = timeout

  def upload_image_from_url(self, url: str) -> types.File:
    """Downloads an image from a URL and then & uploads it to Gemini.

    Args:
      url: the image link to process

    Returns:
      a populated File reference object

    Raises:
      ImagePullError: if the image cannot be downloaded from the link
      GenerativeAIError: if the image cannot be uploaded to Gemini
    """
    # Download image from link
    try:
      response = self.http_session.get(
          url, headers=self.http_headers, timeout=self.timeout
      )
      response.raise_for_status()
      response_content = response.content
      mime_type = response.headers.get('content-type', 'image/jpeg')
    except Exception as e:
      raise ImagePullError(e) from e

    # Upload image to Gemini for multimodal query.
    image_file = io.BytesIO(response_content)

    try:
      genai_file_reference = self.genai_client.files.upload(
          file=image_file,
          config=types.UploadFileConfig(
              mime_type=mime_type,
          ),
      )
      return genai_file_reference

    except Exception as e:
      raise GenerativeAIError(e) from e

  def normalize_embedding(
      self, embedding: types.ContentEmbedding
  ) -> list[float]:
    """Normalize embeddings to produce accurate semantic similarity.

    Args:
      embedding: a embedding to normalize

    Returns:
      a normalized embedding as a list of floats

    This is following the guidance from
    https://ai.google.dev/gemini-api/docs/embeddings#quality-for-smaller-dimensions
    """

    embedding_values_np = np.array(embedding.values)
    normed_embedding = embedding_values_np / np.linalg.norm(embedding_values_np)
    return normed_embedding.tolist()

  def generate_embedding(
      self, text: str, resource_id: Any, files: list[types.File] | None = None
  ) -> types.ContentEmbedding:
    """Generates an embedding for the given text & files (images).

    Args:
      text: the text to embed
      resource_id: a reference to what is being embedded for debugging
      files: a set of File objects to include.


    Returns:
      a populated ContentEmbedding reference object

    Raises:
      GenerativeAIError: if the embedding cannot be generated
    """

    parts: list[types.Part] = []
    if files:
      parts.extend([
          types.Part(
              file_data=types.FileData(
                  file_uri=file.uri, mime_type=file.mime_type
              )
          )
          for file in files
      ])
    parts.append(types.Part(text=text))

    logging.info(
        'Generating embedding for resource %s',
        resource_id,
        extra={
            'json_fields': {
                'resource_id': resource_id,
                'text_to_embed': text,
                'num_files': len(files) if files else 0,
            }
        },
    )

    result = self.genai_client.models.embed_content(
        model=self.embedding_model_name,
        contents=types.Content(parts=parts),
        config=types.EmbedContentConfig(
            output_dimensionality=self.embedding_dimensionality,
        ),
    )
    if result.embeddings is None:
      raise GenerativeAIError('No embeddings returned')

    embedding = result.embeddings[0]
    if self.embedding_dimensionality != 3072:
      embedding.values = self.normalize_embedding(embedding)

    return embedding
