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

"""Processor for Google Ads insertion deployments."""

import datetime
import logging
from typing import Any, Dict, List, Optional

import ads_service as ads_service_module
import google.api_core.exceptions
from google.cloud import firestore
import models
import utils

logger = logging.getLogger(__name__)


@firestore.transactional
def transactional_lease(
    transaction: firestore.Transaction,
    document_reference: firestore.DocumentReference,
    worker_id: str,
    lease_cutoff: datetime.datetime,
) -> bool:
  """Executes a transactional update to acquire an ACID lease on an insertion.

  Args:
      transaction: The active Firestore transaction object.
      document_reference: The reference to the Firestore document representing
          the pending insertion job.
      worker_id: The unique ID of the worker seeking the lease.
      lease_cutoff: The datetime limit used to expire stale processing leases.

  Returns:
      True if the lease was successfully acquired, False otherwise.
  """
  snapshot = document_reference.get(transaction=transaction)

  if not snapshot.exists:
    logger.warning(
        "Document %s disappeared during lease attempt.",
        document_reference.id,
    )
    return False

  data = snapshot.to_dict()
  status = data.get("status")
  leased_at = data.get("leased_at")

  is_pending = status == models.AdGroupInsertionStatus.PENDING
  is_stale_processing = (
      status == models.AdGroupInsertionStatus.PROCESSING
      and leased_at is not None
      and leased_at < lease_cutoff
  )

  if not (is_pending or is_stale_processing):
    logger.info(
        "Document %s is no longer available for leasing (status: %s).",
        document_reference.id,
        status,
    )
    return False

  transaction.update(
      document_reference,
      {
          "status": models.AdGroupInsertionStatus.PROCESSING,
          "worker_id": worker_id,
          "leased_at": firestore.SERVER_TIMESTAMP,
      },
  )

  return True


@firestore.transactional
def _atomic_finalize_video_state(
    transaction: firestore.Transaction,
    request_reference: firestore.DocumentReference,
    client: firestore.Client,
    req_updates: Dict[str, Any],
    is_job_success: bool,
):
  """Safely propagates final job state to parent video document atomically.

  Args:
      transaction: Active firestore transaction.
      request_reference: The handle to the request being finalized.
      client: The active firestore client.
      req_updates: Dictionary of fields to set on request.
      is_job_success: If final outcome counts as a success.
  """
  snapshot = request_reference.get(transaction=transaction)
  if not snapshot.exists:
    return

  data = snapshot.to_dict() or {}
  video_uuid = data.get("video_uuid")
  request_uuid = request_reference.id.removeprefix("req_")

  # Firestore requires reading documents before staging any writes.
  video_ref = None
  video_snapshot = None
  if video_uuid:
    video_ref = client.collection("videos").document(f"video_{video_uuid}")
    video_snapshot = video_ref.get(transaction=transaction)

  # Stage updates for request.
  transaction.update(request_reference, req_updates)

  # If video document exists, update it.
  if video_snapshot and video_snapshot.exists:
    v_data = video_snapshot.to_dict() or {}

    active_map = v_data.get("active_pushes") or {}
    has_successful_push = v_data.get("has_successful_push", False)

    # Count remaining active pushes, subtracting the one that is finishing.
    active_count = len(active_map)
    if request_uuid in active_map:
      active_count -= 1

    combined_success = has_successful_push or is_job_success

    # Run status priority logic.
    if active_count > 0:
      final_status = models.VideoPushStatus.IN_PROGRESS
    elif combined_success:
      final_status = models.VideoPushStatus.COMPLETE
    elif (v_data.get("stats_approved_count") or 0) > 0:
      final_status = models.VideoPushStatus.READY
    else:
      final_status = models.VideoPushStatus.NEEDS_REVIEW

    # Atomically clean up tracking map and set finalized status.
    transaction.update(
        video_ref,
        {
            f"active_pushes.{request_uuid}": firestore.DELETE_FIELD,
            "has_successful_push": combined_success,
            "status": final_status,
        },
    )


