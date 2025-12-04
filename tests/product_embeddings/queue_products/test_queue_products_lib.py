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
import unittest
from unittest import mock

from google.cloud import bigquery
from google.cloud import tasks_v2
from src.pipeline.product_embeddings.queue_products import queue_products_lib
from src.pipeline.shared import common


class TestProductQueuer(unittest.TestCase):
  """Unit tests for the ProductQueuer class."""

  def setUp(self):
    """Set up test environment."""
    super().setUp()
    self.mock_bigquery_client = mock.MagicMock(spec=bigquery.Client)
    self.mock_tasks_client = mock.MagicMock(spec=tasks_v2.CloudTasksClient)

  @mock.patch('google.cloud.bigquery.Client')
  @mock.patch('google.cloud.tasks_v2.CloudTasksClient')
  def test_initialization(self, mock_tasks_client, mock_bigquery_client):
    """Tests that the queuer initializes correctly."""
    mock_bigquery_client.return_value = self.mock_bigquery_client
    mock_tasks_client.return_value = self.mock_tasks_client
    self.mock_tasks_client.queue_path.return_value = 'test-queue-path'

    with self.subTest(msg='Clients are instantiated'):
      queuer = queue_products_lib.ProductQueuer(
          project_id='test-project',
          dataset_id='test-dataset',
          merchant_id='test-merchant',
          location='test-location',
          queue_id='test-queue',
      )
      mock_bigquery_client.assert_called_once_with('test-project')
      mock_tasks_client.assert_called_once_with()

    mock_bigquery_client.reset_mock()
    mock_tasks_client.reset_mock()

    with self.subTest(msg='Clients are passed in'):
      queuer = queue_products_lib.ProductQueuer(
          project_id='test-project',
          dataset_id='test-dataset',
          merchant_id='test-merchant',
          location='test-location',
          queue_id='test-queue',
          bigquery_client=self.mock_bigquery_client,
          tasks_client=self.mock_tasks_client,
      )
      mock_bigquery_client.assert_not_called()
      mock_tasks_client.assert_not_called()
      self.assertEqual(queuer.bigquery_client, self.mock_bigquery_client)
      self.assertEqual(queuer.tasks_client, self.mock_tasks_client)

  def test_is_queue_empty(self):
    """Tests the is_queue_empty method."""
    self.mock_tasks_client.queue_path.return_value = 'test-queue-path'

    queuer = queue_products_lib.ProductQueuer(
        project_id='test-project',
        dataset_id='test-dataset',
        merchant_id='test-merchant',
        location='test-location',
        queue_id='test-queue',
        bigquery_client=self.mock_bigquery_client,
        tasks_client=self.mock_tasks_client,
    )

    with self.subTest(msg='Queue is empty'):
      self.mock_tasks_client.list_tasks.return_value.tasks = []
      self.assertTrue(queuer.is_queue_empty())
      self.mock_tasks_client.list_tasks.assert_called_with(
          request=tasks_v2.ListTasksRequest(parent='test-queue-path')
      )

    with self.subTest(msg='Queue is not empty'):
      self.mock_tasks_client.list_tasks.return_value.tasks = [mock.MagicMock()]
      self.assertFalse(queuer.is_queue_empty())
      self.mock_tasks_client.list_tasks.assert_called_with(
          request=tasks_v2.ListTasksRequest(parent='test-queue-path')
      )

  @mock.patch('builtins.open', new_callable=mock.mock_open)
  def test_get_new_products_from_view(self, mocked_file):
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
    }]
    self.mock_bigquery_client.query.return_value.result.return_value = mock_rows
    queuer = queue_products_lib.ProductQueuer(
        project_id='test-project',
        dataset_id='test-dataset',
        merchant_id='test-merchant',
        location='test-location',
        queue_id='test-queue',
        bigquery_client=self.mock_bigquery_client,
        tasks_client=self.mock_tasks_client,
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
    self.mock_bigquery_client.query.assert_called_once_with('formatted query')

    expected_product = common.Product(
        offer_id='1',
        title='Product 1',
        brand='Brand 1',
        description='Description 1',
        product_type='Type 1',
        google_product_category='Category 1',
    )
    self.assertEqual(products[0], expected_product)

  def test_push_products(self):
    """Tests the push_products method."""
    self.mock_tasks_client.queue_path.return_value = 'test-queue-path'

    queuer = queue_products_lib.ProductQueuer(
        project_id='test-project',
        dataset_id='test-dataset',
        merchant_id='test-merchant',
        location='test-location',
        queue_id='test-queue',
        bigquery_client=self.mock_bigquery_client,
        tasks_client=self.mock_tasks_client,
    )

    products = [
        common.Product(
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
    self.mock_tasks_client.create_task.assert_called_once_with(expected_request)


if __name__ == '__main__':
  unittest.main()
