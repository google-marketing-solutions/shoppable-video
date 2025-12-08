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
      self,
      project_id: str,
      dataset_id: str,
      table_id: str,
      client: Optional[bigquery.Client] = None
  ):
    """Initializes the BigQueryService.

    Args:
      project_id: The Google Cloud project ID.
      dataset_id: The BigQuery dataset ID.
      table_id: The BigQuery table ID.
      client: An optional BigQuery client instance. If not provided, a new one
        will be created.
    """
    self.project_id = project_id
    self.client = client or bigquery.Client(project=self.project_id)
    self.dataset_id = dataset_id
    self.table_id = table_id
    self.table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
    self.client = client or bigquery.Client(project=self.project_id)
    self.dataset_id = dataset_id
    self.table_id = table_id
    self.table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"

  def create_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new record in the BigQuery table.

    Args:
      record: A dictionary representing the record to be created.

    Returns:
      The created record.

    Raises:
      BigQueryError: If there is an error inserting the record.
    """
    errors = self.client.insert_rows_json(self.table_ref, [record])
    if errors:
      raise BigQueryError(f"Error creating record: {errors}")
    return record

  def get_records(self) -> List[Dict[str, Any]]:
    """Retrieves all records from the BigQuery table.

    Returns:
      A list of dictionaries, where each dictionary represents a record.
    """
    query = f"SELECT * FROM `{self.table_ref}`"
    query_job = self.client.query(query)
    return [dict(row) for row in query_job]

  def get_record_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single record from the BigQuery table by its ID.

    Args:
      record_id: The ID of the record to retrieve.

    Returns:
      A dictionary representing the record if found, otherwise None.
    """
    query = f"SELECT * FROM `{self.table_ref}` WHERE id = @id"
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
    query = f"SELECT * FROM `{self.table_ref}` WHERE video.video_id = @video_id"
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
    query = f"DELETE FROM `{self.table_ref}` WHERE id = @id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("id", "STRING", record_id)
        ]
    )
    self.client.query(query, job_config=job_config).result()
