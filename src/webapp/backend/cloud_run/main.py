"""Main entry point for the Cloud Run Job.

This module orchestrates the fetching of pending ad group updates from BigQuery
and applies them to Google Ads using the AdsService.
"""

import argparse
import datetime
import logging

from ads_service import AdsService
from bigquery_service import BigQueryService
import constants
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _calculate_status_for_products(products):
  """Calculates the overall status based on a list of product results.

  Args:
    products: List of dicts, each containing a 'status' key.

  Returns:
    One of STATUS_SUCCESS, STATUS_PARTIAL_SUCCESS, STATUS_FAILED.
  """
  if not products:
    return constants.STATUS_SUCCESS

  has_success = False
  has_failure = False

  for p in products:
    if p["status"] == constants.STATUS_FAILED:
      has_failure = True
    else:
      has_success = True

  if has_success and has_failure:
    return constants.STATUS_PARTIAL_SUCCESS
  if has_failure:
    return constants.STATUS_FAILED
  return constants.STATUS_SUCCESS


def _update_request_status(results_by_request, update, result):
  """Updates the processing status for a single ad group update."""
  if update.request_uuid not in results_by_request:
    results_by_request[update.request_uuid] = {
        "request_uuid": update.request_uuid,
        "status": constants.STATUS_SUCCESS,
        "ads_entities": [],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

  request_result = results_by_request[update.request_uuid]

  entity_record = {
      "customer_id": result["customer_id"],
      "campaign_id": result["campaign_id"],
      "ad_group_id": result["ad_group_id"],
      "products": result["products"],
      "error_message": result["error_message"],
  }

  if entity_record["campaign_id"] is None:
    logger.error(
        "Could not determine campaign_id for ad_group %s", update.ad_group_id
    )
    entity_record["campaign_id"] = -1

  request_result["ads_entities"].append(entity_record)

  all_products = []
  for entity in request_result["ads_entities"]:
    all_products.extend(entity.get("products", []))

    if entity.get("error_message") and not entity.get("products"):
         all_products.append({"status": constants.STATUS_FAILED})

  request_result["status"] = _calculate_status_for_products(all_products)


def _record_job_status(bq_service, results_by_request):
  """Records the job status into BigQuery."""
  if results_by_request:
    logger.info("Inserting status for %d requests", len(results_by_request))
    bq_service.record_insertion_status(list(results_by_request.values()))


def main():
  """Main execution function for the Cloud Run Job.

  Loads environment variables, initializes services, fetches updates from
  BigQuery, and processes each ad group update.
  """
  load_dotenv()

  parser = argparse.ArgumentParser(
      description="Process ad group updates from BigQuery."
  )
  parser.add_argument(
      "--request-uuid",
      type=str,
      help="Optional UUID to filter processing to a specific request.",
  )
  args = parser.parse_args()

  logger.info("Starting Cloud Run Job for Shopping Listing Groups")
  if args.request_uuid:
    logger.info("Filtering by request UUID: %s", args.request_uuid)

  try:
    bq_service = BigQueryService()
    ads_service = AdsService()

    updates = bq_service.fetch_pending_updates(request_uuid=args.request_uuid)
    logger.info("Found %d ad groups to update", len(updates))

    results_by_request = {}

    for update in updates:
      logger.info(
          "Processing Ad Group %s "
          "(Analysis: %s, "
          "Customer: %s) with %d offers",
          update.ad_group_id,
          update.video_analysis_uuid,
          update.customer_id,
          len(update.offer_ids),
      )
      result = ads_service.add_offers_to_ad_group(
          update.ad_group_id, update.campaign_id, update.offer_ids,
          str(update.customer_id), cpc_bid_micros=update.cpc_bid_micros
      )

      _update_request_status(results_by_request, update, result)

    _record_job_status(bq_service, results_by_request)

    logger.info("Job completed successfully")

  except Exception:
    logger.exception("Job failed with error")
    raise


if __name__ == "__main__":
  main()
