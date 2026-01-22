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
from app.models import video
from app.services import bigquery_service
import fastapi

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
