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
        "video_id": candidate_status.get("video_id"),
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
            QUALIFY ROW_NUMBER() OVER (PARTITION BY video_id, candidate_offer_id ORDER BY timestamp DESC) = 1
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
                    t.video.video_id AS video_id,
                    m.offer_id AS candidate_offer_id,
                    'Unreviewed' AS status
                FROM `{self.analysis_table_ref}` t,
                UNNEST(identified_product) AS ip,
                UNNEST(ip.matched_product) AS m
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM `{self.status_table_ref}` s
                    WHERE s.video_id = t.video.video_id
                    AND s.candidate_offer_id = m.offer_id
                )
            """
      query_job = self.client.query(query)
      return [dict(row) for row in query_job]
    query = f"""
            SELECT *
            FROM `{self.status_table_ref}`
            QUALIFY ROW_NUMBER() OVER (PARTITION BY video_id, candidate_offer_id ORDER BY timestamp DESC) = 1
            AND UPPER(status) = UPPER(@status)
        """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("status", "STRING", status)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    return [dict(row) for row in query_job]

  def create_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new record in the BigQuery table.

    Args:
      record: A dictionary representing the record to be created.

    Returns:
      The created record.

    Raises:
      BigQueryError: If there is an error inserting the record.
    """
    errors = self.client.insert_rows_json(self.analysis_table_ref, [record])
    if errors:
      raise BigQueryError(f"Error creating record: {errors}")
    return record

  def get_records(self) -> List[Dict[str, Any]]:
    """Retrieves all records from the BigQuery table.

    Returns:
      A list of dictionaries, where each dictionary represents a record.
    """
    query = f"SELECT * FROM `{self.analysis_table_ref}`"
    query_job = self.client.query(query)
    return [dict(row) for row in query_job]

  def get_record_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single record from the BigQuery table by its ID.

    Args:
      record_id: The ID of the record to retrieve.

    Returns:
      A dictionary representing the record if found, otherwise None.
    """
    query = f"SELECT * FROM `{self.analysis_table_ref}` WHERE id = @id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("id", "STRING", record_id)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    results = list(query_job)
    if results:
      return dict(results[0])
    return None

  def get_records_by_video_id(self, video_id: str) -> List[Dict[str, Any]]:
    """Retrieves records from the BigQuery table filtered by video ID.

    Args:
      video_id: The ID of the video to filter by.

    Returns:
      A list of dictionaries, where each dictionary represents a record
      associated with the given video ID.
    """
    query = (
        f"SELECT * FROM `{self.analysis_table_ref}` "
        f"WHERE video.video_id = @video_id"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("video_id", "STRING", video_id)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    return [dict(row) for row in query_job]

  def update_record(self, record_id: str,
                    updated_record: Dict[str, Any]) -> Dict[str, Any]:
    """Updates an existing record in the BigQuery table.

    This method effectively replaces the existing record identified by
    `record_id` with the `updated_record`. It first deletes the old record and
    then inserts the new one, ensuring the `id` field of the new record
    matches `record_id`.

    Args:
      record_id: The ID of the record to update.
      updated_record: A dictionary representing the new data for the record.
                      It should not contain the 'id' field.

    Returns:
      The updated record, including the `record_id`.

    Raises:
      BigQueryError: If there is an error during the creation of the new record.
    """
    self.delete_record(record_id)
    updated_record["id"] = record_id
    self.create_record(updated_record)
    return updated_record

  def delete_record(self, record_id: str):
    """Deletes a record from the BigQuery table by its ID.

    Args:
      record_id: The ID of the record to delete.
    """
    query = f"DELETE FROM `{self.analysis_table_ref}` WHERE id = @id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("id", "STRING", record_id)
        ]
    )
    self.client.query(query, job_config=job_config).result()
