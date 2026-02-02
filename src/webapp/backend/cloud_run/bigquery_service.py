"""Service for interacting with BigQuery.

This module provides the BigQueryService class, which handles interactions with
BigQuery to fetch pending ad group updates.
"""

import os
from typing import List

from google.cloud import bigquery
from pydantic import BaseModel


class AdGroupUpdate(BaseModel):
  """Represents an update for an Ad Group.

  Attributes:
    ad_group_id: The ID of the ad group.
    offer_ids: A list of offer IDs to add to the ad group.
    video_analysis_uuid: The UUID of the video analysis.
    customer_id: The Google Ads customer ID.
    cpc_bid_micros: The CPC bid in micros.
  """
  ad_group_id: int
  offer_ids: List[str]
  video_analysis_uuid: str
  customer_id: str
  cpc_bid_micros: int


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
      offer_ids = raw_offer_ids if isinstance(raw_offer_ids, list) else (
          str(raw_offer_ids).split(",") if raw_offer_ids else []
      )
      cpc_val = row.get("cpc")
      if cpc_val is None:
        raise ValueError(f"Missing 'cpc' for request {row.get('request_uuid')}")

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
                ad_group_id=dest["adgroup_id"], offer_ids=offer_ids,
                video_analysis_uuid=video_uuid,
                customer_id=str(dest["ads_customer_id"]),
                cpc_bid_micros=cpc_bid_micros
            )
        )

    return results
