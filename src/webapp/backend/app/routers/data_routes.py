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
from app.models import CandidateStatus
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


@router.get(
    "/candidate-status/{candidate_status}", response_model=List[Dict[str, Any]]
)
async def get_candidate_statuses_by_status(candidate_status: str):
  try:
    return bq_service.get_candidate_statuses_by_status(candidate_status)
  except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Error fetching candidate statuses by status: {str(e)}"
    ) from e


@router.get(
    "/candidate-status/analysis/{analysis_id}", response_model=List[Dict[str,
                                                                         Any]]
)
async def get_candidate_statuses_by_analysis_id(analysis_id: str):
  """Gets candidate statuses filtered by their analysis ID.

  Args:
    analysis_id: The ID of the video analysis.

  Returns:
    A list of dictionaries, each representing a candidate status record.

  Raises:
    HTTPException: If an internal server error occurs (500).
  """
  try:
    return bq_service.get_candidate_statuses_by_analysis_id(analysis_id)
  except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Error fetching candidate statuses by analysis ID: {str(e)}"
    ) from e


@router.get(
    "/candidate-status/{analysis_id}/{offer_id}", response_model=Dict[str, Any]
)
async def get_candidate_status(analysis_id: str, offer_id: str):
  """Gets a specific candidate status record by analysis ID and offer ID.

  Args:
    analysis_id: The ID of the video analysis.
    offer_id: The ID of the offer associated with the candidate.

  Returns:
    A dictionary containing the candidate status record.

  Raises:
    HTTPException: If the record is not found (404) or an internal server error
      occurs (500).
  """
  try:
    record = bq_service.get_candidate_status(analysis_id, offer_id)
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error fetching candidate status: {str(e)}"
    ) from e

  if record is None:
    raise HTTPException(status_code=404, detail="Candidate status not found")

  return record


@router.get("/video-analysis", response_model=List[Dict[str, Any]])
async def get_all_data():
  try:
    return bq_service.get_video_analysis()
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error fetching records: {str(e)}"
    ) from e


@router.get(
    "/video-annotations/video/{video_id}", response_model=List[Dict[str, Any]]
)
async def get_data_by_video_id(video_id: str):
  try:
    return bq_service.get_video_analysis_by_video_id(video_id)
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error fetching records by video_id: {str(e)}"
    ) from e


@router.get("/video-analysis/{record_id}")
async def get_data_by_id(record_id: str):
  try:
    record = bq_service.get_video_analysis_by_id(record_id)
    if record:
      return record
    raise HTTPException(status_code=404, detail="Record not found")
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error fetching record: {str(e)}"
    ) from e
