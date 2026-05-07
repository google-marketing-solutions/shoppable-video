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

"""Entrypoint script initiating automated Data Synchronization workflows."""

import logging
import os
import sys

from app.services import sync_service
from google.cloud import bigquery
from google.cloud import firestore
from google.cloud import logging as cloud_logging

# Configure central telemetry
logging_client = cloud_logging.Client()
logging_client.setup_logging()
logger = logging.getLogger(__name__)


def main():
  """Initializes environment context and invokes execution orchestrator."""
  project_id = os.environ.get("PROJECT_ID")
  dataset_id = os.environ.get("DATASET_ID", "shoppable_video")
  merchant_id = os.environ.get("MERCHANT_ID")
  firestore_database = os.environ.get("FIRESTORE_DATABASE", "(default)")

  if not project_id or not merchant_id:
    logger.critical(
        "CRITICAL: Essential environment identifiers (PROJECT_ID, MERCHANT_ID)"
        " missing."
    )
    sys.exit(1)

  logger.info(
      "Building environment context and establishing cloud persistence"
      " clients..."
  )

  bigquery_client = bigquery.Client(project=project_id)
  firestore_client = firestore.Client(
      project=project_id, database=firestore_database
  )

  service = sync_service.DataSyncService(
      bigquery_client=bigquery_client,
      firestore_client=firestore_client,
      project_id=project_id,
      dataset_id=dataset_id,
      merchant_id=merchant_id,
  )

  try:
    logger.info("Unified Data Synchronization Cycle Initiating.")

    # Phase 1: Execute individual atomic cycles
    last_video_timestamp = service.get_last_sync_timestamp("videos")
    last_match_timestamp = service.get_last_sync_timestamp("matches")

    logger.info(
        "Baseline State -> Videos: %s | Matches: %s",
        last_video_timestamp,
        last_match_timestamp,
    )

    service.sync_videos(last_video_timestamp)
    service.sync_matched_products(last_match_timestamp)

    # Critical Optimization: Refactored to fetch identifiers solely
    # from Firestore
    service.sync_inventory()

    logger.info("Successfully finalized absolute synchronization flow state.")

  except Exception as e:  # pylint: disable=broad-exception-caught
    logger.exception(
        "System synchronization failure boundary breached: %s", str(e)
    )
    sys.exit(1)


if __name__ == "__main__":
  main()
