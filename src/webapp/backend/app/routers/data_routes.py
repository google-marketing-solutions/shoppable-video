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

"""This module defines the API routes for managing video analysis data."""
import os
from typing import Any, Dict, List
import uuid
from app.models import CandidateStatus
from app.models import VideoAnalysis
from app.services.bigquery_service import BigQueryService
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

router = APIRouter()
PROJECT_ID = os.environ.get("PROJECT_ID")
DATASET_ID = os.environ.get("DATASET_ID")
TABLE_ID = os.environ.get("TABLE_ID")
bq_service = BigQueryService(PROJECT_ID, DATASET_ID, TABLE_ID)


@router.post("/candidate-status/add", status_code=status.HTTP_201_CREATED)
async def add_candidate_status(status_data: CandidateStatus):
  try:
    record = status_data.dict()
    record["status"] = record["status"].value
    new_record = bq_service.add_candidate_status(record)
    return new_record
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error creating candidate status: {str(e)}"
    ) from e


@router.get("/candidate-status/latest", response_model=List[Dict[str, Any]])
async def get_latest_candidate_statuses():
  try:
    return bq_service.get_latest_candidate_statuses()
  except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Error fetching latest candidate statuses: {str(e)}"
    ) from e


@router.get("/status/{candidate_status}", response_model=List[Dict[str, Any]])
async def get_candidate_statuses_by_status(candidate_status: str):
  try:
    return bq_service.get_candidate_statuses_by_status(candidate_status)
  except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Error fetching candidate statuses by status: {str(e)}"
    ) from e


@router.post("/video-analysis", status_code=status.HTTP_201_CREATED)
async def create_data(annotation: VideoAnalysis):
  try:
    record = annotation.dict()
    if "id" not in record:
      record["id"] = str(uuid.uuid4())
    new_record = bq_service.create_record(record)
    return new_record
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error creating record: {str(e)}"
    ) from e


@router.get("/video-analysis", response_model=List[Dict[str, Any]])
async def get_all_data():
  try:
    return bq_service.get_records()
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error fetching records: {str(e)}"
    ) from e


@router.get(
    "/video-annotations/video/{video_id}", response_model=List[Dict[str, Any]]
)
async def get_data_by_video_id(video_id: str):
  try:
    return bq_service.get_records_by_video_id(video_id)
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error fetching records by video_id: {str(e)}"
    ) from e


@router.get("/video-analysis/{record_id}")
async def get_data_by_id(record_id: str):
  try:
    record = bq_service.get_record_by_id(record_id)
    if record:
      return record
    raise HTTPException(status_code=404, detail="Record not found")
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error fetching record: {str(e)}"
    ) from e


@router.put("/video-analysis/{record_id}")
async def update_data(record_id: str, annotation: VideoAnalysis):
  try:
    record = annotation.dict()
    updated_record = bq_service.update_record(record_id, record)
    return updated_record
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error updating record: {str(e)}"
    ) from e


@router.delete(
    "/video-analysis/{record_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_data(record_id: str):
  try:
    bq_service.delete_record(record_id)
    return
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error deleting record: {str(e)}"
    ) from e
