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

from typing import Any, Dict, List
from app.api import dependencies
from app.services import bigquery_service
import fastapi

router = fastapi.APIRouter()


@router.get("/analysis", response_model=List[Dict[str, Any]])
async def get_all_data(
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Gets all video analysis records."""
  try:
    return bq_service.get_video_analysis()
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500, detail=f"Error fetching records: {str(e)}"
    ) from e


@router.get(
    "/analysis/video/{video_id}", response_model=List[Dict[str, Any]]
)
async def get_data_by_video_id(
    video_id: str,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Gets video analysis records filtered by video ID."""
  try:
    return bq_service.get_video_analysis_by_video_id(video_id)
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500, detail=f"Error fetching records by video_id: {str(e)}"
    ) from e


@router.get("/analysis/{record_id}")
async def get_data_by_id(
    record_id: str,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Gets a video analysis record by its unique analysis ID."""
  try:
    record = bq_service.get_video_analysis_by_id(record_id)
    if record:
      return record
    raise fastapi.HTTPException(status_code=404, detail="Record not found")
  except fastapi.HTTPException:
    raise
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500, detail=f"Error fetching record: {str(e)}"
    ) from e
