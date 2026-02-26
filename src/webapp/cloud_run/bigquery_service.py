"""Service for interacting with BigQuery.

This module provides the BigQueryService class, which handles interactions with
BigQuery to fetch pending ad group updates.
"""

import os
from typing import Any, List

from google.cloud import bigquery
from pydantic import BaseModel


class AdGroupUpdate(BaseModel):
  """Represents an update for an Ad Group.

  Attributes:
    ad_group_id: The ID of the ad group.
    campaign_id: The ID of the campaign.
    cpc_bid_micros: The CPC bid in micros.
    customer_id: The Google Ads customer ID.
    offer_ids: A list of offer IDs to add to the ad group.
    request_uuid: The UUID of the request.
    video_analysis_uuid: The UUID of the video analysis.
  """

  ad_group_id: int
  campaign_id: int
  cpc_bid_micros: int | None
  customer_id: int
  offer_ids: List[str]
  request_uuid: str
  video_analysis_uuid: str


class ProductResult(BaseModel):
  """Represents the result of a product insertion."""

  offer_id: str
  status: str


class AdsEntity(BaseModel):
  """Represents a Google Ads entity (Campaign/Ad Group) update status."""

  customer_id: int
  campaign_id: int
  ad_group_id: int
  products: List[ProductResult]
  cpc_bid_micros: int | None = None
  error_message: str | None


class InsertionStatusRow(BaseModel):
  """Represents a row to be inserted into the status table."""

  request_uuid: str
  status: str
  ads_entities: List[AdsEntity]
  timestamp: str


class BigQueryService:
  """Handles interactions with BigQuery."""

  def __init__(self):
    """Initializes the BigQueryService with a BigQuery client.

    Raises:
      ValueError: If the GOOGLE_ADS_INSERTION_REQUESTS_TABLE_ID environment
        variable is not set.
    """
    self.client = bigquery.Client()
    self.table_id = os.getenv("GOOGLE_ADS_INSERTION_REQUESTS_TABLE_ID")
    if not self.table_id:
      raise ValueError(
          "GOOGLE_ADS_INSERTION_REQUESTS_TABLE_ID environment variable is not "
          "set"
      )

    self.project_id = os.getenv("PROJECT_ID")
    self.dataset_id = os.getenv("DATASET_ID")

    self.table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"

    self.status_table_id = os.getenv("AD_GROUP_INSERTION_STATUS_TABLE_ID")
    if not self.status_table_id:
      raise ValueError(
          "AD_GROUP_INSERTION_STATUS_TABLE_ID environment variable is not set"
      )
    self.status_table_ref = (
        f"{self.project_id}.{self.dataset_id}.{self.status_table_id}"
    )

  def fetch_pending_updates(
      self, request_uuid: str | None = None
  ) -> List[AdGroupUpdate]:
    """Fetches pending ad group updates from BigQuery.

    Args:
      request_uuid: Optional UUID to filter the updates by.

    Returns:
      A list of AdGroupUpdate objects containing ad_group_id, offer_ids,
      video_analysis_uuid, and customer_id.
    """
    query = f"""
            SELECT request_uuid, video_uuid, offer_ids, destinations,
                   submitting_user, timestamp, cpc
            FROM `{self.table_ref}`
        """

    query_params = []
    if request_uuid:
      query += " WHERE request_uuid = @request_uuid"
      query_params.append(
          bigquery.ScalarQueryParameter("request_uuid", "STRING", request_uuid)
      )

    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    query_job = self.client.query(query, job_config=job_config)
    results = []

    for row in query_job:
      video_uuid = row["video_uuid"]
      raw_offer_ids = row["offer_ids"]
      offer_ids = (
          raw_offer_ids
          if isinstance(raw_offer_ids, list)
          else (str(raw_offer_ids).split(",") if raw_offer_ids else [])
      )
      cpc_val = row.get("cpc")
      cpc_bid_micros = None
      if cpc_val is not None:
        try:
          cpc_bid_micros = int(float(cpc_val) * 1_000_000)
        except (ValueError, TypeError) as e:
          request_uuid = row.get("request_uuid")
          raise ValueError(
              f"Invalid 'cpc' value '{cpc_val}' for request {request_uuid}: {e}"
          ) from e

      destinations = row["destinations"]
      for dest in destinations:
        results.append(
            AdGroupUpdate(
                ad_group_id=dest["adgroup_id"],
                campaign_id=int(dest["campaign_id"]),
                offer_ids=offer_ids,
                video_analysis_uuid=video_uuid,
                customer_id=int(dest["ads_customer_id"]),
                cpc_bid_micros=cpc_bid_micros,
                request_uuid=row.get("request_uuid", ""),
            )
        )

    return results

  def record_insertion_status(
      self, rows: List[InsertionStatusRow] | List[dict[str, Any]]
  ):
    """Inserts ad group insertion status rows into BigQuery.

    Args:
      rows: A list of InsertionStatusRow objects or dictionaries representing
        the rows to insert.

    Raises:
      RuntimeError: If there is an error inserting rows into BigQuery.
    """
    if not rows:
      return

    rows_to_insert = [
        row.model_dump() if isinstance(row, BaseModel) else row for row in rows
    ]

    errors = self.client.insert_rows_json(self.status_table_ref, rows_to_insert)
    if errors:
      raise RuntimeError(f"Failed to insert rows into BigQuery: {errors}")
