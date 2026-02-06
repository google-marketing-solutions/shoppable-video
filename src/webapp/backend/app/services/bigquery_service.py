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

import datetime
import pathlib
from typing import Any, Dict, Optional, Sequence
import uuid

from app.models import ad_group_insertion
from app.models import candidate
from app.models import video
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
      table_ids: Dict[str, str],
      client: Optional[bigquery.Client] = None,
  ):
    """Initializes the BigQueryService.

    Args:
      project_id: The Google Cloud project ID.
      dataset_id: The BigQuery dataset ID.
      table_ids: a dict containing canonical table refs to actual table names
      client: An optional BigQuery client instance. If not provided, a new one
        will be created.
    """
    self.project_id = project_id
    self.client = client or bigquery.Client(project=self.project_id)
    self.dataset_id = dataset_id
    self.dataset_ref = self.client.dataset(self.dataset_id)
    self.table_ids = table_ids

    self._validate_table_ids()
    self._load_queries()

  def _validate_table_ids(self):
    """Validates that table_ids contains all required keys.

    Raises:
      ValueError: If a required key is missing from table_ids.
    """
    required_table_ids = [
        "video_analysis_table_id",
        "matched_products_table_id",
        "matched_products_view_id",
        "candidate_status_table_id",
        "candidate_status_view_id",
        "google_ads_insertion_requests_table_id",
        "ad_group_insertion_status_table_id",
    ]
    if not all(key in self.table_ids for key in required_table_ids):
      missing_keys = [
          key for key in required_table_ids if key not in self.table_ids
      ]
      raise ValueError(
          f"Missing required table IDs in table_ids: {missing_keys}"
      )

  def _load_queries(self):
    """Loads and formats all SQL queries from the queries directory."""
    self.queries = {}
    queries_dir = pathlib.Path(__file__).parent / "queries"

    context = {
        "project_id": self.project_id,
        "dataset_id": self.dataset_id,
    }
    context.update(self.table_ids)

    for query_file in queries_dir.glob("*.sql"):
      with open(query_file, "r", encoding="utf-8") as f:
        query_name = query_file.stem
        self.queries[query_name] = f.read().format(**context)

  def get_video_analysis(self,
                         video_uuid: str) -> Optional[video.VideoAnalysis]:
    """Retrieves a video analysis records from BigQuery.

    Args:
      video_uuid: The unique identifier for the video analysis.

    Returns:
      A list of video analysis records.
    """

    query = self.queries["get_video_analysis"]
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("uuid", "STRING", video_uuid)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    results = list(query_job.result())
    if not results:
      return None

    return video.VideoAnalysis.model_validate(dict(results[0]))

  def get_video_analysis_summary(
      self,
      pagination: video.PaginationParams,
  ) -> video.PaginatedVideoAnalysisSummary:
    """Gets video analysis summary from BigQuery."""
    query = self.queries["get_video_analysis_summary"]
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("limit", "INT64", pagination.limit),
            bigquery.ScalarQueryParameter("offset", "INT64", pagination.offset),
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    results = list(query_job.result())

    items = []
    total_count = 0
    if results:
      total_count = results[0]["total_count"]
    for row in results:
      items.append(video.VideoAnalysisSummary.model_validate(dict(row)))

    return video.PaginatedVideoAnalysisSummary(
        items=items,
        total_count=total_count,
        limit=pagination.limit,
        offset=pagination.offset,
    )

  def get_ad_groups_for_video(self, video_id: str,
                              customer_id: str) -> Sequence[Dict[str, str]]:
    """Retrieves ad groups for a video from BigQuery.

    Args:
      video_id: The YouTube Video ID.
      customer_id: The Google Ads Customer ID.

    Returns:
      A list of dictionaries containing ad group details.
    """
    query_template = self.queries["get_ad_groups_for_video"]
    sanitized_cid = customer_id.replace("-", "")
    query = query_template.format(customer_id=sanitized_cid)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("video_id", "STRING", video_id)
        ]
    )

    query_job = self.client.query(query, job_config=job_config)
    results = list(query_job.result())
    return [dict(row) for row in results]

  def insert_submission_requests(
      self, submission_requests: Sequence[candidate.SubmissionMetadata]
  ) -> None:
    """Inserts submission requests into BigQuery.

    Args:
      submission_requests: A sequence of submission metadata to be inserted.

    Raises:
      BigQueryError: If there are errors during the BigQuery row insertion.
    """
    table_ref = self.dataset_ref.table(
        self.table_ids["google_ads_insertion_requests_table_id"]
    )
    rows_to_insert = []
    current_time = datetime.datetime.now().isoformat()

    for request in submission_requests:
      destinations = []
      if request.destinations:
        for dest in request.destinations:
          destinations.append({
              "ads_customer_id": dest.customer_id,
              "campaign_id": dest.campaign_id,
              "adgroup_id": dest.ad_group_id,
          })

      offer_ids = []
      if request.offer_ids:
        offer_ids = [
            oid.strip() for oid in request.offer_ids.split(",") if oid.strip()
        ]

      request_uuid = request.request_uuid or str(uuid.uuid4())

      row = {
          "request_uuid": request_uuid,
          "video_uuid": request.video_uuid,
          "offer_ids": offer_ids,
          "destinations": destinations,
          "submitting_user": request.submitting_user,
          "cpc": request.cpc,
          "timestamp": current_time,
      }
      rows_to_insert.append(row)

    errors = self.client.insert_rows_json(table_ref, rows_to_insert)

    if errors:
      raise BigQueryError(
          "Encountered errors while inserting submission requests: {}".
          format(errors)
      )

  def update_candidates(
      self, candidates: Sequence[candidate.Candidate]
  ) -> None:
    """Updates one or more candidate statuses in BigQuery.

    Args:
      candidates: A sequence of candidate statuses to be updated.

    Returns:
      The inserted candidate status dictionary.

    Raises:
      BigQueryError: If there are errors during the BigQuery row insertion.
    """

    candidate_status_table_ref = self.dataset_ref.table(
        self.table_ids["candidate_status_table_id"]
    )

    status_rows_to_insert = []
    for cand in candidates:
      row = cand.model_dump(exclude={"candidate_status"})
      status_dump = cand.candidate_status.model_dump(mode="json")
      row.update(status_dump)
      row["modified_timestamp"] = datetime.datetime.now().isoformat()
      status_rows_to_insert.append(row)

    errors = self.client.insert_rows_json(
        candidate_status_table_ref, status_rows_to_insert
    )
    if errors:
      raise BigQueryError(
          "Encountered errors while inserting rows: {}".format(errors)
      )

  def _row_to_dict(self, row) -> Dict[str, Any]:
    """Recursively converts a BigQuery Row (and nested Rows) to a dict."""
    if hasattr(row, "_asdict"):  # Handle namedtuples (if any)
      return {k: self._row_to_dict(v) for k, v in row._asdict().items()}
    if isinstance(row, (list, tuple)):
      return [self._row_to_dict(item) for item in row]
    if hasattr(row, "keys"):  # Handle Row objects and dicts
      return {k: self._row_to_dict(v) for k, v in row.items()}
    return row

  def get_ad_group_insertion_status(
      self, request_uuid: str
  ) -> Sequence[ad_group_insertion.AdGroupInsertionStatus]:
    """Retrieves ad group insertion status from BigQuery.

    Args:
      request_uuid: The unique identifier for the insertion request.

    Returns:
      A list of ad group insertion status records.
    """
    query = self.queries["get_ad_group_insertion_status"]
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "request_uuid", "STRING", request_uuid
            )
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    results = list(query_job.result())
    return [
        ad_group_insertion.AdGroupInsertionStatus.model_validate(
            self._row_to_dict(row)
        )
        for row in results
    ]

  def get_all_ad_group_insertion_statuses(
      self, pagination: video.PaginationParams
  ) -> ad_group_insertion.PaginatedAdGroupInsertionStatus:
    """Retrieves all ad group insertion statuses from BigQuery with pagination.

    Args:
      pagination: Pagination parameters.

    Returns:
      A paginated list of ad group insertion status records.
    """
    query = self.queries["get_all_ad_group_insertion_statuses"]
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("limit", "INT64", pagination.limit),
            bigquery.ScalarQueryParameter("offset", "INT64", pagination.offset),
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    results = list(query_job.result())

    items = []
    total_count = 0
    if results:
      total_count = results[0]["total_count"]
    for row in results:
      items.append(
          ad_group_insertion.AdGroupInsertionStatus.model_validate(
              self._row_to_dict(row)
          )
      )

    return ad_group_insertion.PaginatedAdGroupInsertionStatus(
        items=items,
        total_count=total_count,
        limit=pagination.limit,
        offset=pagination.offset,
    )

  def get_ad_group_insertion_statuses_for_video(
      self, video_uuid: str
  ) -> Sequence[ad_group_insertion.AdGroupInsertionStatus]:
    """Retrieves ad group insertion statuses for a specific video from BigQuery.

    Args:
      video_uuid: The unique identifier for the video analysis.

    Returns:
      A list of ad group insertion status records.
    """
    query = self.queries["get_ad_group_insertion_status_by_video"]
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("video_uuid", "STRING", video_uuid)
        ]
    )
    query_job = self.client.query(query, job_config=job_config)
    results = list(query_job.result())
    return [
        ad_group_insertion.AdGroupInsertionStatus.model_validate(
            self._row_to_dict(row)
        )
        for row in results
    ]
