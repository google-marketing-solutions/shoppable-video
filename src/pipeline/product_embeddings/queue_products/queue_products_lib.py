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

"""Queue Products Module."""

import dataclasses
import json
import logging
import pathlib
from typing import Optional

from google.cloud import bigquery
from google.cloud import tasks_v2

try:
  from shared import common  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ...shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level

Product = common.Product


class Error(Exception):
  """Base error class for this module."""


class BigQueryReadError(Error):
  """Error reading from BigQuery."""


class CloudTasksPublishError(Error):
  """Error publishing to Cloud Tasks."""


class CloudTasksQueueNotEmptyError(Error):
  """Error when queue has unfinished tasks."""


class ProductQueuer:
  """Product queuer class."""

  def __init__(
      self,
      project_id: str,
      dataset_id: str,
      merchant_id: str,
      location: str,
      queue_id: str,
      bigquery_client: Optional[bigquery.Client] = None,
      tasks_client: Optional[tasks_v2.CloudTasksClient] = None,
  ):
    """Initialize instance of ProductQueuer.

    Args:
      project_id: The Google Cloud project ID.
      dataset_id: The BigQuery dataset ID.
      merchant_id: The Google Merchant ID.
      location: The Google Cloud location.
      queue_id: The Cloud Tasks queue ID.
      bigquery_client: An optional BigQuery client.
      tasks_client: An optional Cloud Tasks client.
    """
    self.project_id = project_id
    self.dataset_id = dataset_id
    self.merchant_id = merchant_id
    self.location = location
    self.queue_id = queue_id

    self.bigquery_client = bigquery_client or bigquery.Client(self.project_id)
    self.tasks_client = tasks_client or tasks_v2.CloudTasksClient()

    self.parent_queue = self.tasks_client.queue_path(
        self.project_id, self.location, self.queue_id
    )

  def is_queue_empty(self) -> bool:
    """Checks if the Google Cloud Tasks queue is empty.

    Returns:
        True if the queue is empty, False otherwise.
    """
    request = tasks_v2.ListTasksRequest(parent=self.parent_queue)
    response = self.tasks_client.list_tasks(request=request)
    # Check if the queue is empty
    return not bool(list(response.tasks))

  def get_new_products_from_view(
      self, product_limit: int = 10
  ) -> list[Product]:
    """Retrieves set of new unprocessed products.

    Args:
      product_limit (int): Maximum number of products to retrieve

    Returns:
      a list of Product dataclasses
    """
    query_path = pathlib.Path(__file__).parent / 'queries/get_new_products.sql'
    with open(query_path, 'r', encoding='utf-8') as f:
      query = f.read().format(
          project_id=self.project_id,
          dataset_id=self.dataset_id,
          merchant_id=self.merchant_id,
          product_limit=product_limit,
      )
    try:
      query_job = self.bigquery_client.query(query)
      rows = query_job.result()
    except Exception as e:  # pylint: disable=broad-exception-caught
      raise BigQueryReadError(e) from e
    products = [Product(**row) for row in rows]
    return products

  def push_products(
      self,
      products: list[Product],
      cloud_function_url: str,
  ):
    """Pushes products to Cloud Tasks.

    Args:
      products (list[Product]): A list of Product dataclasses.
      cloud_function_url (str): The URL of the Cloud Function to call.

    Raises:
      CloudTasksPublishError: if the Cloud Tasks publish fails
    """

    task_count = 0

    for product in products:
      try:
        # Construct the request body.
        payload = {'product': dataclasses.asdict(product)}
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=cloud_function_url,
                body=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-type': 'application/json',
                },
            )
        )
        # Use the client to build and send the task.
        self.tasks_client.create_task(
            tasks_v2.CreateTaskRequest(
                parent=self.parent_queue,
                task=task,
            )
        )
        task_count += 1
      except Exception as e:
        raise CloudTasksPublishError(e) from e

    logging.info('Submitted %d tasks to Cloud Tasks.', task_count)
