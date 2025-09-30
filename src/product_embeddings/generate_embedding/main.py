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

import os

import functions_framework
import generate_embedding_lib
from google.cloud import logging as cloud_logging

# Cloud Logging
logging_client = cloud_logging.Client()
logging_client.setup_logging()

# Environment Global Variables
PROJECT_ID = os.environ.get('PROJECT_ID', 'Project ID env variable is not set.')
DATASET_ID = os.environ.get('DATASET_ID', 'Dataset ID env variable is not set.')
TABLE_NAME = os.environ.get('TABLE_NAME', 'Table name env variable is not set.')
TABLE_ID = f'{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}'

try:
  EMBEDDING_DIMENSIONALITY = int(os.environ['EMBEDDING_DIMENSIONALITY'])
except (KeyError, ValueError):
  EMBEDDING_DIMENSIONALITY = None

text_embedding_generator = generate_embedding_lib.TextEmbeddingGenerator(
    embedding_dimensionality=EMBEDDING_DIMENSIONALITY
)
bigquery_connector = generate_embedding_lib.BigQueryConnector(
    project_id=PROJECT_ID, embedding_table_name=TABLE_ID
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
    product = generate_embedding_lib.Product(**request_json.get('product'))
  except (TypeError, ValueError) as e:
    return f'Bad Request: Invalid JSON format: {e}', 400

  embedding = text_embedding_generator.get_embedding_for_product(product)
  bigquery_connector.insert_embedding_for_product(
      product=product, embedding=embedding
  )
  return 'OK', 200
