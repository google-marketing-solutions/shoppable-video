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

"""Library for generating product embeddings.

The main component of this library is the BigQueryConnector, a class to handle
interactions with BigQuery, specifically inserting the product embedding result.
"""
import datetime

from google.cloud import bigquery
from google.genai import types

try:
  from shared import common  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ...shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level


class Error(Exception):
  """Generic Error class for module."""


class BigQueryReadError(Error):
  """Error reading from BigQuery."""


class BigQueryWriteError(Error):
  """Error writing to BigQuery."""


class BigQueryConnector:
  """BigQuery Connector class."""

  def __init__(
      self,
      embedding_table_name: str,
      client: bigquery.Client | None = None,
  ):
    """Initializes the BigQuery Connector.

    Args:
      embedding_table_name: The name of the BQ table to use for embeddings.
      client: An optional BigQuery client to use.
    """

    self.embedding_table_name = embedding_table_name
    self.client = client or bigquery.Client()

  def insert_embedding_for_product(
      self, product: common.Product, embedding: types.ContentEmbedding
  ):
    """Inserts an embedding for the provided product.

    Args:
      product: The product to insert the embedding for.
      embedding: The embedding to insert.

    Raises:
      BigQueryWriteError: If there is an error writing to BigQuery.
    """

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
      errors = self.client.insert_rows_json(
          self.embedding_table_name, rows_to_insert
      )
      if errors:
        raise BigQueryWriteError(errors)
    except Exception as e:
      raise BigQueryWriteError(e) from e
