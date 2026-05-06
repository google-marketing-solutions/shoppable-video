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

"""Service class for interacting with Firestore."""

import datetime
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid

from app.models import ad_group_insertion
from app.models import candidate
from app.models import product
from app.models import video
from google.cloud import firestore

logger = logging.getLogger(__name__)


class FirestoreBatchManager:
  """Smart wrapper for Firestore WriteBatch that manages auto-commits.

  Tracks internal write capacity and automatically flushes current transactions
  before Firestore limits are exceeded.

  Attributes:
    db: The client handle utilized for generating fresh batches.
    limit: Operational threshold triggering automated flush cycles.
    batch: Active transactional buffer object.
    count: Running total of staged pending operations.
  """

  def __init__(self, db: firestore.Client, limit: int = 240):
    """Initializes the manager with a safe rotation limit threshold.

    Args:
      db: The Firestore database client reference.
      limit: The upper cap on staged operation counts. Defaults to 240.
    """
    self.db = db
    self.limit = limit
    self.batch = db.batch()
    self.count = 0

  def reserve(self, required: int):
    """Commits current batch early if space falls below requirement threshold.

    Args:
      required: The required operations volume of the approaching block.
    """
    if self.count + required > self.limit:
      self.commit()

  def set(
      self,
      reference: firestore.DocumentReference,
      data: Dict[str, Any],
      merge=True,
  ):
    """Executes set write and automatically commits if limit reached.

    Args:
      reference: Targeted resource document reference handle.
      data: Raw field state updates data object.
      merge: Governs attribute patching vs full document rewrite.
    """
    self.batch.set(reference, data, merge=merge)
    self.count += 1
    if self.count >= self.limit:
      self.commit()

  def commit(self):
    """Flushes pending writes and resets internal state counters."""
    if self.count > 0:
      self.batch.commit()
      self.batch = self.db.batch()
      self.count = 0


