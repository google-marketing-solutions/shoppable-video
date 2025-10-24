# Copyright 2025 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generate Embedding Module."""

import datetime
import logging

from google import genai
from google.cloud import aiplatform
from google.cloud import bigquery
from google.genai import types

try:
  from shared import common  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ...shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level

Product = common.Product


class Error(Exception):
  """Generic Error class for module."""


class BigQueryReadError(Error):
  """Error reading from BigQuery."""


class BigQueryWriteError(Error):
  """Error writing to BigQuery."""


class TextEmbeddingGenerator:
  """Text Embedding Generator class."""

  def __init__(self, embedding_dimensionality: int):
    """Initializes the TextEmbeddingGenerator."""

    self.genai_client = genai.Client()
    self.model = 'gemini-embedding-001'
    self.embed_content_config = types.EmbedContentConfig(
        task_type='CLUSTERING', output_dimensionality=embedding_dimensionality
    )

  def get_embedding_for_product(
      self, product: Product
  ) -> types.ContentEmbedding:
    """Returns the embedding for the given product."""

    text_to_embed = []
    text_to_embed.append(f'Title: {product.title}')
    text_to_embed.append(f'Brand: {product.brand}')
    if product.google_product_category:
      text_to_embed.append(
          f'Product Category: {product.google_product_category}'
      )
    if product.product_type:
      text_to_embed.append(f'Product Type: {product.product_type}')
    if product.age_group:
      text_to_embed.append(f'Age Group: {product.age_group}')
    if product.color:
      text_to_embed.append(f'Color: {product.color}')
    if product.gender:
      text_to_embed.append(f'Gender: {product.gender}')
    if product.material:
      text_to_embed.append(f'Material: {product.material}')
    if product.pattern:
      text_to_embed.append(f'Pattern: {product.pattern}')
    text_to_embed.append(f'Description: {product.description}')

    logging.info(
        'Generating embedding for product %s',
        product.offer_id,
        extra={
            'json_fields': {
                'product': product.to_json(),
                'text_to_embed': '\n'.join(text_to_embed),
            }
        },
    )
    response = self.genai_client.models.embed_content(
        model=self.model,
        contents=text_to_embed,
        config=self.embed_content_config,
    )
    if not response.embeddings:
      raise ValueError('No embeddings returned from embedding model')
    return response.embeddings[0]


class BigQueryConnector:
  """BigQuery Connector class."""

  def __init__(self, project_id: str, embedding_table_name: str):
    """Initializes the BigQuery."""

    self.client = bigquery.Client(project=project_id)
    self.embedding_table_name = embedding_table_name

  def insert_embedding_for_product(
      self, product: Product, embedding: types.ContentEmbedding
  ):
    """Inserts an embedding for the provided product."""

    insertion_datetime = datetime.datetime.now(datetime.timezone.utc)
    insertion_timestamp = insertion_datetime.strftime('%Y-%m-%d %H:%M:%S')

    rows_to_insert = [{
        'id': product.offer_id,
        'insertion_timestamp': insertion_timestamp,
        'embedding': embedding.values,
        'embedding_metadata': {
            'title': product.title,
            'brand': product.brand,
        },
    }]
    try:
      logging.info(
          'Inserting embedding for product ID %s',
          product.offer_id,
          extra={'json_fields': {'product': product.to_json()}},
      )
      errors = self.client.insert_rows_json(
          self.embedding_table_name, rows_to_insert
      )
      if errors:
        raise BigQueryWriteError(errors)
    except Exception as e:
      raise BigQueryWriteError(e) from e


class VectorSearchConnector:
  """Vector Search Connector class."""

  def __init__(
      self,
      project_id: str,
      location: str,
      index_name: str,
  ):
    """Initializes the VectorSearchConnector.

    Args:
        project_id: The Google Cloud project ID.
        location: The Google Cloud location.
        index_name: The Vector Search index resource name.
    """

    self.project_id = project_id
    self.location = location

    aiplatform.init(project=self.project_id, location=self.location)
    self.index_name = index_name
    self.index = aiplatform.MatchingEngineIndex(index_name=self.index_name)

  def upsert_datapoint(
      self, product: Product, embedding: types.ContentEmbedding
  ):
    """Upserts a datapoint to Vector Search for the provided product.

    Args:
        product: The product.
        embedding: The embedding for the product.
    """

    datapoint = {
        'datapoint_id': product.offer_id,
        'embedding': embedding.values,
    }
    logging.info('Upserting datapoint for product ID %s', product.offer_id)
    self.index.upsert_datapoints(datapoints=[datapoint])