class AdsInsertionProcessor:
  """Orchestrates processing of Ads insertion jobs."""

  def __init__(
      self,
      firestore_client: firestore.Client,
      ads_service: ads_service_module.AdsService,
      worker_id: str,
  ):
    """Initializes the processor with necessary service dependencies.

    Args:
        firestore_client: Google Cloud Firestore client.
        ads_service: An instance of AdsService to interact with Google Ads API.
        worker_id: A unique identifier for this processing run.
    """
    self.firestore_client = firestore_client
    self.ads_service = ads_service
    self.worker_id = worker_id

  def run(self) -> None:
    """Executes polling and processing lifecycle, draining pending insertions.

    Raises:
        Exception: Bubbled exception only if core infrastructure/query fails.
    """
    logger.info("Executing with ID=%s", self.worker_id)

    while True:
      try:
        request_reference = self.get_pending_insertion()
      except google.api_core.exceptions.GoogleAPIError:
        logger.exception(
            "Critical infrastructure fault while polling candidate queue."
        )
        # Terminating current batch run due to critical infrastructure fault.
        logger.warning("Terminating processing loop due to error.")
        break

      if not request_reference:
        logger.info(
            "Queue drained: Zero remaining pending lockable insertion jobs"
            " found."
        )
        break

      logger.info(
          "Initiating operations for locked job %s", request_reference.id
      )

      try:
        deployments_snapshots = list(
            request_reference.collection("deployments").stream()
        )
        success_total = 0
        items_total = 0

        for snapshot in deployments_snapshots:
          result = self.process_deployment(snapshot)
          success_total += result.success_count
          items_total += result.total_count

        self._finalize_job_state(
            request_reference,
            success_count=success_total,
            total_count=items_total,
        )

      except google.api_core.exceptions.GoogleAPIError as e:
        logger.exception(
            "Infrastructure API error during job %s traversal:",
            request_reference.id,
        )
        self._finalize_job_state(
            request_reference,
            error_message=f"Infrastructure API Error: {str(e)}",
        )
        logger.warning(
            "Skipping block %s due to Firestore API error.",
            request_reference.id,
        )
      except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(
            "Unexpected runtime exception processing job %s:",
            request_reference.id,
        )
        self._finalize_job_state(request_reference, error_message=str(e))
        # Continue loop attempt to not halt others due to one corruption.
        logger.warning(
            "Skipping block %s following isolated failure.",
            request_reference.id,
        )

  def get_pending_insertion(
      self,
  ) -> Optional[firestore.DocumentReference]:
    """Finds a valid candidate request and secures a transactional lock.

    Returns:
        The document reference, or None if no candidate request found.
    """
    collection = self.firestore_client.collection("ads_insertions")

    while True:
      lease_cutoff = datetime.datetime.now(
          datetime.timezone.utc
      ) - datetime.timedelta(hours=2)
      found_candidates = False

      # Define available candidates sequentially prioritizing stale re-runs
      stale_query = (
          collection.where(
              filter=firestore.FieldFilter(
                  "status", "==", models.AdGroupInsertionStatus.PROCESSING
              )
          )
          .where(filter=firestore.FieldFilter("leased_at", "<", lease_cutoff))
          .order_by("leased_at")
          .limit(5)
      )

      pending_query = (
          collection.where(
              filter=firestore.FieldFilter(
                  "status", "==", models.AdGroupInsertionStatus.PENDING
              )
          )
          .order_by("timestamp")
          .limit(5)
      )

      # Configure stages sequentially prioritizing stale re-runs
      stages = [
          (stale_query, "stale", "stale insertion"),
          (pending_query, "pending", "insertion"),
      ]

      for query, label, msg_label in stages:
        for document in query.stream():
          found_candidates = True
          reference = document.reference
          transaction = self.firestore_client.transaction()
          try:
            if transactional_lease(
                transaction, reference, self.worker_id, lease_cutoff
            ):
              logger.info(
                  "Locked %s via transactional lease: %s",
                  msg_label,
                  reference.id,
              )
              return reference
          except google.api_core.exceptions.Aborted as e:
            logger.warning(
                "Contention on %s %s. Error: %s", label, reference.id, e
            )
            continue

      # If neither query yielded any documents, the queue is genuinely empty
      if not found_candidates:
        break

      logger.info("Lost candidate lock races. Fetching next available batch.")

    return None

  def process_deployment(
      self,
      snapshot: firestore.DocumentSnapshot,
  ) -> models.DeploymentResult:
    """Processes pre-fetched deployment data avoiding network retrieval loops.

    Args:
        snapshot: The Firestore document snapshot containing deployment data.

    Returns:
        A `models.DeploymentResult` dataclass containing the tally of
        successfully processed items (`success_count`) and the total number of
        items attempted (`total_count`).
    """
    if not snapshot.exists:
      return models.DeploymentResult(success_count=0, total_count=0)

    data = snapshot.to_dict()
    deployment_reference = snapshot.reference
    offers_map = data.get("offers") or {}
    offer_ids = list(offers_map.keys())
    total_count = len(offer_ids)

    if not self._validate_deployment(deployment_reference, data):
      fail_map = self._create_failure_map(
          offer_ids,
          "Corrupt deployment metadata (missing customer/campaign/offers)",
      )
      if fail_map:
        try:
          deployment_reference.update(fail_map)
        except google.api_core.exceptions.GoogleAPIError:
          logger.exception(
              "Failed to write validation failure state to Firestore."
          )
      return models.DeploymentResult(success_count=0, total_count=total_count)

    ad_group_id = data.get("ad_group_id")
    campaign_id = data.get("campaign_id")
    raw_customer_id = data.get("customer_id")
    customer_id = utils.normalize_customer_id(raw_customer_id) or None

    target_products = [str(oid) for oid in offer_ids]

    use_strategy = utils.parse_strategy(data.get("strategy"))

    logger.info(
        "Triggering Ads API mutation for adgroup %s (%s items, strategy=%s)",
        ad_group_id,
        len(target_products),
        use_strategy.name,
    )

    try:
      result = self.ads_service.add_offers_to_ad_group(
          ad_group_id=ad_group_id,
          campaign_id=campaign_id,
          customer_id=customer_id,
          target_products=target_products,
          strategy=use_strategy,
      )

      updates = self._map_results_to_updates(result, offer_ids)
      if updates:
        deployment_reference.update(updates)
        logger.info(
            "Mutate status updates flushed to %s", deployment_reference.id
        )

      success_count = sum(
          1
          for product_result in result.products
          if product_result.status != models.AdGroupInsertionStatus.FAILED
      )
      return models.DeploymentResult(
          success_count=success_count, total_count=total_count
      )

    except google.api_core.exceptions.GoogleAPIError:
      logger.exception(
          "Infrastructure API fault updating deployment: %s",
          deployment_reference.id,
      )
      # Re-raise infrastructure errors directly to bubble up to run loop
      # rather than initiating another doomed Firestore write.
      raise
    except Exception as e:  # pylint: disable=broad-exception-caught
      logger.exception(
          "Critical runtime exception executing deployment payload: %s",
          deployment_reference.id,
      )
      fail_map = self._create_failure_map(offer_ids, str(e))
      try:
        deployment_reference.update(fail_map)
      except google.api_core.exceptions.GoogleAPIError:
        logger.exception("Failed to write failure state to Firestore.")
      return models.DeploymentResult(success_count=0, total_count=total_count)

  def _finalize_job_state(
      self,
      request_reference: firestore.DocumentReference,
      success_count: int = 0,
      total_count: int = 0,
      error_message: Optional[str] = None,
  ) -> None:
    """Finalizes the job state in Firestore, marking it as COMPLETED or FAILED.

    Args:
        request_reference: The Firestore document reference for the job request.
        success_count: The number of items successfully processed.
        total_count: The total number of items attempted in this job.
        error_message: The error string explaining why the job failed, if any.
    """
    transaction = self.firestore_client.transaction()
    if error_message is not None:
      logger.error(
          "Terminal runtime fault on worker processing block %s: %s",
          request_reference.id,
          error_message,
      )
      try:
        req_updates = {
            "status": models.AdGroupInsertionStatus.FAILED,
            "error_message": f"Critical Worker Fail: {error_message}",
            "failed_at": firestore.SERVER_TIMESTAMP,
        }
        _atomic_finalize_video_state(
            transaction,
            request_reference,
            self.firestore_client,
            req_updates,
            False,
        )
      except google.api_core.exceptions.GoogleAPIError:
        logger.exception(
            "Failed recording terminal fault status to Firestore for %s",
            request_reference.id,
        )
    else:
      final_status = models.AdGroupInsertionStatus.SUCCESS

      if total_count == 0:
        # If no items were targeted, it's a SUCCESS for the request but does not
        # count as a successful push for the video status calculation.
        is_outcome_success = False
      else:
        is_outcome_success = success_count > 0
        if success_count == 0:
          final_status = models.AdGroupInsertionStatus.FAILED
        elif success_count < total_count:
          final_status = models.AdGroupInsertionStatus.PARTIAL_SUCCESS

      try:
        req_updates = {
            "status": final_status,
            "error_message": None,
            "completed_at": firestore.SERVER_TIMESTAMP,
        }
        _atomic_finalize_video_state(
            transaction,
            request_reference,
            self.firestore_client,
            req_updates,
            is_outcome_success,
        )
      except google.api_core.exceptions.GoogleAPIError:
        logger.exception(
            "Failed recording success finalization to Firestore for %s",
            request_reference.id,
        )
      logger.info(
          "Successfully finalized execution %s with status %s (%s/%s"
          " successful).",
          request_reference.id,
          final_status,
          success_count,
          total_count,
      )

  def _validate_deployment(
      self,
      deployment_reference: firestore.DocumentReference,
      data: Dict[str, Any],
  ) -> bool:
    """Validates deployment snapshot data.

    Args:
        deployment_reference: The Firestore reference for the deployment.
        data: The dictionary of deployment snapshot data.

    Returns:
        True if valid, False otherwise.
    """
    if not (
        data.get("ad_group_id")
        and data.get("campaign_id")
        and data.get("customer_id") is not None
    ):
      logger.error(
          "Corrupt metadata detected for deployment snapshot %s",
          deployment_reference.id,
      )
      return False

    if not data.get("offers"):
      logger.info(
          "Empty offers list mapped in deployment %s", deployment_reference.id
      )
      return False

    return True

  def _map_results_to_updates(
      self,
      result: models.AdsMutationResult,
      offer_ids: List[str],
  ) -> Dict[str, str]:
    """Maps the Ads API mutation results to Firestore update paths.

    Args:
        result: The `models.AdsMutationResult` object containing the mutation
            outcome, including individual product statuses and any global error.
        offer_ids: A list of offer IDs that were part of the mutation request.

    Returns:
        A dictionary where keys are Firestore field paths to the status/error
        fields of the offers, and values are the new status strings or error
        messages to persist in Firestore.
    """
    updates = {}
    if not result.products and result.error_message:
      return self._create_failure_map(offer_ids, result.error_message)

    for product_result in result.products:
      offer_id = product_result.offer_id
      status = product_result.status
      if status == models.AdGroupInsertionStatus.FAILED:
        updates.update(
            self._create_failure_map(
                [offer_id],
                result.error_message or "Mutate operation failed",
            )
        )
      else:
        updates[
            self.firestore_client.field_path("offers", offer_id, "status")
        ] = status

    return updates

  def _create_failure_map(
      self,
      offer_ids: List[str],
      error_message: str,
  ) -> Dict[str, Any]:
    """Creates a dictionary mapping offer IDs to failure statuses.

    Args:
        offer_ids: A list of offer IDs that failed to process.
        error_message: The explanation for the failure.

    Returns:
        A dictionary containing Firestore update paths for the failed offers.
    """
    fail_map = {}
    for offer_id in offer_ids:
      fail_map[
          self.firestore_client.field_path("offers", offer_id, "status")
      ] = models.AdGroupInsertionStatus.FAILED
      fail_map[
          self.firestore_client.field_path("offers", offer_id, "error_message")
      ] = f"Fatal: {error_message}"
    return fail_map
