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

"""Unit tests for the queue_products_lib module."""

import dataclasses
import json
from unittest import mock

from google.cloud import bigquery
from google.cloud import tasks_v2
import pytest

from src.pipeline.product_embeddings.queue_products import queue_products_lib


class TestProductQueuer:
  """Unit tests for the ProductQueuer class."""

  @pytest.fixture
  def mock_bigquery_client(self):
    """Set up test environment mock BigQuery client."""
    return mock.MagicMock(spec=bigquery.Client)

  @pytest.fixture
  def mock_tasks_client(self):
    """Set up test environment mock Cloud Tasks client."""
    client = mock.MagicMock(spec=tasks_v2.CloudTasksClient)
    client.queue_path.return_value = 'test-queue-path'
    return client

  @mock.patch('google.cloud.bigquery.Client')
  @mock.patch('google.cloud.tasks_v2.CloudTasksClient')
  def test_initialization_with_client_creation(
      self,
      mock_tasks_client_class,
      mock_bigquery_client_class,
      mock_tasks_client,
      mock_bigquery_client,
  ):
    """Tests that the queuer initializes correctly by creating clients."""
    mock_bigquery_client_class.return_value = mock_bigquery_client
    mock_tasks_client_class.return_value = mock_tasks_client

    queue_products_lib.ProductQueuer(
        project_id='test-project',
        dataset_id='test-dataset',
        merchant_id='test-merchant',
        location='test-location',
        queue_id='test-queue',
    )
    mock_bigquery_client_class.assert_called_once_with('test-project')
    mock_tasks_client_class.assert_called_once_with()

  def test_initialization_with_passed_clients(
      self, mock_bigquery_client, mock_tasks_client
  ):
    """Tests that the queuer initializes correctly with passed clients."""
    queuer = queue_products_lib.ProductQueuer(
        project_id='test-project',
        dataset_id='test-dataset',
        merchant_id='test-merchant',
        location='test-location',
        queue_id='test-queue',
        bigquery_client=mock_bigquery_client,
        tasks_client=mock_tasks_client,
    )
    assert queuer.bigquery_client == mock_bigquery_client
    assert queuer.tasks_client == mock_tasks_client

  def test_is_queue_empty_true(self, mock_bigquery_client, mock_tasks_client):
    """Tests the is_queue_empty method when queue is empty."""
    queuer = queue_products_lib.ProductQueuer(
        project_id='test-project',
        dataset_id='test-dataset',
        merchant_id='test-merchant',
        location='test-location',
        queue_id='test-queue',
        bigquery_client=mock_bigquery_client,
        tasks_client=mock_tasks_client,
    )
    mock_tasks_client.list_tasks.return_value.tasks = []
    assert queuer.is_queue_empty()

    mock_tasks_client.list_tasks.assert_called_with(
        request=tasks_v2.ListTasksRequest(parent='test-queue-path')
    )

  def test_is_queue_empty_false(self, mock_bigquery_client, mock_tasks_client):
    """Tests the is_queue_empty method when queue is not empty."""
    queuer = queue_products_lib.ProductQueuer(
        project_id='test-project',
        dataset_id='test-dataset',
        merchant_id='test-merchant',
        location='test-location',
        queue_id='test-queue',
        bigquery_client=mock_bigquery_client,
        tasks_client=mock_tasks_client,
    )
    mock_tasks_client.list_tasks.return_value.tasks = [mock.MagicMock()]
    assert not queuer.is_queue_empty()
    mock_tasks_client.list_tasks.assert_called_with(
        request=tasks_v2.ListTasksRequest(parent='test-queue-path')
    )

  @mock.patch('builtins.open', new_callable=mock.mock_open)
  def test_get_new_products_from_view(
      self, mocked_file, mock_bigquery_client, mock_tasks_client
  ):
    """Tests the get_new_products_from_view method."""
    mock_sql_query = mock.MagicMock(spec=str)
    mock_sql_query.format.return_value = 'formatted query'
    mocked_file.return_value.read.return_value = mock_sql_query
    mock_rows = [{
        'offer_id': '1',
        'title': 'Product 1',
        'brand': 'Brand 1',
        'description': 'Description 1',
        'product_type': 'Type 1',
        'google_product_category': 'Category 1',
        'image_link': 'http://example.com/image.jpg',
        'additional_image_links': ['http://example.com/image2.jpg'],
    }]
    mock_bigquery_client.query.return_value.result.return_value = mock_rows
    queuer = queue_products_lib.ProductQueuer(
        project_id='test-project',
        dataset_id='test-dataset',
        merchant_id='test-merchant',
        location='test-location',
        queue_id='test-queue',
        bigquery_client=mock_bigquery_client,
        tasks_client=mock_tasks_client,
    )
    products = queuer.get_new_products_from_view(product_limit=5)

    expected_format_args = {
        'project_id': 'test-project',
        'dataset_id': 'test-dataset',
        'merchant_id': 'test-merchant',
        'product_limit': 5,
    }
    mocked_file().read.assert_called_once()
    mock_sql_query.format.assert_called_once_with(**expected_format_args)
    mock_bigquery_client.query.assert_called_once_with('formatted query')

    expected_product_dict = {
        'offer_id': '1',
        'title': 'Product 1',
        'brand': 'Brand 1',
        'description': 'Description 1',
        'product_type': 'Type 1',
        'google_product_category': 'Category 1',
        'age_group': None,
        'color': None,
        'gender': None,
        'material': None,
        'pattern': None,
        'image_link': 'http://example.com/image.jpg',
        'additional_image_links': ['http://example.com/image2.jpg'],
    }
    assert dataclasses.asdict(products[0]) == expected_product_dict

  def test_push_products(self, mock_bigquery_client, mock_tasks_client):
    """Tests the push_products method."""
    queuer = queue_products_lib.ProductQueuer(
        project_id='test-project',
        dataset_id='test-dataset',
        merchant_id='test-merchant',
        location='test-location',
        queue_id='test-queue',
        bigquery_client=mock_bigquery_client,
        tasks_client=mock_tasks_client,
    )

    products = [
        queue_products_lib.Product(
            offer_id='1',
            title='Product 1',
            brand='Brand 1',
            description='Description 1',
            product_type='Type 1',
            google_product_category='Category 1',
        )
    ]
    queuer.push_products(products, 'http://test-url')

    expected_payload = {'product': dataclasses.asdict(products[0])}
    expected_task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url='http://test-url',
            body=json.dumps(expected_payload).encode('utf-8'),
            headers={
                'Content-type': 'application/json',
            },
        )
    )
    expected_request = tasks_v2.CreateTaskRequest(
        parent='test-queue-path',
        task=expected_task,
    )
    mock_tasks_client.create_task.assert_called_once_with(expected_request)
