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

"""Generate Embedding HTTP Cloud Function."""

import functions_framework
import generate_embedding_lib
from google.cloud import logging as cloud_logging

try:
  from shared import common  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ..shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level


# Cloud Logging
logging_client = cloud_logging.Client()
logging_client.setup_logging()

# Environment Global Variables
PROJECT_ID = common.get_env_var('PROJECT_ID')
LOCATION = common.get_env_var('LOCATION')
DATASET_ID = common.get_env_var('DATASET_ID')
TABLE_NAME = common.get_env_var('TABLE_NAME')
TABLE_ID = f'{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}'

VECTOR_SEARCH_INDEX_NAME = common.get_env_var('VECTOR_SEARCH_INDEX_NAME')
EMBEDDING_DIMENSIONALITY = int(common.get_env_var('EMBEDDING_DIMENSIONALITY'))

text_embedding_generator = generate_embedding_lib.TextEmbeddingGenerator(
    embedding_dimensionality=EMBEDDING_DIMENSIONALITY
)
bigquery_connector = generate_embedding_lib.BigQueryConnector(
    project_id=PROJECT_ID, embedding_table_name=TABLE_ID
)
vector_search_connector = generate_embedding_lib.VectorSearchConnector(
    project_id=PROJECT_ID,
    location=LOCATION,
    index_name=VECTOR_SEARCH_INDEX_NAME,
)


@functions_framework.http
def run(request):
  """HTTP Cloud Function.

  Args:
      request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

  Returns:
      The response text, or any set of values that can be turned into a
      Response object using `make_response`
      <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
  Note:
      For more information on how Flask integrates with Cloud
      Functions, see the `Writing HTTP functions` page.
      <https://cloud.google.com/functions/docs/writing/http#http_frameworks>
  """

  if request.method != 'POST':
    return 'Method Not Allowed', 405
  if request.content_type != 'application/json':
    return 'Unsupported Media Type', 415

  try:
    request_json = request.get_json(silent=True)
    if not request_json:
      return 'Bad Request: No JSON data provided', 400
    if 'product' not in request_json:
      return 'Bad Request: No product provided', 400
    product = common.Product(**request_json.get('product'))
    upsert = request_json.get('upsert_to_vector_search', False)
  except (TypeError, ValueError) as e:
    return f'Bad Request: Invalid JSON format: {e}', 400

  embedding = text_embedding_generator.get_embedding_for_product(product)
  bigquery_connector.insert_embedding_for_product(
      product=product, embedding=embedding
  )
  if upsert:
    vector_search_connector.upsert_datapoint(
        product=product, embedding=embedding
    )
  return 'OK', 200