class FirestoreService:
  """Service for backend operations against Firestore."""

  def __init__(
      self,
      project_id: str,
      database_id: str = "(default)",
      client: Optional[firestore.Client] = None,
  ):
    """Initializes the FirestoreService.

    Args:
      project_id: The Google Cloud project ID.
      database_id: The specific Firestore database ID to connect to.
      client: An optional pre-initialized Firestore client.
    """
    self.project_id = project_id
    self.db = client or firestore.Client(
        project=project_id, database=database_id
    )

  def get_video_analysis(
      self, video_uuid: str
  ) -> Optional[video.VideoAnalysis]:
    """Orchestrates fetching and correlation of a video's analysis graph.

    Args:
      video_uuid: The UUID of the video to analyze.

    Returns:
      The constructed VideoAnalysis object if the video exists, otherwise None.
    """
    video_reference = self.db.collection("videos").document(
        f"video_{video_uuid}"
    )
    res_video = self._get_video_base(video_reference)
    if not res_video:
      return None

    identified_products_map = self._fetch_identified_products(video_reference)
    raw_matches, inventory = self._fetch_matches_and_inventory(video_uuid)

    self._stitch_matches_to_products(
        raw_matches, inventory, identified_products_map
    )

    final_identified_products = []
    for item in identified_products_map.values():
      final_identified_products.append(product.IdentifiedProduct(**item))

    return video.VideoAnalysis(
        video=res_video, identified_products=final_identified_products
    )

  def get_video_analysis_summary(
      self, pagination: video.PaginationParams
  ) -> video.PaginatedVideoAnalysisSummary:
    """Retrieves a paginated list of video summaries.

    Args:
      pagination: The pagination parameters containing offset and limit.

    Returns:
      A paginated object containing a list of video analysis summaries and
      the total count of videos.
    """
    total_count_reference = self.db.collection("videos").count()
    total_count = total_count_reference.get()[0][0].value

    query = (
        self.db.collection("videos")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .offset(pagination.offset)
        .limit(pagination.limit)
        .stream()
    )

    items = []
    for snapshot in query:
      summary = self._map_video_to_summary(snapshot)
      if summary:
        items.append(summary)

    return video.PaginatedVideoAnalysisSummary(
        items=items,
        total_count=total_count,
        limit=pagination.limit,
        offset=pagination.offset,
    )

  def _get_video_base(
      self, video_reference: firestore.DocumentReference
  ) -> Optional[video.Video]:
    """Fetches a video document and hydrates it into a Video model.

    Args:
      video_reference: The Firestore document reference to the video.

    Returns:
      The initialized Video model if the document exists and has valid source
      or video_id data, otherwise None.
    """
    video_snapshot = video_reference.get()
    return self._map_snapshot_to_video(video_snapshot)

  def _fetch_identified_products(
      self, video_reference: firestore.DocumentReference
  ) -> Dict[str, Any]:
    """Retrieves all identified products for a video, indexed by product ID.

    Args:
      video_reference: The video's Firestore document reference.

    Returns:
      A dictionary mapping the product ID to its corresponding identified
      product data.
    """
    identified_products_stream = video_reference.collection(
        "identified_products"
    ).stream()
    identified_products_map = {}
    for snapshot in identified_products_stream:
      data = snapshot.to_dict()
      product_id = snapshot.id.removeprefix("idp_")
      identified_products_map[product_id] = {
          "uuid": product_id,
          "title": data.get("title") or "",
          "description": data.get("description") or "",
          "relevance_reasoning": data.get("relevance_reasoning") or "",
          "video_timestamp": data.get("video_timestamp") or 0,
          "matched_products": [],
      }
    return identified_products_map

  def _fetch_matches_and_inventory(
      self, video_uuid: str
  ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Retrieves matched products for a video and batch-fetches inventory.

    Uses collection_group to find items across nested sub-trees in one call,
    then bulk-fetches inventory details to minimize network requests.

    Args:
      video_uuid: The UUID of the video to fetch matches for.

    Returns:
      A tuple (raw_matches, inventory), where raw_matches is a list of raw match
      dictionaries, and inventory is a dictionary mapping offer IDs to product
      inventory data.
    """
    match_query = (
        self.db.collection_group("matched_products")
        .where(filter=firestore.FieldFilter("video_uuid", "==", video_uuid))
        .stream()
    )

    raw_matches = []
    offer_ids_to_fetch = set()
    for match_snapshot in match_query:
      match_data = match_snapshot.to_dict()
      raw_matches.append(match_data)
      if match_data.get("offer_id"):
        offer_ids_to_fetch.add(match_data["offer_id"])

    inventory = {}
    if offer_ids_to_fetch:
      references = [
          self.db.collection("products").document(f"prod_{offer_id}")
          for offer_id in offer_ids_to_fetch
      ]
      snapshots = self.db.get_all(references)
      for snapshot in snapshots:
        if snapshot.exists:
          inventory_data = snapshot.to_dict()
          inventory[inventory_data.get("offer_id", "")] = inventory_data

    return raw_matches, inventory

  def _stitch_matches_to_products(
      self,
      raw_matches: List[Dict[str, Any]],
      inventory: Dict[str, Any],
      identified_products_map: Dict[str, Any],
  ):
    """Performs an in-memory join of matched and identified products.

    Args:
      raw_matches: A list of raw matched product dictionaries.
      inventory: A dictionary mapping offer IDs to product inventory details.
      identified_products_map: A dictionary of identified products to which
        the matched models will be appended.
    """
    for match in raw_matches:
      offer_id = match.get("offer_id") or ""
      identified_product_uuid = match.get("identified_product_uuid")

      if identified_product_uuid not in identified_products_map:
        continue

      inventory_data = inventory.get(offer_id, {})
      candidate_status = candidate.CandidateStatus(
          status=match.get("candidate_status", "UNREVIEWED"),
          is_added_by_user=match.get("is_added_by_user", False),
          user=match.get("user", "system"),
      )

      stitched_match = product.MatchedProduct(
          matched_product_offer_id=offer_id,
          matched_product_title=inventory_data.get("title", "Unknown"),
          matched_product_brand=inventory_data.get("brand", ""),
          matched_product_image_link=inventory_data.get("image_link"),
          matched_product_availability=inventory_data.get("availability"),
          matched_timestamp=match.get("modified_timestamp")
          or datetime.datetime.now(datetime.timezone.utc),
          distance=match.get("distance") or 0.0,
          candidate_status=candidate_status,
      )

      identified_products_map[identified_product_uuid][
          "matched_products"
      ].append(stitched_match)

  def _map_video_to_summary(
      self, snapshot: firestore.DocumentSnapshot
  ) -> Optional[video.VideoAnalysisSummary]:
    """Maps a Firestore video snapshot to a video summary model."""
    res_video = self._map_snapshot_to_video(snapshot)
    if not res_video:
      return None

    data = snapshot.to_dict() or {}
    return video.VideoAnalysisSummary(
        video=res_video,
        identified_products_count=data.get("stats_identified_count", 0),
        matched_products_count=data.get("stats_matched_count", 0),
        approved_products_count=data.get("stats_approved_count", 0),
        disapproved_products_count=data.get("stats_disapproved_count", 0),
        unreviewed_products_count=data.get("stats_unreviewed_count", 0),
    )

  @staticmethod
  def _map_snapshot_to_video(
      snapshot: firestore.DocumentSnapshot,
  ) -> Optional[video.Video]:
    """Maps a Firestore DocumentSnapshot to a Video model.

    Args:
      snapshot: The raw Firestore document snapshot to map.

    Returns:
      An Optional loaded Video model ready for API output, or None if invalid.
    """
    if not snapshot.exists:
      return None
    data = snapshot.to_dict()
    if not data or (not data.get("source") and not data.get("video_id")):
      return None

    return video.Video(
        uuid=snapshot.id.removeprefix("video_"),
        source=data.get("source") or "youtube",
        video_id=data.get("video_id"),
        gcs_uri=data.get("gcs_uri"),
        md5_hash=data.get("md5_hash"),
        metadata=video.VideoMetadata(
            title=data.get("title"),
            description=data.get("description"),
        ),
    )

  def update_candidates(
      self, candidates: Sequence[candidate.Candidate]
  ) -> None:
    """Updates multiple candidate statuses, respecting operation limits.

    Args:
      candidates: A sequence of candidate objects to be updated in Firestore.
    """
    if not candidates:
      return

    reference_tuples = []
    for individual_candidate in candidates:
      reference = (
          self.db.collection("videos")
          .document(f"video_{individual_candidate.video_analysis_uuid}")
          .collection("identified_products")
          .document(f"idp_{individual_candidate.identified_product_uuid}")
          .collection("matched_products")
          .document(f"offer_{individual_candidate.candidate_offer_id}")
      )
      reference_tuples.append((reference, individual_candidate))

    snap_lookup = self._fetch_existing_snapshots(reference_tuples)

    batch_mgr = FirestoreBatchManager(self.db)
    local_increments = {}

    for reference, current_candidate in reference_tuples:
      # Track update (1), user product (1), and stats side-inc (1)
      ops_needed = (
          2 if current_candidate.candidate_status.is_added_by_user else 1
      )

      # Combine local_increments length into the cap check logic
      if (
          batch_mgr.count + len(local_increments) + ops_needed + 1
          > batch_mgr.limit
      ):
        self._apply_increments(batch_mgr.batch, local_increments)
        batch_mgr.commit()
        local_increments = {}

      existing_data = snap_lookup.get(reference.path, {})
      delta = self._stage_candidate_update(
          batch_mgr.batch, reference, current_candidate, existing_data
      )
      batch_mgr.count += 1

      if current_candidate.candidate_status.is_added_by_user:
        prod_ref = self.db.collection("products").document(
            f"prod_{current_candidate.candidate_offer_id}"
        )
        batch_mgr.batch.set(
            prod_ref,
            {
                "offer_id": current_candidate.candidate_offer_id,
                "availability": "in stock",
                "title": f"User Product {current_candidate.candidate_offer_id}",
            },
            merge=True,
        )
        batch_mgr.count += 1

      local_increments[current_candidate.video_analysis_uuid] = (
          local_increments.get(current_candidate.video_analysis_uuid, 0) + delta
      )

    # Finalize final subset logic
    self._apply_increments(batch_mgr.batch, local_increments)
    batch_mgr.commit()

  def _fetch_existing_snapshots(
      self, reference_tuples: List[Tuple[firestore.DocumentReference, Any]]
  ) -> Dict[str, Dict[str, Any]]:
    """Fetches document snapshots in a single batch get request.

    Args:
      reference_tuples: List of tuples where the first element is a
        Firestore document reference.

    Returns:
      A dictionary mapping the document reference path to its data dictionary
      for all existing snapshots.
    """
    existing_snapshots = self.db.get_all([pair[0] for pair in reference_tuples])
    return {
        snapshot.reference.path: snapshot.to_dict()
        for snapshot in existing_snapshots
        if snapshot.exists
    }

  def _stage_candidate_update(
      self,
      batch: firestore.WriteBatch,
      reference: firestore.DocumentReference,
      candidate_item: candidate.Candidate,
      existing_data: Dict[str, Any],
  ) -> int:
    """Appends candidate updates to the write batch and tracks the delta.

    Args:
      batch: The Firestore write batch object.
      reference: The Firestore document reference for the candidate update.
      candidate_item: The candidate details to be written.
      existing_data: A dictionary of the existing data for the candidate.

    Returns:
      The delta change in approved status count (-1, 0, or 1).
    """
    old_status = existing_data.get("candidate_status", "UNREVIEWED")
    new_status = candidate_item.candidate_status.status

    approved_delta = 0
    if old_status != "APPROVED" and new_status == "APPROVED":
      approved_delta = 1
    elif old_status == "APPROVED" and new_status != "APPROVED":
      approved_delta = -1

    batch.set(
        reference,
        {
            "candidate_status": new_status,
            "user": candidate_item.candidate_status.user,
            "is_added_by_user": (
                candidate_item.candidate_status.is_added_by_user
            ),
            "modified_timestamp": firestore.SERVER_TIMESTAMP,
            "video_uuid": candidate_item.video_analysis_uuid,
            "identified_product_uuid": candidate_item.identified_product_uuid,
            "offer_id": candidate_item.candidate_offer_id,
        },
        merge=True,
    )
    return approved_delta

  def _apply_increments(
      self, batch: firestore.WriteBatch, increments: Dict[str, int]
  ):
    """Enqueues stats increment operations onto active batch without committing.

    Args:
      batch: The Firestore write batch object.
      increments: A dictionary mapping video UUIDs to increment values.
    """
    for video_uuid, increment in increments.items():
      if increment == 0:
        continue
      video_reference = self.db.collection("videos").document(
          f"video_{video_uuid}"
      )
      batch.set(
          video_reference,
          {"stats_approved_count": firestore.Increment(increment)},
          merge=True,
      )

  def insert_submission_requests(
      self, submission_requests: Sequence[candidate.SubmissionMetadata]
  ) -> None:
    """Creates ads insertion requests and writes deployment children.

    Args:
      submission_requests: A sequence of submission metadata objects defining
        the requests to be inserted.
    """
    batch_mgr = FirestoreBatchManager(self.db)

    for submission_request in submission_requests:
      request_uuid = submission_request.request_uuid or str(uuid.uuid4())
      offer_ids = []
      if submission_request.offer_ids:
        offer_ids = [
            offer_id.strip()
            for offer_id in submission_request.offer_ids.split(",")
        ]

      destinations = submission_request.destinations or []

      # Reserve to guarantee master and children share one atomic batch
      batch_mgr.reserve(1 + len(destinations))

      req_reference = self.db.collection("ads_insertions").document(
          f"req_{request_uuid}"
      )
      batch_mgr.set(
          req_reference,
          {
              "video_uuid": submission_request.video_uuid,
              "submitting_user": submission_request.submitting_user,
              "status": "PENDING",
              "offer_ids": offer_ids,
              "timestamp": firestore.SERVER_TIMESTAMP,
          },
      )

      cpc_micros = (
          int(submission_request.cpc * 1e6) if submission_request.cpc else None
      )

      self._stage_deployments(
          batch_mgr,
          req_reference,
          submission_request.video_uuid,
          offer_ids,
          cpc_micros,
          submission_request.destinations or [],
      )

    batch_mgr.commit()

  def get_ad_group_insertion_status(
      self, request_uuid: str
  ) -> Sequence[ad_group_insertion.AdGroupInsertionStatus]:
    """Fetches the detailed status for an insertion request.

    Args:
      request_uuid: The UUID of the specific submission request.

    Returns:
      A sequence containing a single AdGroupInsertionStatus if found, otherwise
      an empty sequence.
    """
    submission_request_reference = self.db.collection(
        "ads_insertions"
    ).document(f"req_{request_uuid}")
    snapshot = submission_request_reference.get()
    if not snapshot.exists:
      return []

    document_data = snapshot.to_dict()
    deployment_snapshots = submission_request_reference.collection(
        "deployments"
    ).get()

    entities = self._map_deployments_to_entities(deployment_snapshots)

    return [
        ad_group_insertion.AdGroupInsertionStatus(
            request_uuid=request_uuid,
            video_analysis_uuid=document_data.get("video_uuid", ""),
            status=document_data.get("status"),
            ads_entities=entities,
            timestamp=document_data.get("timestamp"),
        )
    ]

  def get_ad_group_insertion_statuses_for_video(
      self, video_uuid: str
  ) -> Sequence[ad_group_insertion.AdGroupInsertionStatus]:
    """Retrieves video insertion statuses and joins request metadata.

    Args:
      video_uuid: The UUID of the video to fetch insertion statuses for.

    Returns:
      A sequence of constructed AdGroupInsertionStatus models.
    """
    deployments_stream = (
        self.db.collection_group("deployments")
        .where(filter=firestore.FieldFilter("video_uuid", "==", video_uuid))
        .stream()
    )

    results_by_request = {}
    for snapshot in deployments_stream:
      deployment_data = snapshot.to_dict()
      request_uuid = snapshot.reference.parent.parent.id.removeprefix("req_")

      if request_uuid not in results_by_request:
        results_by_request[request_uuid] = {
            "request_uuid": request_uuid,
            "video_analysis_uuid": video_uuid,
            "status": "PROCESSING",
            "ads_entities": [],
            "timestamp": None,
        }

      results_by_request[request_uuid]["ads_entities"].append(
          self._map_deployment_to_entity(deployment_data)
      )

    self._backfill_parent_metadata(results_by_request)

    final_results = []
    for final_data in results_by_request.values():
      if not final_data["timestamp"]:
        final_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
      final_results.append(
          ad_group_insertion.AdGroupInsertionStatus(**final_data)
      )

    return final_results

  def get_all_ad_group_insertion_statuses(
      self, pagination: video.PaginationParams
  ) -> ad_group_insertion.PaginatedAdGroupInsertionStatus:
    """Retrieves paginated insertion statuses via bulk deployment fetch.

    Args:
      pagination: The pagination parameters containing offset and limit.

    Returns:
      A paginated object of aggregated ad group insertion statuses.
    """
    total_count_reference = self.db.collection("ads_insertions").count()
    total_count = total_count_reference.get()[0][0].value

    request_stream = (
        self.db.collection("ads_insertions")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .offset(pagination.offset)
        .limit(pagination.limit)
        .stream()
    )

    parent_lookup = {}
    request_ids = []
    for snapshot in request_stream:
      document_data = snapshot.to_dict()
      request_id = snapshot.id.removeprefix("req_")
      request_ids.append(request_id)
      parent_lookup[request_id] = {
          "request_uuid": request_id,
          "video_analysis_uuid": document_data.get("video_uuid", ""),
          "status": document_data.get("status"),
          "timestamp": document_data.get("timestamp"),
          "ads_entities": [],
      }

    if request_ids:
      visible_video_uuids = list(
          set([
              p["video_analysis_uuid"]
              for p in parent_lookup.values()
              if p["video_analysis_uuid"]
          ])
      )
      if visible_video_uuids:
        self._resolve_all_deployments(parent_lookup, visible_video_uuids)

    items = [
        ad_group_insertion.AdGroupInsertionStatus(**parent_lookup[rid])
        for rid in request_ids
    ]
    return ad_group_insertion.PaginatedAdGroupInsertionStatus(
        items=items,
        total_count=total_count,
        limit=pagination.limit,
        offset=pagination.offset,
    )

  def _stage_deployments(
      self,
      batch_mgr: "FirestoreBatchManager",
      req_reference: firestore.DocumentReference,
      video_uuid: str,
      offer_ids: List[str],
      cpc_micros: Optional[int],
      destinations: List[candidate.Destination],
  ) -> None:
    """Stages deployments into the batch, auto-rotating upon limit breach.

    Args:
      batch_mgr: Smart manager governing auto-rotating commit rotation.
      req_reference: The Firestore document reference to the insertion request.
      video_uuid: The UUID of the video related to the deployments.
      offer_ids: A list of offer IDs associated with the deployments.
      cpc_micros: The cost-per-click bid in micros, if available.
      destinations: A list of destination configurations.
    """
    for destination in destinations:
      deploy_ref = req_reference.collection("deployments").document(
          f"deploy_{destination.ad_group_id}"
      )
      offers_map = {}
      for iterate_offer_id in offer_ids:
        offers_map[iterate_offer_id] = {
            "status": "PENDING",
            "cpc_bid_micros": cpc_micros,
            "error_message": None,
        }

      batch_mgr.set(
          deploy_ref,
          {
              "video_uuid": video_uuid,
              "customer_id": destination.customer_id,
              "campaign_id": destination.campaign_id,
              "ad_group_id": destination.ad_group_id,
              "offers": offers_map,
          },
      )

  def _resolve_all_deployments(
      self,
      parent_lookup: Dict[str, Dict[str, Any]],
      visible_video_uuids: List[str],
  ):
    """Queries deployments across video IDs using chunked 'in' operators.

    Mandatory chunking complies with Firestore's 30-item 'in' limit.

    Args:
      parent_lookup: A mapping of insertion request IDs to their entity states,
        mutated in-place to append entities.
      visible_video_uuids: A list of video UUIDs to limit the deployments
        query.
    """
    # Critical Fix: Firestore limits 'in' queries to a maximum of 30 entries
    chunk_size = 30
    for i in range(0, len(visible_video_uuids), chunk_size):
      uuid_chunk = visible_video_uuids[i : i + chunk_size]

      deployments_stream = (
          self.db.collection_group("deployments")
          .where(filter=firestore.FieldFilter("video_uuid", "in", uuid_chunk))
          .stream()
      )

      for snapshot in deployments_stream:
        deployment_data = snapshot.to_dict()
        parent_request_id = snapshot.reference.parent.parent.id.removeprefix(
            "req_"
        )

        if parent_request_id in parent_lookup:
          parent_lookup[parent_request_id]["ads_entities"].append(
              self._map_deployment_to_entity(deployment_data)
          )

  def _backfill_parent_metadata(
      self, results_by_request: Dict[str, Dict[str, Any]]
  ):
    """Batch-loads metadata from insertion requests for associated deployments.

    Args:
      results_by_request: A dictionary mapping request UUIDs to their
        corresponding results dictionaries, which are mutated in-place.
    """
    if not results_by_request:
      return

    parent_references = [
        self.db.collection("ads_insertions").document(f"req_{request_id}")
        for request_id in results_by_request.keys()
    ]
    parent_snapshots = self.db.get_all(parent_references)
    for parent_snapshot in parent_snapshots:
      if parent_snapshot.exists:
        parent_data = parent_snapshot.to_dict()
        request_id = parent_snapshot.id.removeprefix("req_")
        results_by_request[request_id]["status"] = parent_data.get("status")
        results_by_request[request_id]["timestamp"] = parent_data.get(
            "timestamp"
        )

  def _map_deployments_to_entities(
      self, deployment_snapshots: List[firestore.DocumentSnapshot]
  ) -> List[Dict[str, Any]]:
    """Converts deployment snapshots into Ads Entity dictionaries.

    Args:
      deployment_snapshots: A list of Firestore document snapshots
        representing deployments.

    Returns:
      A list of dictionaries containing structured Ads entities details.
    """
    entities = []
    for snapshot in deployment_snapshots:
      data = snapshot.to_dict()
      entities.append(self._map_deployment_to_entity(data))
    return entities

  @staticmethod
  def _map_deployment_to_entity(
      deployment_data: Dict[str, Any],
  ) -> Dict[str, Any]:
    """Converts raw deployment data into an Ads Entity dictionary.

    Args:
      deployment_data: Raw data payload fetched from Firestore.

    Returns:
      A dictionary representation of the Ads Entity with default values.
    """
    return {
        "customer_id": deployment_data.get("customer_id") or 0,
        "campaign_id": deployment_data.get("campaign_id") or 0,
        "ad_group_id": deployment_data.get("ad_group_id") or 0,
        "products": [
            {
                "offer_id": offer_id,
                "status": offer_info.get("status", "PENDING"),
            }
            for offer_id, offer_info in (
                deployment_data.get("offers") or {}
            ).items()
        ],
        "error_message": deployment_data.get("error_message"),
    }
