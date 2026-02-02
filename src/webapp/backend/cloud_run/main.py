"""Main entry point for the Cloud Run Job.

This module orchestrates the fetching of pending ad group updates from BigQuery
and applies them to Google Ads using the AdsService.
"""

import argparse
import logging

from ads_service import AdsService
from bigquery_service import BigQueryService
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
      ads_service.add_offers_to_ad_group(
          update.ad_group_id, update.offer_ids, update.customer_id,
          cpc_bid_micros=update.cpc_bid_micros
      )

    logger.info("Job completed successfully")

  except Exception:
    logger.exception("Job failed with error")
    raise


if __name__ == "__main__":
  main()
