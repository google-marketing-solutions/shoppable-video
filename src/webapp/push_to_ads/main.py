# Copyright 2026 Google LLC
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

"""Main entry point for the Google Ads Insertion Cloud Run Job.

This module initializes clients and triggers the AdsInsertionProcessor.
"""

import logging
import os
import sys
import uuid
import ads_service as ads_svc_module
import dotenv
from google.cloud import firestore
from google.cloud.logging.handlers import StructuredLogHandler
import processor


def _configure_logging() -> None:
  """Configures appropriate logging backend based on runtime environment."""
  dotenv.load_dotenv()

  log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
  is_cloud = (
      "K_SERVICE" in os.environ or os.environ.get("ENVIRONMENT") == "production"
  )

  if is_cloud:
    logging.basicConfig(level=log_level, handlers=[StructuredLogHandler()])
  else:
    local_handler = logging.StreamHandler(sys.stdout)
    local_handler.setFormatter(
        logging.Formatter("%(levelname)s - %(name)s - %(message)s")
    )
    logging.basicConfig(level=log_level, handlers=[local_handler])


# Initialize environment & log subsystem immediately upon module loads
_configure_logging()
logger = logging.getLogger(__name__)

project_id = os.environ.get("PROJECT_ID")
if not project_id:
  sys.exit("CRITICAL: PROJECT_ID must be configured in environment.")

firestore_database = os.environ.get("FIRESTORE_DATABASE", "(default)")


def main() -> None:
  """Initializes and executes the background Ads Insertion Processor."""

  worker_id = str(uuid.uuid4())
  firestore_client = firestore.Client(
      project=project_id, database=firestore_database
  )

  try:
    developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    if not developer_token:
      raise ValueError(
          "GOOGLE_ADS_DEVELOPER_TOKEN must be set in the environment."
      )

    customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
    if not customer_id:
      raise ValueError("GOOGLE_ADS_CUSTOMER_ID must be set in the environment.")

    ads_service = ads_svc_module.AdsService(
        customer_id=customer_id,
        developer_token=developer_token,
    )
    ads_processor = processor.AdsInsertionProcessor(
        firestore_client=firestore_client,
        ads_service=ads_service,
        worker_id=worker_id,
    )

    ads_processor.run()

  except Exception as e:  # pylint: disable=broad-exception-caught
    logger.exception("Critical bootstrap failure: %s", str(e))
    sys.exit(1)


if __name__ == "__main__":
  main()
