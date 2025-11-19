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

"""HTTP Cloud Function for analyzing videos.

This Cloud Function is triggered by an HTTP POST request containing video data.
It orchestrates the process of analyzing the video to identify products,
generating embeddings for the identified products, and storing the results in
BigQuery.
"""

import logging
import os
from typing import Any, Dict

import analyze_video_lib
import functions_framework
from google.cloud import logging as cloud_logging


try:
  from shared import common  # pylint: disable=g-import-not-at-top
  from shared import embeddings  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ...shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level
  from ...shared import embeddings  # pylint: disable=g-import-not-at-top, relative-beyond-top-level

# Set up Cloud Logging
logging_client = cloud_logging.Client()
logging_client.setup_logging()

# BigQuery Configuration
PROJECT_ID = common.get_env_var('PROJECT_ID')
DATASET_ID = common.get_env_var('DATASET_ID')
TABLE_NAME = common.get_env_var('TABLE_NAME')
TABLE_ID = f'{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}'

# Gemini Configuration
GOOGLE_API_KEY = common.get_env_var('GOOGLE_API_KEY')
GENERATIVE_MODEL_NAME = common.get_env_var('GENERATIVE_MODEL_NAME')
EMBEDDING_MODEL_NAME = common.get_env_var('EMBEDDING_MODEL_NAME')
EMBEDDING_DIMENSIONALITY = int(common.get_env_var('EMBEDDING_DIMENSIONALITY'))

# Video Analysis Prompt
_PROMPT_FILE = os.path.join('config', 'video_analysis_prompt.txt')
with open(_PROMPT_FILE, 'r', encoding='utf-8') as f:
  PROMPT = f.read()

video_analyzer_cls = analyze_video_lib.VideoAnalyzer(
    prompt=PROMPT,
    generative_model_name=GENERATIVE_MODEL_NAME,
)
bigquery_connector = analyze_video_lib.BigQueryConnector(
    table_id=TABLE_ID,
)
text_embedding_generator = embeddings.TextEmbeddingGenerator(
    embedding_model_name=EMBEDDING_MODEL_NAME,
    embedding_dimensionality=EMBEDDING_DIMENSIONALITY,
    api_key=GOOGLE_API_KEY,
)


def _analyze_video(request_json: Dict[str, Any]) -> None:
  """Analyzes a video, generates embeddings, and stores the results.

  Args:
    request_json: The JSON payload from the request.

  Raises:
    ValueError: If the request JSON is invalid.
  """
  if not request_json or 'video' not in request_json:
    raise ValueError('No JSON data or video object provided')

  video_data = request_json['video']
  # Convert source string to Enum before creating the Video object
  if 'source' in video_data:
    video_data['source'] = common.Source(video_data['source'])

  video = common.Video(**video_data)
  identified_products = video_analyzer_cls.analyze_video(video)
  for identified_product in identified_products:
    resource_id = f'{video.get_resource_id()}_{identified_product.title}'
    embedding = text_embedding_generator.generate_embedding(
        identified_product.get_text_for_embedding(), resource_id
    )
    identified_product.embedding = embedding.values

  bigquery_connector.insert_video_analysis(video, identified_products)
  logging.info(
      'Identified %d products from video %s and stored results in BQ.',
      len(identified_products),
      video,
      extra={
          'json_fields': {
              'identified_products': [
                  p.to_dict(exclude_embedding=True) for p in identified_products
              ]
          }
      },
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
    _analyze_video(request.get_json(silent=True))
  except (TypeError, ValueError) as e:
    logging.error('Error processing request: %s', e)
    return f'Bad Request: Invalid JSON format or video object: {e}', 400
  except Exception as e:  # pylint: disable=broad-exception-caught
    logging.error('An unexpected error occurred: %s', e)
    return 'Internal Server Error', 500

  return 'OK', 200
