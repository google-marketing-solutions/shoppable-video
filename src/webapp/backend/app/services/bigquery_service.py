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

"""This module provides a service for interacting with Google BigQuery."""
from typing import List, Dict, Any, Optional

from google.cloud import bigquery


class Error(Exception):
  """Base class for exceptions in this module."""


class BigQueryError(Error):
  """Exception raised for errors during BigQuery operations."""


class BigQueryService:
  """Service class for interacting with BigQuery."""

  def __init__(
      self, project_id: str, dataset_id: str, analysis_table_id: str,
      status_table_id: str, client: Optional[bigquery.Client] = None
  ):
    """Initializes the BigQueryService.

    Args:
      project_id: The Google Cloud project ID.
      dataset_id: The BigQuery dataset ID.
      analysis_table_id: The BigQuery table ID for video analysis records.
      status_table_id: The BigQuery table ID for candidate statuses.
      client: An optional BigQuery client instance. If not provided, a new one
        will be created.
    """
    self.project_id = project_id
    self.client = client or bigquery.Client(project=self.project_id)
    self.dataset_id = dataset_id
    self.analysis_table_id = analysis_table_id
    self.analysis_table_ref = (
        f"{self.project_id}.{self.dataset_id}."
        f"{self.analysis_table_id}"
    )
    self.status_table_id = status_table_id
    self.status_table_ref = (
        f"{self.project_id}.{self.dataset_id}."
        f"{self.status_table_id}"
    )

  def add_candidate_status(self, candidate_status: Dict[str,
                                                        Any]) -> Dict[str, Any]:
    """Adds a new candidate status record to BigQuery.

    Args:
      candidate_status: A dictionary containing the candidate status details,
        expected to have 'video_id', 'candidate_offer_id', and 'status'.

    Returns:
      The inserted candidate status dictionary.

    Raises:
      RuntimeError: If there are errors during the BigQuery row insertion.
    """
    record = {
        "video_analysis_uuid": candidate_status.get("video_analysis_uuid"),
        "candidate_offer_id": candidate_status.get("candidate_offer_id"),
        "status": candidate_status.get("status")
    }
    errors = self.client.insert_rows_json(self.status_table_ref, [record])
    if errors:
      raise RuntimeError(f"Error creating candidate status: {errors}")
    return candidate_status

  def get_latest_candidate_statuses(self) -> List[Dict[str, Any]]:
    """Gets the latest candidate statuses for each video and candidate offer.

    Returns:
      A list of dictionaries, where each dictionary represents a candidate
      status record.
    """
    query = f"""
            SELECT *
            FROM `{self.status_table_ref}`
            QUALIFY ROW_NUMBER() OVER (
              PARTITION BY video_analysis_uuid, candidate_offer_id
              ORDER BY timestamp DESC
            ) = 1
        """
    query_job = self.client.query(query)
    return [dict(row) for row in query_job]

  def get_candidate_statuses_by_status(self,
                                       status: str) -> List[Dict[str, Any]]:
    """Gets candidate statuses filtered by their current status.

    Args:
      status: The status to filter by (e.g., 'UNREVIEWED', 'APPROVED',
        'REJECTED').
    Returns:
      A list of dictionaries, each representing a candidate status record.
    """
    if status.upper() == "UNREVIEWED":
      query = f"""
                SELECT
                    t.video_analysis_uuid AS video_analysis_uuid,
                    m.matched_product_offer_id AS candidate_offer_id,
                    'Unreviewed' AS status
                FROM `{self.analysis_table_ref}` t,
                UNNEST(identified_product) AS ip,
                UNNEST(ip.matched_product) AS m
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM `{self.status_table_ref}` s
                    WHERE s.video_analysis_uuid = t.video_analysis_uuid
                    AND s.candidate_offer_id = m.offer_id
                )
            """
      query_job = self.client.query(query)
      return [dict(row) for row in query_job]
    query = f"""
            SELECT *
            FROM `{self.status_table_ref}`
            QUALIFY ROW_NUMBER() OVER (
              PARTITION BY video_analysis_uuid, candidate_offer_id
              ORDER BY timestamp DESC
            ) = 1
            AND UPPER(status) = UPPER(@status)
        """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("status", "STRING", status)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    return [dict(row) for row in query_job]

  def get_candidate_status(self, analysis_id: str,
                           offer_id: str) -> Optional[Dict[str, Any]]:
    """Gets the latest candidate status for given video analysis ID and offer ID.

    Args:
      analysis_id: The unique identifier for the video analysis.
      offer_id: The unique identifier for the offer.

    Returns:
      A dictionary representing the latest status for a unique candidate offer
      within the specified analysis.
    """
    query = f"""
        SELECT *
        FROM `{self.status_table_ref}`
        WHERE video_analysis_uuid = @analysis_id
        AND candidate_offer_id = @offer_id
        ORDER BY timestamp DESC
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("analysis_id", "STRING", analysis_id),
            bigquery.ScalarQueryParameter("offer_id", "STRING", offer_id)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    results = list(query_job)
    if results:
      return dict(results[0])
    return None

  def get_candidate_statuses_by_analysis_id(
      self, analysis_id: str
  ) -> List[Dict[str, Any]]:
    """Gets the latest candidate statuses for a given video analysis ID.

    Args:
      analysis_id: The unique identifier for the video analysis.

    Returns:
      A list of dictionaries, each representing the latest status for a unique
      candidate offer within the specified analysis.
    """
    query = f"""
          SELECT *
          FROM `{self.status_table_ref}`
          WHERE video_analysis_uuid = @analysis_id
          QUALIFY ROW_NUMBER() OVER (
            PARTITION BY candidate_offer_id
            ORDER BY timestamp DESC
          ) = 1
      """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("analysis_id", "STRING", analysis_id)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    return [dict(row) for row in query_job]

  def get_video_analysis(self) -> List[Dict[str, Any]]:
    """Retrieves all video analysis records from the BigQuery table.

    Returns:
      A list of dictionaries, where each dictionary
      represents a video analysis record.
    """
    query = f"SELECT * FROM `{self.analysis_table_ref}`"
    query_job = self.client.query(query)
    return [dict(row) for row in query_job]

  def get_video_analysis_by_id(self,
                               analysis_id: str) -> Optional[Dict[str, Any]]:
    """Gets a video analysis record by its unique analysis ID.

    Args:
      analysis_id: The unique identifier for the video analysis.

    Returns:
      A dictionary representing the video analysis record if found, otherwise
      None.
    """
    query = (
        f"SELECT * FROM `{self.analysis_table_ref}` "
        "WHERE video_analysis_uuid = @analysis_id"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("analysis_id", "STRING", analysis_id)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    results = list(query_job)
    if results:
      return dict(results[0])
    return None

  def get_video_analysis_by_video_id(self,
                                     video_id: str) -> List[Dict[str, Any]]:
    """Gets video analysis records filtered by video ID.

    Args:
      video_id: The ID of the video to filter by.

    Returns:
      A list of dictionaries, each representing a video analysis record.
    """
    query = (
        f"SELECT * FROM `{self.analysis_table_ref}` "
        "WHERE video.video_id = @video_id"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("video_id", "STRING", video_id)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    return [dict(row) for row in query_job]

