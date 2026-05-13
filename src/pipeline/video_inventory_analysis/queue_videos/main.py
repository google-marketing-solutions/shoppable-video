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

"""Queue Videos Cloud Run Job."""

import logging

import queue_videos_lib

from shared import common
from shared import logging_config

logging_config.configure_logging()
logger = logging.getLogger(__name__)


# Video source configuration
try:
  ADS_CUSTOMER_ID = common.get_env_var('ADS_CUSTOMER_ID')
except ValueError:
  logger.info('No ADS_CUSTOMER_ID passed to job, skipping Google Ads source.')
  ADS_CUSTOMER_ID = None

try:
  SPREADSHEET_ID = common.get_env_var('SPREADSHEET_ID')
except ValueError:
  logger.info('No SPREADSHEET_ID passed to job, skipping Google Sheet source.')
  SPREADSHEET_ID = None

# General configuration
PROJECT_ID = common.get_env_var('PROJECT_ID')
DATASET_ID = common.get_env_var('DATASET_ID')
LOCATION = common.get_env_var('LOCATION')
QUEUE_ID = common.get_env_var('QUEUE_ID')
CLOUD_FUNCTION_URL = common.get_env_var('CLOUD_FUNCTION_URL')
VIDEO_LIMIT = int(common.get_env_var('VIDEO_LIMIT'))


def _queue_videos() -> None:
  """Queries for videos and pushes them to a Cloud Task queue."""
  logger.debug(
      'Initializing VideoQueuer for Project: %s, Dataset: %s, Queue: %s',
      PROJECT_ID,
      DATASET_ID,
      QUEUE_ID,
  )
  video_queuer = queue_videos_lib.VideoQueuer(
      project_id=PROJECT_ID,
      dataset_id=DATASET_ID,
      location=LOCATION,
      queue_id=QUEUE_ID,
      customer_id=ADS_CUSTOMER_ID,
      spreadsheet_id=SPREADSHEET_ID,
  )
  logger.info('Retrieving unprocessed videos up to limit: %d', VIDEO_LIMIT)
  videos = video_queuer.get_videos(video_limit=VIDEO_LIMIT)
  if videos:
    logger.debug('Found %d candidate videos for queuing.', len(videos))
    if not video_queuer.is_queue_empty():
      logger.warning('Target Tasks queue is not empty. Aborting execution.')
      raise queue_videos_lib.CloudTasksQueueNotEmptyError(
          'Cloud Tasks queue is not empty. Exiting to prevent duplicate tasks.'
      )
    logger.info('Submitting video tasks to endpoint: %s', CLOUD_FUNCTION_URL)
    video_queuer.push_videos(
        videos=videos, cloud_function_url=CLOUD_FUNCTION_URL
    )
  else:
    logger.info('No new videos found.')


def main():
  """Entry point for the Cloud Run job."""
  try:
    _queue_videos()
  except Exception as e:
    logging.error('An error occurred in the video queuing job: %s', e)
    # Re-raise the exception to ensure the job fails and can be monitored.
    raise


if __name__ == '__main__':
  main()
