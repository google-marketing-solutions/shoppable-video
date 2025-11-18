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


"""HTTP Cloud Function for generating product embeddings.

This Cloud Function is triggered by an HTTP POST request containing product
data. It generates an embedding for the product and stores the result in
BigQuery.
"""

import logging
import functions_framework
import generate_embedding_lib
from google.cloud import logging as cloud_logging

try:
  from shared import common  # pylint: disable=g-import-not-at-top
  from shared import embeddings  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ...shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level
  from ...shared import embeddings  # pylint: disable=g-import-not-at-top, relative-beyond-top-level

# Cloud Logging
logging_client = cloud_logging.Client()
logging_client.setup_logging()

# Environment Global Variables
PROJECT_ID = common.get_env_var('PROJECT_ID')
GOOGLE_API_KEY = common.get_env_var('GOOGLE_API_KEY')

# BigQuery Variables
DATASET_ID = common.get_env_var('DATASET_ID')
TABLE_NAME = common.get_env_var('TABLE_NAME')
TABLE_ID = f'{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}'

# Embedding Variables
EMBEDDING_MODEL_NAME = common.get_env_var('EMBEDDING_MODEL_NAME')
EMBEDDING_DIMENSIONALITY = int(common.get_env_var('EMBEDDING_DIMENSIONALITY'))

text_embedding_generator = embeddings.TextEmbeddingGenerator(
    embedding_model_name=EMBEDDING_MODEL_NAME,
    embedding_dimensionality=EMBEDDING_DIMENSIONALITY,
    api_key=GOOGLE_API_KEY,
)
bigquery_connector = generate_embedding_lib.BigQueryConnector(
    embedding_table_name=TABLE_ID
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

  except (TypeError, ValueError) as e:
    return f'Bad Request: Invalid JSON format: {e}', 400

  text_for_embedding = product.get_text_for_embedding()
  embedding = text_embedding_generator.generate_embedding(
      text=text_for_embedding, resource_id=product.offer_id
  )
  bigquery_connector.insert_embedding_for_product(
      product=product, embedding=embedding
  )
  logging.info(
      'Successfully generated & stored embedding for product %s',
      product.offer_id,
  )
  return 'OK', 200
