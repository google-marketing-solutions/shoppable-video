"""Imports a BigQuery table into a Vector Search index."""

import logging

from google.cloud import aiplatform
from google.cloud import aiplatform_v1beta1
from google.cloud import logging as cloud_logging
from google.protobuf import json_format

logging_client = cloud_logging.Client()
logging_client.setup_logging()

try:
  from shared import common  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ...shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level


PROJECT_ID = common.get_env_var('PROJECT_ID')
LOCATION = common.get_env_var('LOCATION')
DATASET_ID = common.get_env_var('DATASET_ID')
TABLE_NAME = common.get_env_var('TABLE_NAME')
TABLE_ID = f'bq://{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}'

VECTOR_SEARCH_INDEX_NAME = common.get_env_var('VECTOR_SEARCH_INDEX_NAME')

aiplatform.init(project=PROJECT_ID, location=LOCATION)


def import_index_from_bq(table_id: str, index_name: str) -> None:
  """Imports a BigQuery table into a Vector Search index.

  Args:
    table_id: The ID of the BigQuery table to import.
    index_name: The name of the Vector Search index to import the table into.
  """
  # TODO(blakegoodwin): Replace with aiplatform once feature is in prod branch.
  client_options = {'api_endpoint': f'{LOCATION}-aiplatform.googleapis.com'}
  client = aiplatform_v1beta1.IndexServiceClient(client_options=client_options)
  config = {
      'big_query_source_config': {
          'table_path': table_id,
          'datapoint_field_mapping': {
              'id_column': 'id',
              'embedding_column': 'embedding',
          },
      }
  }
  request = aiplatform_v1beta1.ImportIndexRequest(
      name=index_name, is_complete_overwrite=True, config=config
  )
  operation = client.import_index(request=request)
  logging.info(
      'ImportIndexRequest has been submitted, waiting for operation to'
      ' complete...',
      extra={
          'json_fields': {
              'request': json_format.MessageToJson(request._pb),
          }
      },
  )
  response = operation.result(timeout=1800)
  logging.info(
      'ImportIndexRequest operation has completed!',
      extra={
          'json_fields': {
              'request': json_format.MessageToJson(request._pb),
              'response': str(response),
          }
      },
  )


def main():
  import_index_from_bq(table_id=TABLE_ID, index_name=VECTOR_SEARCH_INDEX_NAME)


if __name__ == '__main__':
  main()
