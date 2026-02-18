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

"""Routes for managing video analysis data."""

from app.api import dependencies
from app.core.config import settings
from app.models import video
from app.services import bigquery_service
from app.services import google_ads
import fastapi
from google.ads.googleads import client

router = fastapi.APIRouter(
    dependencies=[fastapi.Depends(dependencies.get_session_data)]
)


@router.get(
    "/analysis/summary", response_model=video.PaginatedVideoAnalysisSummary
)
async def get_video_analysis_summary(
    limit: int = 10,
    offset: int = 0,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Gets a video analysis summary record."""
  pagination = video.PaginationParams(limit=limit, offset=offset)
  try:
    return bq_service.get_video_analysis_summary(pagination)
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500, detail=f"Error fetching records: {str(e)}"
    ) from e


@router.get("/analysis/{uuid}", response_model=video.VideoAnalysis)
async def get_video_analysis_by_id(
    uuid: str,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Gets a video analysis record by its unique analysis ID."""
  try:
    record = bq_service.get_video_analysis(uuid)
    if record:
      return record
    raise fastapi.HTTPException(status_code=404, detail="Record not found")
  except fastapi.HTTPException:
    raise
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500, detail=f"Error fetching record: {str(e)}"
    ) from e


@router.get("/analysis/{uuid}/ad-groups")
async def get_ad_groups_for_video(
    uuid: str,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
    google_ads_client: client.GoogleAdsClient = fastapi.Depends(
        dependencies.get_authenticated_client
    ),
):
  """Gets ad groups for the video associated with the analysis UUID."""
  target_customer_id = settings.GOOGLE_ADS_CUSTOMER_ID
  if not target_customer_id:
    raise fastapi.HTTPException(
        status_code=500,
        detail="Google Ads Customer ID is not configured in settings.",
    )

  analysis = bq_service.get_video_analysis(uuid)
  if not analysis or not analysis.video or not analysis.video.video_id:
    raise fastapi.HTTPException(
        status_code=404, detail="Video Analysis or Video ID not found"
    )

  try:
    campaign_ids = bq_service.get_campaigns_for_video(
        analysis.video.video_id, target_customer_id
    )

    if not campaign_ids:
      return []

    ga_service = google_ads.GoogleAdsService(
        google_ads_client, target_customer_id
    )
    all_ad_groups = []

    for campaign_id in campaign_ids:
      ad_groups = ga_service.get_ad_groups(campaign_id)
      all_ad_groups.extend(ad_groups)

    return all_ad_groups

  except Exception as e:
    raise fastapi.HTTPException(status_code=500, detail=str(e)) from e
