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

from google.ads.googleads import client
from google.ads.googleads import errors
import google.auth
from google.cloud import bigquery
from google.cloud import storage
from google.cloud import tasks_v2
from googleapiclient import discovery
from googleapiclient import errors as apiclient_errors

from shared import common

logger = logging.getLogger(__name__)

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


class GoogleAdsAPIError(Error):
  """Raised when an error occurs while querying Google Ads API."""


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
      google_ads_client: Optional[client.GoogleAdsClient] = None,
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
      google_ads_client: An optional Google Ads client instance.

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

    creds, _ = google.auth.default(
        scopes=[
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/youtube.readonly",
        ]
    )

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
    if self.customer_id is not None:
      if google_ads_client is not None:
        self.google_ads_client = google_ads_client
      else:
        adwords_creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/adwords"]
        )
        developer_token = common.get_env_var("GOOGLE_ADS_DEVELOPER_TOKEN")
        self.google_ads_client = client.GoogleAdsClient(
            credentials=adwords_creds,
            developer_token=developer_token,
            login_customer_id=self.customer_id,
            use_proto_plus=True,
        )
    else:
      self.google_ads_client = None

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
      sheet_videos = self._get_videos_from_google_sheet()
      logger.info(
          "Fetched %d videos from Google Sheets source.", len(sheet_videos)
      )
      videos.extend(sheet_videos)
    if self.customer_id:
      ads_videos = self._get_videos_from_google_ads()
      logger.info("Fetched %d videos from Google Ads source.", len(ads_videos))
      videos.extend(ads_videos)

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
          privacy_status, title, description = video_info[video.video_id]
          if privacy_status != "public":
            excluded_videos_info.append({
                "video_id": video.video_id,
                "status": privacy_status,
            })
            unprocessed_videos.remove(video)
          else:
            video.metadata = VideoMetadata(title=title, description=description)

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

  def _execute_gaql_query(
      self, customer_id: str, query: str, ignore_errors: bool = False
  ):
    """Executes a GAQL search stream query and yields rows.

    Args:
      customer_id: The Google Ads customer ID string.
      query: The GAQL query string to execute.
      ignore_errors: If True, suppresses GoogleAdsException and logs a warning
        instead.

    Yields:
      Google Ads API search stream result rows.

    Raises:
      ValueError: If the Google Ads client is not initialized.
      GoogleAdsAPIError: If the GAQL query fails and ignore_errors is False.
    """
    if not self.google_ads_client:

      raise ValueError("Google Ads client is required to query Google Ads API.")

    ga_service = self.google_ads_client.get_service("GoogleAdsService")
    try:
      logger.debug(
          "Executing GAQL search stream for customer_id: %s", customer_id
      )
      response = ga_service.search_stream(customer_id=customer_id, query=query)
      for batch in response:
        for row in batch.results:
          yield row
    except errors.GoogleAdsException as e:
      if ignore_errors:
        logger.warning("GAQL query failed for account %s: %s", customer_id, e)
      else:
        raise GoogleAdsAPIError(e) from e

  def _get_videos_from_google_ads(self) -> List[Video]:
    """Fetches video IDs from Google Ads Demand Gen campaigns via API.

    Returns:
      A list of Video objects from Google Ads.

    Raises:
      GoogleAdsAPIError: If an error occurs while querying Google Ads API.
    """
    customer_id_str = str(self.customer_id)

    # Determine accounts to query
    accounts_to_query = []
    is_manager = False
    customer_query = (
        "SELECT customer.id, customer.manager FROM customer LIMIT 1"
    )

    for row in self._execute_gaql_query(customer_id_str, customer_query):
      if row.customer.manager:
        is_manager = True
      else:
        accounts_to_query.append(str(row.customer.id))

    if is_manager:
      logger.debug(
          "Account %s is an MCC. Discovering child client accounts.",
          customer_id_str,
      )
      child_query = """
          SELECT customer_client.id
          FROM customer_client
          WHERE customer_client.level > 0
            AND customer_client.manager = FALSE
      """
      for row in self._execute_gaql_query(customer_id_str, child_query):
        accounts_to_query.append(str(row.customer_client.id))

    # Query each account for videos
    video_query = """
        SELECT
          campaign.advertising_channel_type,
          video.id
        FROM video
        WHERE
          campaign.advertising_channel_type = 'DEMAND_GEN'
    """
    video_ids = set()
    row_count = 0

    for account_id in accounts_to_query:
      account_video_ids = set()
      for row in self._execute_gaql_query(
          account_id, video_query, ignore_errors=True
      ):
        row_count += 1
        account_video_ids.add(row.video.id)
        video_ids.add(row.video.id)
      logger.info(
          "Pulled %d unique videos from account %s",
          len(account_video_ids),
          account_id,
      )

    logger.debug(
        "GAQL query returned %d total rows across %d unique video IDs from %d"
        " accounts.",
        row_count,
        len(video_ids),
        len(accounts_to_query),
    )
    videos = [
        Video(source=Source.GOOGLE_ADS, video_id=vid)  # type: ignore
        for vid in video_ids
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
      apiclient_errors.HttpError: If there is an issue accessing the Google
        Sheet.
    """

    try:
      yt_ids_videos = self._get_youtube_ids_from_sheet()
      gcs_uris_from_sheet = self._get_gcs_uris_from_sheet()
      gcs_uris_videos = []
      for gcs_uri in gcs_uris_from_sheet:
        gcs_uris_videos.extend(self._process_gcs_uri(gcs_uri))
      return yt_ids_videos + gcs_uris_videos
    except apiclient_errors.HttpError as e:
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
      A dictionary mapping video IDs to a tuple of
        (privacy_status, title, description).
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
          item["snippet"]["description"],
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
