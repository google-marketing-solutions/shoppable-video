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

"""Queue Products Cloud Run Job."""

import logging

from google.cloud import logging as cloud_logging
import queue_products_lib

try:
  from shared import common  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ...shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level


logging_client = cloud_logging.Client()
logging_client.setup_logging()

# Global Initialization
PROJECT_ID = common.get_env_var('PROJECT_ID')
DATASET_ID = common.get_env_var('DATASET_ID')
MERCHANT_ID = common.get_env_var('MERCHANT_ID')
LOCATION = common.get_env_var('LOCATION')
QUEUE_ID = common.get_env_var('QUEUE_ID')
CLOUD_FUNCTION_URL = common.get_env_var('CLOUD_FUNCTION_URL')
PRODUCT_LIMIT = int(common.get_env_var('PRODUCT_LIMIT'))


def main():
  """Queries BigQuery for products and pushes them to a Cloud Task queue."""
  product_queuer = queue_products_lib.ProductQueuer(
      project_id=PROJECT_ID,
      dataset_id=DATASET_ID,
      merchant_id=MERCHANT_ID,
      location=LOCATION,
      queue_id=QUEUE_ID,
  )
  products = product_queuer.get_new_products_from_view(
      product_limit=PRODUCT_LIMIT
  )
  if products:
    # To prevent duplicate tasks, do not push unless queue is empty.
    if not product_queuer.is_queue_empty():
      raise queue_products_lib.CloudTasksQueueNotEmptyError(
          'Queue is not empty!'
      )
    logging.info('Found %d new products to push', len(products))
    product_queuer.push_products(
        products=products, cloud_function_url=CLOUD_FUNCTION_URL
    )
  else:
    logging.info('No new products found, exiting...')


if __name__ == '__main__':
  main()
