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

"""Unit tests for generate_embedding_lib."""

import datetime
from unittest import mock

from google.cloud import bigquery
from google.genai import types
import pytest

from src.pipeline.product_embeddings.generate_embedding import generate_embedding_lib
from src.pipeline.shared import common


class TestGenerateEmbeddingLib:
  """Unit tests for the generate_embedding_lib library."""

  @pytest.fixture
  def mock_bigquery_client(self):
    """Set up test environment mock BigQuery client."""
    return mock.MagicMock(spec=bigquery.Client)

  @mock.patch('google.cloud.bigquery.Client')
  def test_client_instantiation(
      self, mock_bigquery_client_class, mock_bigquery_client
  ):
    """Tests that the BigQuery client is instantiated and attributes are set."""
    mock_bigquery_client_class.return_value = mock_bigquery_client

    connector = generate_embedding_lib.BigQueryConnector(
        embedding_table_name='test_table'
    )

    mock_bigquery_client_class.assert_called_once_with()
    assert connector.client == mock_bigquery_client
    assert connector.embedding_table_name == 'test_table'

  @mock.patch('google.cloud.bigquery.Client')
  def test_insert_embedding_for_product(
      self, mock_bigquery_client_class, mock_bigquery_client
  ):
    """Tests that insert_embedding_for_product calls BQ client correctly."""
    mock_bigquery_client_class.return_value = mock_bigquery_client
    connector = generate_embedding_lib.BigQueryConnector(
        embedding_table_name='test_table'
    )
    product = common.Product(
        offer_id='123',
        title='Test Product',
        brand='Test Brand',
        description='Test Description',
        product_type='Test Product Type',
        google_product_category='Test Google Product Category',
    )
    embedding = types.ContentEmbedding(values=[1.0, 2.0, 3.0])
    mock_bigquery_client.insert_rows_json.return_value = []

    with mock.patch(
        'src.pipeline.product_embeddings.generate_embedding'
        '.generate_embedding_lib.datetime'
    ) as mock_dt:
      mock_insertion_datetime = datetime.datetime(
          2025, 11, 19, 12, 0, 0, tzinfo=datetime.timezone.utc
      )
      mock_dt.datetime.now.return_value = mock_insertion_datetime
      mock_dt.timezone = datetime.timezone
      connector.insert_embedding_for_product(
          product=product, embedding=embedding, embedding_model_id='test-model'
      )

      expected_rows_to_insert = [{
          'id': '123',
          'insertion_timestamp': '2025-11-19 12:00:00',
          'embedding': [1.0, 2.0, 3.0],
          'embedding_model_id': 'test-model',
      }]
      mock_bigquery_client.insert_rows_json.assert_called_once_with(
          'test_table', expected_rows_to_insert
      )

  @mock.patch('google.cloud.bigquery.Client')
  def test_insert_embedding_for_product_with_error(
      self, mock_bigquery_client_class, mock_bigquery_client
  ):
    """Tests that insert_embedding_for_product raises error on BQ error."""
    mock_bigquery_client_class.return_value = mock_bigquery_client
    connector = generate_embedding_lib.BigQueryConnector(
        embedding_table_name='test_table'
    )
    product = common.Product(
        offer_id='123',
        title='Test Product',
        brand='Test Brand',
        description='Test Description',
        product_type='Test Product Type',
        google_product_category='Test Google Product Category',
    )
    embedding = types.ContentEmbedding(values=[1.0, 2.0, 3.0])
    mock_bigquery_client.insert_rows_json.return_value = [
        {'errors': 'test_error'}
    ]

    with pytest.raises(generate_embedding_lib.BigQueryWriteError):
      connector.insert_embedding_for_product(
          product=product, embedding=embedding, embedding_model_id='test-model'
      )
