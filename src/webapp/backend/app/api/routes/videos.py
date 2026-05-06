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

"""Routes for managing video analysis data."""

from app.api import dependencies
from app.models import video
from app.services import firestore_service
from app.services import google_ads
import fastapi

router = fastapi.APIRouter(
    dependencies=[fastapi.Depends(dependencies.get_session_data)]
)


@router.get(
    "/analysis/summary", response_model=video.PaginatedVideoAnalysisSummary
)
def get_video_analysis_summary(
    pagination: video.PaginationParams = fastapi.Depends(),
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
):
  """Gets a video analysis summary record."""
  return fs_service.get_video_analysis_summary(pagination)


@router.get("/analysis/{uuid}", response_model=video.VideoAnalysis)
def get_video_analysis_by_id(
    uuid: str,
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
):
  """Gets a video analysis record by its unique analysis ID."""
  record = fs_service.get_video_analysis(uuid)
  if record:
    return record
  raise fastapi.HTTPException(status_code=404, detail="Record not found")


@router.get("/analysis/{uuid}/ad-groups")
def get_ad_groups_for_video(
    uuid: str,
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
    ads_service: google_ads.GoogleAdsService = fastapi.Depends(
        dependencies.get_google_ads_service
    ),
):
  """Gets ad groups for the video associated with the analysis UUID."""
  analysis = fs_service.get_video_analysis(uuid)
  if not analysis or not analysis.video or not analysis.video.video_id:
    raise fastapi.HTTPException(
        status_code=404, detail="Video Analysis or Video ID not found"
    )

  target_customer_id = ads_service.login_customer_id

  # Use native discovery logic from GoogleAdsService that replaced
  # BigQuery analytics reads.
  linked_entities = ads_service.get_ad_groups_with_video(
      video_id=analysis.video.video_id, customer_id=target_customer_id
  )

  # Map key keys to retain old expected list format
  results = []
  for entity in linked_entities:
    results.append({
        "id": entity["ad_group_id"],
        "name": entity["ad_group_name"],
        "campaign_id": entity["campaign_id"],
        "customer_id": entity["customer_id"],
    })

  return results
