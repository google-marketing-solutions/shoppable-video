# Copyright 2026 Google LLC
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

"""Logic for data synchronization between BigQuery and Firestore."""

import datetime
import logging
import re
from typing import Any, Dict, List, Tuple, Optional

from google.cloud import bigquery
from google.cloud import firestore

logger = logging.getLogger(__name__)

_KEYWORD_REGEX = re.compile(r"[\w-]+")


class DataSyncService:
  """Encapsulates testable execution logic for the automated sync process."""

  def __init__(
      self,
      bigquery_client: bigquery.Client,
      firestore_client: firestore.Client,
      project_id: str,
      dataset_id: str,
      merchant_id: str,
      batch_size_limit: int = 400,
  ):
    """Initializes the DataSyncService with explicit clients.

    Args:
        bigquery_client: Initialized Client for reading datasets.
        firestore_client: Initialized Client for writing target stores.
        project_id: Google Cloud Project identifier.
        dataset_id: The BigQuery Dataset targeting analytics outputs.
        merchant_id: Merchant Center account identifier string.
        batch_size_limit: Cutoff boundary for recursive batch flushes.
    """
    self.bigquery_client = bigquery_client
    self.firestore_client = firestore_client
    self.project_id = project_id
    self.dataset_id = dataset_id
    self.merchant_id = merchant_id
    self.batch_size_limit = batch_size_limit
    self.video_analysis_table = f"{project_id}.{dataset_id}.video_analysis"
    self.matched_products_table = f"{project_id}.{dataset_id}.matched_products"

  def get_last_sync_timestamp(self, component_key: str) -> datetime.datetime:
    """Fetches atomic component-specific high-water mark timestamp.

    Args:
        component_key: Unique key identifying component in _system collection.

    Returns:
        A datetime timestamp representing the last successful sync execution.
    """
    document_reference = self.firestore_client.collection("_system").document(
        f"{component_key}_sync_state"
    )
    document = document_reference.get()
    epoch_utc = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    if document.exists:
      return document.to_dict().get("last_sync_timestamp", epoch_utc)
    return epoch_utc

  def _fetch_videos_from_bigquery(self, last_sync: datetime.datetime) -> Any:
    """Executes parameterized BigQuery lookup extracting new analyses.

    Args:
        last_sync: Cutoff timestamp for extracting newer records.

    Returns:
        BigQuery RowIterator containing extracted video analysis records.
    """
    query = f"""
            SELECT
                uuid AS video_uuid,
                timestamp,
                source,
                video_id,
                gcs_uri,
                md5_hash,
                identified_products,
                metadata.title AS title,
                metadata.description AS description
            FROM `{self.video_analysis_table}`
            WHERE timestamp > @last_sync
            ORDER BY timestamp ASC
        """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("last_sync", "TIMESTAMP", last_sync)
        ]
    )
    return self.bigquery_client.query(query, job_config=job_config).result()

  def _flush_video_batch(
      self,
      batch: firestore.WriteBatch,
      safe_timestamp: Optional[datetime.datetime] = None,
  ):
    """Ensures safe high-water mark is atomically included in commit.

    Args:
        batch: The Firestore WriteBatch to commit.
        safe_timestamp: Optimal high-water mark value to record on success.
    """
    if safe_timestamp:
      state_ref = self.firestore_client.collection("_system").document(
          "videos_sync_state"
      )
      batch.set(state_ref, {"last_sync_timestamp": safe_timestamp}, merge=True)
    batch.commit()

  def _stage_identified_products(
      self,
      video_reference: firestore.DocumentReference,
      identified_products: List[Dict[str, Any]],
      batch: firestore.WriteBatch,
      write_count: int,
      safe_timestamp: Optional[datetime.datetime] = None,
  ) -> Tuple[firestore.WriteBatch, int]:
    """Batches internal identified products ensuring boundary safety.

    Args:
        video_reference: Firestore document target for appending identifiers.
        identified_products: List of dict records from nested bigquery rows.
        batch: The current active WriteBatch object.
        write_count: Number of mutation operations tracked inside the batch.
        safe_timestamp: Optional fallback timestamp for intermediate flushing.

    Returns:
        Tuple containing the active WriteBatch and current write_count integer.
    """
    current_batch = batch
    current_count = write_count

    for product in identified_products:
      product_uuid = product.get("uuid")
      if not product_uuid:
        continue

      product_reference = video_reference.collection(
          "identified_products"
      ).document(f"idp_{product_uuid}")

      product_data = {
          "title": product.get("title") or "",
          "description": product.get("description") or "",
          "relevance_reasoning": product.get("relevance_reasoning") or "",
          "video_timestamp": product.get("video_timestamp"),
      }
      current_batch.set(product_reference, product_data, merge=True)
      current_count += 1

      if current_count >= self.batch_size_limit:
        self._flush_video_batch(current_batch, safe_timestamp)
        current_batch = self.firestore_client.batch()
        current_count = 0

    return current_batch, current_count

  def _process_video_row(
      self,
      row: Any,
      batch: firestore.WriteBatch,
      write_count: int,
      safe_timestamp: Optional[datetime.datetime] = None,
  ) -> Tuple[firestore.WriteBatch, int]:
    """Processes single BigQuery record into mapped Firestore entries.

    Args:
        row: The loaded BigQuery row representation containing base fields.
        batch: The active firestore WriteBatch.
        write_count: Total count of writes performed on current batch.
        safe_timestamp: Intermediate recovery high-water mark for step-flushes.

    Returns:
        A tuple containing refreshed WriteBatch and current integer write count.
    """
    current_batch = batch
    current_count = write_count
    video_uuid = row.video_uuid

    video_reference = self.firestore_client.collection("videos").document(
        f"video_{video_uuid}"
    )
    video_data = {
        "video_id": row.video_id,
        "source": row.source,
        "gcs_uri": row.gcs_uri,
        "md5_hash": row.md5_hash,
        "timestamp": row.timestamp,
        "title": row.title or "",
        "description": row.description or "",
        "search_keywords": list(
            set(
                _KEYWORD_REGEX.findall(
                    " ".join([row.title or "", row.video_id or ""]).lower()
                )
            )
        ),
        "stats_identified_count": len(row.identified_products or []),
        "stats_matched_count": firestore.Increment(0),
        "stats_approved_count": firestore.Increment(0),
        "stats_disapproved_count": firestore.Increment(0),
        "stats_unreviewed_count": firestore.Increment(0),
    }
    current_batch.set(video_reference, video_data, merge=True)
    current_count += 1

    if current_count >= self.batch_size_limit:
      self._flush_video_batch(current_batch, safe_timestamp)
      current_batch = self.firestore_client.batch()
      current_count = 0

    return self._stage_identified_products(
        video_reference,
        row.identified_products or [],
        current_batch,
        current_count,
        safe_timestamp,
    )

  def sync_videos(self, last_sync: datetime.datetime) -> None:
    """Syncs analysis output to videos store.

    Args:
        last_sync: Initial timestamp used for determining update scope.
    """
    logger.info("Step 1: Syncing videos created after %s", last_sync)
    results = self._fetch_videos_from_bigquery(last_sync)

    batch = self.firestore_client.batch()
    write_count = 0
    safe_timestamp = last_sync
    prev_timestamp = None

    for row in results:
      if prev_timestamp and row.timestamp > prev_timestamp:
        safe_timestamp = prev_timestamp

      batch, write_count = self._process_video_row(
          row, batch, write_count, safe_timestamp
      )
      prev_timestamp = row.timestamp

    if write_count > 0 or prev_timestamp:
      # If loop completes completely, the absolute last timestamp is 100% secure
      self._flush_video_batch(batch, prev_timestamp or last_sync)
      logger.info("Final video batch commit finalized.")

  def _fetch_matched_products_from_bigquery(
      self, last_sync: datetime.datetime
  ) -> Any:
    """Aggregates joined match and parent video relationship records.

    Args:
        last_sync: Upper-bound timestamp from last successful run.

    Returns:
        BigQuery RowIterator with aggregated matching results.
    """

    query = f"""
            WITH new_matches AS (
                SELECT
                    m.timestamp,
                    m.uuid AS idp_uuid,
                    m.matched_product_offer_id AS offer_id,
                    m.distance,
                    v.video_uuid
                FROM `{self.matched_products_table}` AS m
                JOIN (
                    SELECT va.uuid AS video_uuid, ip.uuid AS idp_uuid
                    FROM `{self.video_analysis_table}` AS va,
                    UNNEST(identified_products) AS ip
                ) AS v ON v.idp_uuid = m.uuid
                WHERE m.timestamp > @last_sync
            ),
            video_totals AS (
                SELECT
                    v.video_uuid,
                    COUNT(m.uuid) AS total_count
                FROM `{self.matched_products_table}` AS m
                JOIN (
                    SELECT va.uuid AS video_uuid, ip.uuid AS idp_uuid
                    FROM `{self.video_analysis_table}` AS va,
                    UNNEST(identified_products) AS ip
                ) AS v ON v.idp_uuid = m.uuid
                WHERE v.video_uuid IN (SELECT DISTINCT video_uuid FROM new_matches)
                GROUP BY v.video_uuid
            )
            SELECT
                nm.timestamp,
                nm.idp_uuid,
                nm.offer_id,
                nm.distance,
                nm.video_uuid,
                vt.total_count
            FROM new_matches AS nm
            JOIN video_totals AS vt ON nm.video_uuid = vt.video_uuid
            ORDER BY nm.timestamp ASC
        """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("last_sync", "TIMESTAMP", last_sync)
        ]
    )
    return self.bigquery_client.query(query, job_config=job_config).result()

  def _flush_matched_increments(
      self,
      batch: firestore.WriteBatch,
      totals_map: Dict[str, int],
      latest_timestamp: Optional[datetime.datetime] = None,
  ):
    """Ensures absolute total tallies reside atomically inside payload.

    Args:
        batch: Firestore WriteBatch staged for commit.
        totals_map: Mapping video uuid keys to total count integer values.
        latest_timestamp: Watermark to increment system state clock.
    """
    for video_uuid, total_count in totals_map.items():
      video_reference = self.firestore_client.collection("videos").document(
          f"video_{video_uuid}"
      )
      batch.set(
          video_reference,
          {"stats_matched_count": total_count},
          merge=True,
      )

    if latest_timestamp:
      state_ref = self.firestore_client.collection("_system").document(
          "matches_sync_state"
      )
      batch.set(
          state_ref, {"last_sync_timestamp": latest_timestamp}, merge=True
      )

    batch.commit()

  def sync_matched_products(self, last_sync: datetime.datetime) -> None:
    """Pushes pipeline ML matches down nested stores.

    Args:
        last_sync: Clock timestamp defining the delta synchronization point.
    """
    logger.info("Step 2: Syncing pipeline matches after %s", last_sync)
    results = self._fetch_matched_products_from_bigquery(last_sync)

    batch = self.firestore_client.batch()
    write_count = 0
    safe_timestamp = last_sync
    prev_timestamp = None
    local_totals = {}

    for row in results:
      if prev_timestamp and row.timestamp > prev_timestamp:
        safe_timestamp = prev_timestamp

      match_reference = (
          self.firestore_client.collection("videos")
          .document(f"video_{row.video_uuid}")
          .collection("identified_products")
          .document(f"idp_{row.idp_uuid}")
          .collection("matched_products")
          .document(f"offer_{row.offer_id}")
      )

      batch.set(
          match_reference,
          {
              "video_uuid": row.video_uuid,
              "identified_product_uuid": row.idp_uuid,
              "offer_id": row.offer_id,
              "distance": row.distance,
          },
          merge=True,
      )
      write_count += 1
      local_totals[row.video_uuid] = row.total_count
      prev_timestamp = row.timestamp

      if (write_count + len(local_totals)) >= self.batch_size_limit:
        self._flush_matched_increments(batch, local_totals, safe_timestamp)
        batch = self.firestore_client.batch()
        write_count = 0
        local_totals = {}

    if write_count > 0 or prev_timestamp:
      self._flush_matched_increments(
          batch, local_totals, prev_timestamp or last_sync
      )

  def _fetch_active_offer_ids(self) -> List[str]:
    """Projects offer IDs combining BigQuery and Firestore inventory.

    This approach dynamically overcomes cold-start synchronization lockouts by
    driving the seed dataset from the BigQuery source of truth.

    Returns:
        A list of distinct active offer ID strings to be refreshed.
    """
    active_offer_ids: set[str] = set()

    # Phase 1: Extract distinct pipeline match identifiers efficiently.
    query = f"""
        SELECT DISTINCT
          matched_product_offer_id AS offer_id
        FROM `{self.matched_products_table}`
        WHERE matched_product_offer_id IS NOT NULL
    """
    query_results = self.bigquery_client.query(query).result()
    for row in query_results:
      if row.offer_id is not None:
        active_offer_ids.add(row.offer_id)

    # Phase 2: Projection utilizing select([]) pulls existing metadata.
    product_projection = self.firestore_client.collection("products").select([])
    for document in product_projection.stream():
      document_id = document.id
      if document_id.startswith("prod_"):
        offer_id = document_id.removeprefix("prod_")
        active_offer_ids.add(offer_id)

    return list(active_offer_ids)

  def _fetch_inventory_updates_from_bigquery(
      self, active_offer_ids: List[str]
  ) -> Any:
    """Reconciles external store state strictly against key subset.

    Args:
        active_offer_ids: String list limiters defining subset filter scope.

    Returns:
        BigQuery RowIterator over localized product mapping details.
    """
    if not active_offer_ids:
      return []

    table_path = (
        f"{self.project_id}.{self.dataset_id}."
        f"Products_{self.merchant_id}_Latest"
    )
    query = f"""
            SELECT
                p.offer_id,
                p.title,
                p.brand,
                p.image_link,
                p.availability,
                CAST(p.price.value AS FLOAT64) AS price
            FROM
                `{table_path}` AS p
            WHERE p.offer_id IN UNNEST(@active_offer_ids)
        """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "active_offer_ids", "STRING", active_offer_ids
            )
        ]
    )
    return self.bigquery_client.query(query, job_config=job_config).result()

  def sync_inventory(self):
    """Refreshing explicit inventory details by merging projection sets."""
    logger.info("Step 3: Refreshing localized product catalog metadata.")

    active_ids = self._fetch_active_offer_ids()
    if not active_ids:
      logger.info("Skipping phase: Zero active inventory monitored.")
      return

    logger.info("Syncing specific subset (%s items).", len(active_ids))
    results = self._fetch_inventory_updates_from_bigquery(active_ids)

    batch = self.firestore_client.batch()
    write_count = 0

    for row in results:
      product_reference = self.firestore_client.collection("products").document(
          f"prod_{row.offer_id}"
      )
      batch.set(
          product_reference,
          {
              "offer_id": row.offer_id,
              "title": row.title,
              "brand": row.brand,
              "image_link": row.image_link,
              "availability": row.availability,
              "price": row.price,
          },
          merge=True,
      )
      write_count += 1

      if write_count >= self.batch_size_limit:
        batch.commit()
        batch = self.firestore_client.batch()
        write_count = 0

    if write_count > 0:
      batch.commit()
      logger.info("Inventory refresh commit finalized.")
