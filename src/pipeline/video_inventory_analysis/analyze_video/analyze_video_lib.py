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

"""Library for analyzing videos to identify products.

This module provides functionalities to analyze videos from various sources
(like YouTube and Google Cloud Storage) using Gemini to identify
products shown in the video. The analysis results, including the identified
products, are then stored in a BigQuery table for further use.

The main components of this library are:
- `VideoAnalyzer`: A class that orchestrates the video analysis process. It
  retrieves video content, sends it to the Generative AI API for analysis, and
  processes the results.
- `BigQueryConnector`: A class to handle interactions with BigQuery, including
  inserting the video analysis results.
"""

import dataclasses
import datetime
import logging
import mimetypes
import time
from typing import Sequence
from google import genai
from google.cloud import bigquery
from google.cloud import storage
from google.genai import types
import tenacity

try:
  from shared import common  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ...shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level


class Error(Exception):
  """Base exception for errors raised by this module."""


class GenerativeAIError(Error):
  """Raised when an error occurs with the Generative AI API."""


class CloudStorageError(Error):
  """Raised when a Cloud Storage operation fails."""


class BigQueryError(Error):
  """Raised when a BigQuery operation fails."""


class VideoAnalyzer:
  """Analyzes videos to identify products using a generative model.

  This class orchestrates the video analysis process. It retrieves video
  content from either a GCS URI or a YouTube URL, sends it to Gemini for
  analysis, and processes the results. It also handles the temporary upload of
  video files to Gemini and their subsequent deletion.
  """

  def __init__(
      self,
      prompt: str,
      generative_model_name: str,
      storage_client: storage.Client | None = None,
      genai_client: genai.Client | None = None,
  ):
    """Initializes the VideoAnalyzer.

    Args:
      prompt: The prompt to use for video analysis.
      generative_model_name: The name of the generative model to use.
      storage_client: An optional Cloud Storage client instance.
      genai_client: An optional Generative AI client instance.
    """

    self.prompt = types.Part(text=prompt)
    self.generative_model_name = generative_model_name
    self.storage_client = storage_client or storage.Client()
    self.genai_client = genai_client or genai.Client()

    self.genai_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=list[common.IdentifiedProduct],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        top_k=1,
        top_p=0.2,
    )

  def analyze_video(
      self, video: common.Video
  ) -> Sequence[common.IdentifiedProduct]:
    """Analyzes a video using a generative model to identify products.

    Args:
      video: The video to analyze.

    Returns:
      A list of identified products.

    Raises:
      GenerativeAIError: If the generative AI API call fails.
    """

    if video.gcs_uri:
      video_content = self._upload_video_from_gcs(gcs_uri=video.gcs_uri)
    else:
      video_content = types.Part(
          file_data=types.FileData(
              file_uri=f"https://www.youtube.com/watch?v={video.video_id}"
          )
      )

    response = None
    try:
      response = self.genai_client.models.generate_content(
          model=self.generative_model_name,
          contents=[video_content, self.prompt],
          config=self.genai_config,
      )
      identified_products: list[common.IdentifiedProduct] = response.parsed  # type: ignore
    except Exception as e:
      raise GenerativeAIError(e) from e
    finally:
      if (
          video.gcs_uri is not None
          and isinstance(video_content, types.File)
          and video_content.name
      ):
        self.genai_client.files.delete(name=video_content.name)

    return identified_products or []

  def _upload_video_from_gcs(self, gcs_uri: str) -> types.File:
    """Uploads a video from Google Cloud Storage to Gemini API.

    Args:
      gcs_uri: The GCS URI of the video to upload.

    Returns:
      A File object representing the uploaded video.

    Raises:
      GenerativeAIError: If the video upload fails.
    """
    bucket_name, blob_name = common.split_gcs_uri(gcs_uri)
    bucket = self.storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    mime_type, _ = mimetypes.guess_type(blob_name)

    if mime_type is None:
      logging.debug("Unable to guess mime_type, will default to video/mp4.")
      mime_type = "video/mp4"

    with blob.open("rb") as video_file:
      video_content = self.genai_client.files.upload(
          file=video_file, config={"mime_type": mime_type}
      )

    video_content_name = video_content.name
    if video_content_name is None:
      raise GenerativeAIError(
          f"No name reference returned from files.upload for GCS URI {gcs_uri}"
      )

    time.sleep(5)  # add delay before polling for video status.
    video_content = self._wait_for_video_processing(video_content_name, gcs_uri)

    return video_content

  @tenacity.retry(
      stop=tenacity.stop_after_delay(300),  # 5 minutes
      wait=tenacity.wait_exponential(multiplier=1, min=2, max=60),
      retry=tenacity.retry_if_exception_type(GenerativeAIError),
      after=tenacity.after_log(logging.getLogger(__name__), logging.INFO),
  )
  def _wait_for_video_processing(
      self, video_content_name: str, gcs_uri: str
  ) -> types.File:
    """Waits for a video to be processed by the generative AI API.

    Args:
      video_content_name: The reference name of the video file to check.
      gcs_uri: The GCS URI of the video for logging purposes.

    Returns:
      The processed video file.

    Raises:
      GenerativeAIError: If the video processing is not complete.
    """
    video_content = self.genai_client.files.get(name=video_content_name)
    if video_content.state != "ACTIVE":
      logging.debug(
          "Uploaded file %s for GCS URI %s is in state %s, waiting for ACTIVE"
          " state",
          video_content_name,
          gcs_uri,
          video_content.state,
      )
      raise GenerativeAIError(
          f"Video {video_content_name} is not processed yet."
      )
    logging.info(
        "Uploaded file %s for GCS URI %s is in state ACTIVE, continuing...",
        video_content_name,
        gcs_uri,
    )
    return video_content


class BigQueryConnector:
  """Handles interactions with BigQuery for video analysis results.

  This class is responsible for writing video analysis data to a specified
  BigQuery table. It abstracts the details of BigQuery table insertion and
  error handling.
  """

  def __init__(
      self,
      table_id: str,
      bigquery_client: bigquery.Client | None = None,
  ):
    """Initializes the BigQueryWriter.

    Args:
      table_id: The BigQuery table ID for storing analysis results.
      bigquery_client: An optional BigQuery client instance. If not provided, a
        new client will be created.
    """

    self.table_id = table_id
    self.bigquery_client = bigquery_client or bigquery.Client()

  def insert_video_analysis(
      self,
      video: common.Video,
      identified_products: Sequence[common.IdentifiedProduct],
  ):
    """Inserts video analysis results into a BigQuery table.

    Args:
      video: The video that was analyzed.
      identified_products: A list of products identified in the video.

    Raises:
      BigQueryError: If the BigQuery insertion fails.
    """

    insertion_datetime = datetime.datetime.now(datetime.timezone.utc)
    insertion_timestamp = insertion_datetime.strftime("%Y-%m-%d %H:%M:%S")

    rows_to_insert = [{
        "uuid": video.uuid,
        "timestamp": insertion_timestamp,
        "source": video.source.value,
        "video_id": video.video_id,
        "metadata": (
            dataclasses.asdict(video.metadata) if video.metadata else None
        ),
        "gcs_uri": video.gcs_uri,
        "md5_hash": video.md5_hash,
        "status": "SUCCESS",
        "error_message": None,
        "identified_products": [p.to_dict() for p in identified_products],
    }]
    errors = self.bigquery_client.insert_rows_json(
        self.table_id, rows_to_insert
    )
    if errors:
      raise BigQueryError(f"Failed to insert rows into BigQuery: {errors}")
