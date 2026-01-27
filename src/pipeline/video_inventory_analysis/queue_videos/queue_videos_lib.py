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

"""Library for queuing videos for analysis."""

import base64
import dataclasses
import json
import logging
from typing import Any, List, Optional, Tuple

import google.auth
from google.cloud import bigquery
from google.cloud import storage
from google.cloud import tasks_v2
from googleapiclient import discovery
from googleapiclient.errors import HttpError

try:
  from shared import common  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ...shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level

Video = common.Video
VideoMetadata = common.VideoMetadata
Source = common.Source


class Error(Exception):
  """Base error class for this module."""


class BigQueryReadError(Error):
  """Raised when an error occurs while reading from BigQuery."""


class CloudTasksPublishError(Error):
  """Raised when an error occurs while publishing to Cloud Tasks."""


class CloudTasksQueueNotEmptyError(Error):
  """Raised when the Cloud Tasks queue has unfinished tasks."""


class VideoQueuer:
  """A class for queuing videos from various sources for analysis.

  This class retrieves video information from Google Ads, Google Sheets, and
  Google Cloud Storage, filters out videos that have already been processed,
  and pushes the unprocessed videos to a Cloud Tasks queue for further
  analysis.
  """

  def __init__(
      self,
      project_id: str,
      dataset_id: str,
      location: str,
      queue_id: str,
      customer_id: Optional[str] = None,
      spreadsheet_id: Optional[str] = None,
      bigquery_client: Optional[bigquery.Client] = None,
      storage_client: Optional[storage.Client] = None,
      tasks_client: Optional[tasks_v2.CloudTasksClient] = None,
      sheets_service: Optional[Any] = None,
      youtube_service: Optional[Any] = None,
  ):
    """Initializes the VideoQueuer instance.

    Args:
      project_id: The Google Cloud project ID.
      dataset_id: The BigQuery dataset ID.
      location: The Google Cloud location for Cloud Tasks.
      queue_id: The Cloud Tasks queue ID.
      customer_id: The Google Ads customer ID.
      spreadsheet_id: The Google Sheet ID for manual video entry.
      bigquery_client: An optional BigQuery client instance.
      storage_client: An optional Cloud Storage client instance.
      tasks_client: An optional Cloud Tasks client instance.
      sheets_service: An optional Google Sheets service instance.
      youtube_service: An optional YouTube service instance.

    Raises:
      ValueError: If neither customer_id nor spreadsheet_id is provided.
    """
    if not customer_id and not spreadsheet_id:
      raise ValueError("Either customer_id or spreadsheet_id is required.")

    self.project_id = project_id
    self.dataset_id = dataset_id
    self.customer_id = customer_id
    self.location = location
    self.queue_id = queue_id
    self.spreadsheet_id = spreadsheet_id

    creds, _ = google.auth.default()

    self.bigquery_client = bigquery_client or bigquery.Client()
    self.storage_client = storage_client or storage.Client()
    self.tasks_client = tasks_client or tasks_v2.CloudTasksClient()
    if self.spreadsheet_id is not None:
      self.sheets_service = sheets_service or discovery.build(
          "sheets", "v4", credentials=creds
      )
    self.youtube_service = youtube_service or discovery.build(
        "youtube", "v3", credentials=creds
    )

    self.parent_queue = self.tasks_client.queue_path(
        self.project_id, self.location, self.queue_id
    )

  def get_videos(self, video_limit: int = 10) -> List[Video]:
    """Retrieves a list of unprocessed videos from all configured sources.

    This method fetches videos from Google Ads and/or a Google Sheet,
    filters out any videos that have already been processed, and returns
    a list of unique, unprocessed videos up to the specified limit.

    Args:
      video_limit: The maximum number of videos to return.

    Returns:
      A list of Video objects representing the unprocessed videos.
    """
    videos = []
    if self.spreadsheet_id:
      videos.extend(self._get_videos_from_google_sheet())
    if self.customer_id:
      videos.extend(self._get_videos_from_google_ads())

    processed_video_ids, processed_gcs_uris = self._get_processed_videos()

    unprocessed_videos = []
    seen_video_ids = set()
    seen_gcs_uris = set()

    for video in videos:
      if video.video_id:
        if (
            video.video_id in processed_video_ids
            or video.video_id in seen_video_ids
        ):
          continue
        seen_video_ids.add(video.video_id)
      elif video.gcs_uri:
        if (
            video.gcs_uri in processed_gcs_uris
            or video.gcs_uri in seen_gcs_uris
        ):
          continue
        seen_gcs_uris.add(video.gcs_uri)
      unprocessed_videos.append(video)

    # Check if unprocessed Youtube videos are public and get titles
    unprocessed_youtube_videos = [
        video for video in unprocessed_videos if video.video_id is not None
    ]
    if unprocessed_youtube_videos:
      video_ids = [video.video_id for video in unprocessed_youtube_videos]
      video_info = self._get_youtube_video_info(video_ids)
      excluded_videos_info = []
      for video in unprocessed_youtube_videos:
        if video.video_id in video_info:
          privacy_status, title = video_info[video.video_id]
          if privacy_status != "public":
            excluded_videos_info.append({
                "video_id": video.video_id,
                "status": privacy_status,
            })
            unprocessed_videos.remove(video)
          else:
            video.metadata = VideoMetadata(title=title)

      if excluded_videos_info:
        logging.info(
            "Excluded %d YouTube videos due to non-public status.",
            len(excluded_videos_info),
            extra={"json_fields": {"excluded_videos": excluded_videos_info}},
        )

    return unprocessed_videos[:video_limit]

  def push_videos(
      self,
      videos: List[Video],
      cloud_function_url: str,
  ):
    """Pushes a list of videos to a Cloud Tasks queue.

    Each video is sent as a separate task to the specified Cloud Function URL.

    Args:
      videos: A list of Video objects to be pushed to the queue.
      cloud_function_url: The URL of the Cloud Function that will process the
        tasks.

    Raises:
      CloudTasksPublishError: If an error occurs while creating a task.
    """
    task_count = 0

    for video in videos:
      try:
        payload = {"video": dataclasses.asdict(video)}
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=cloud_function_url,
                body=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-type": "application/json",
                },
            )
        )
        self.tasks_client.create_task(
            tasks_v2.CreateTaskRequest(
                parent=self.parent_queue,
                task=task,
            )
        )
        task_count += 1
      except Exception as e:
        raise CloudTasksPublishError(e) from e

    logging.info(
        "Submitted %d tasks to Cloud Tasks.",
        task_count,
        extra={
            "json_fields": {"videos": [dataclasses.asdict(v) for v in videos]}
        },
    )

  def is_queue_empty(self) -> bool:
    """Checks if the Cloud Tasks queue is empty.

    Returns:
      True if the queue has no pending tasks, False otherwise.
    """
    request = tasks_v2.ListTasksRequest(parent=self.parent_queue)
    response = self.tasks_client.list_tasks(request=request)
    return not bool(list(response.tasks))

  def _get_videos_from_google_ads(self) -> List[Video]:
    """Fetches video IDs from Google Ads campaigns via BigQuery.

    Returns:
      A list of Video objects from Google Ads.

    Raises:
      BigQueryReadError: If an error occurs while querying BigQuery.
    """
    query = f"""
        SELECT DISTINCT
          video_id,
        FROM
          `{self.project_id}.{self.dataset_id}.ads_videos_{self.customer_id}`
        WHERE
          campaign_advertising_channel_type = 'DEMAND_GEN'
          AND _DATA_DATE = _LATEST_DATE
    """
    try:
      query_job = self.bigquery_client.query(query)
      rows = query_job.result()
    except Exception as e:
      raise BigQueryReadError(e) from e
    videos = [
        Video(source=Source.GOOGLE_ADS, video_id=row.video_id) for row in rows  # type: ignore
    ]
    return videos

  def _get_videos_from_google_sheet(self) -> List[Video]:
    """Fetches video IDs and GCS URIs from a Google Sheet.

    This method reads from two sheets: 'VideoIDs' for YouTube video IDs and
    'GCS' for Google Cloud Storage URIs. It processes the GCS URIs to find
    video files.

    Returns:
      A list of Video objects from the Google Sheet.

    Raises:
      HttpError: If there is an issue accessing the Google Sheet.
    """
    try:
      yt_ids_videos = self._get_youtube_ids_from_sheet()
      gcs_uris_from_sheet = self._get_gcs_uris_from_sheet()
      gcs_uris_videos = []
      for gcs_uri in gcs_uris_from_sheet:
        gcs_uris_videos.extend(self._process_gcs_uri(gcs_uri))
      return yt_ids_videos + gcs_uris_videos
    except HttpError as e:
      if e.resp.status == 404:
        logging.warning(
            "Google Sheet with ID %s not found. Returning empty list.",
            self.spreadsheet_id,
        )
        return []
      elif e.resp.status == 403:
        logging.error(
            "Google Sheet with ID %s returned a 403 Forbidden error. Please"
            " ensure the Google Sheet is shared with the service account.",
            self.spreadsheet_id,
        )
        raise
      raise

  def _get_youtube_ids_from_sheet(self) -> List[Video]:
    """Fetches YouTube video IDs from the 'VideoIDs' sheet."""
    video_ids_result = (
        self.sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=self.spreadsheet_id, range="VideoIDs!A2:A")
        .execute()
    )
    values = video_ids_result.get("values", [])
    logging.debug("Retrieved %d rows of YT IDs from Google Sheet", len(values))
    return [
        Video(source=Source.MANUAL_ENTRY, video_id=row[0])  # type: ignore
        for row in values
        if row and row[0]
    ]

  def _get_youtube_video_info(self, video_ids: List[str]):
    """Gets the info for a list of YouTube videos.

    Args:
      video_ids: A list of YouTube video IDs.

    Returns:
      A dictionary mapping video IDs to a tuple of (privacy_status, title).
    """
    video_ids_chunks = [
        video_ids[i : i + 50] for i in range(0, len(video_ids), 50)
    ]

    video_items = []
    for chunk in video_ids_chunks:
      request = self.youtube_service.videos().list(
          part="status,snippet", id=",".join(chunk)
      )
      response = request.execute()
      video_items.extend(response.get("items", []))

    video_info = {}
    for item in video_items:
      video_info[item["id"]] = (
          item["status"]["privacyStatus"],
          item["snippet"]["title"],
      )
    return video_info

  def _get_gcs_uris_from_sheet(self) -> List[str]:
    """Fetches GCS URIs from the 'GCS' sheet."""
    gcs_uris_result = (
        self.sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=self.spreadsheet_id, range="GCS!A2:A")
        .execute()
    )
    gcs_uris_from_sheet = [
        row[0] for row in gcs_uris_result.get("values", []) if row and row[0]
    ]
    logging.debug(
        "Retrieved %d GCS URIs from Google Sheet", len(gcs_uris_from_sheet)
    )
    return gcs_uris_from_sheet

  def _process_gcs_uri(self, gcs_uri: str) -> List[Video]:
    """Processes a GCS URI to find video files and create Video objects.

    If the URI points to a folder, it will list the contents and identify
    video files based on their extensions.

    Args:
      gcs_uri: The Google Cloud Storage URI to process.

    Returns:
      A list of Video objects for the video files found at the GCS URI.
    """
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}

    try:
      bucket_name, prefix = common.split_gcs_uri(gcs_uri)
      prefix = prefix or ""
      blobs = list(self.storage_client.list_blobs(bucket_name, prefix=prefix))

      if not blobs:
        logging.warning("No objects found for GCS URI: %s", gcs_uri)
        return []

      video_blobs = [
          blob
          for blob in blobs
          if any(blob.name.lower().endswith(ext) for ext in video_extensions)
      ]

      if not video_blobs:
        is_single_file = (
            len(blobs) == 1
            and blobs[0].name == prefix
            and not gcs_uri.endswith("/")
        )
        if is_single_file:
          logging.warning("GCS URI %s is not a video file.", gcs_uri)
        else:
          logging.warning("No video files found for GCS URI/prefix %s", gcs_uri)
        return []

      videos = []
      for blob in video_blobs:
        video_uri = f"gs://{bucket_name}/{blob.name}"
        blob.reload()  # Refreshes metadata for hash retrieval
        md5_hash = base64.b64decode(blob.md5_hash).hex()

        # Use filename as title
        title = blob.name.split("/")[-1]

        videos.append(
            Video(
                source=Source.MANUAL_ENTRY,  # type: ignore
                gcs_uri=video_uri,
                md5_hash=md5_hash,
                metadata=VideoMetadata(title=title),  # type: ignore
            )
        )
      return videos

    except ValueError as e:
      logging.error("Invalid GCS URI %s: %s", gcs_uri, e)
    except Exception as e:  # pylint: disable=broad-exception-caught
      logging.error("Error processing GCS URI %s: %s", gcs_uri, e)

    return []

  def _get_processed_videos(self) -> Tuple[List[str], List[str]]:
    """Retrieves the IDs and GCS URIs of videos that have been processed.

    Returns:
      A tuple containing two lists: one of processed video IDs and one of
      processed GCS URIs.

    Raises:
      BigQueryReadError: If an error occurs while querying BigQuery.
    """
    query = f"""
        SELECT DISTINCT
          video_id,
          gcs_uri,
        FROM
          `{self.project_id}.{self.dataset_id}.video_analysis`
    """
    try:
      query_job = self.bigquery_client.query(query)
      rows = query_job.result()
    except Exception as e:
      raise BigQueryReadError(e) from e

    video_ids, gcs_uris = [], []
    for row in rows:
      if row.gcs_uri:
        gcs_uris.append(row.gcs_uri)
      elif row.video_id:
        video_ids.append(row.video_id)
    return video_ids, gcs_uris
