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

"""Routes for managing candidate statuses."""

from typing import Any, Dict, List
from app import models
from app.api import dependencies
from app.services import bigquery_service
import fastapi

router = fastapi.APIRouter()


@router.post("/add", status_code=fastapi.status.HTTP_201_CREATED)
async def add_candidate_status(
    status_data: models.CandidateStatus,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Adds a new candidate status."""
  try:
    record = status_data.dict()
    record["status"] = record["status"].value
    new_record = bq_service.add_candidate_status(record)
    return new_record
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500, detail=f"Error creating candidate status: {str(e)}"
    ) from e


@router.get("/latest", response_model=List[Dict[str, Any]])
async def get_latest_candidate_statuses(
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Gets the latest candidate statuses."""
  try:
    return bq_service.get_latest_candidate_statuses()
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500,
        detail=f"Error fetching latest candidate statuses: {str(e)}",
    ) from e


@router.get("/status/{candidate_status}", response_model=List[Dict[str, Any]])
async def get_candidate_statuses_by_status(
    candidate_status: str,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Gets candidate statuses filtered by status."""
  try:
    return bq_service.get_candidate_statuses_by_status(candidate_status)
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500,
        detail=f"Error fetching candidate statuses by status: {str(e)}",
    ) from e


@router.get("/analysis/{analysis_id}", response_model=List[Dict[str, Any]])
async def get_candidate_statuses_by_analysis_id(
    analysis_id: str,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Gets candidate statuses filtered by their analysis ID."""
  try:
    return bq_service.get_candidate_statuses_by_analysis_id(analysis_id)
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500,
        detail=f"Error fetching candidate statuses by analysis ID: {str(e)}",
    ) from e


@router.get("/{analysis_id}/{offer_id}", response_model=Dict[str, Any])
async def get_candidate_status(
    analysis_id: str,
    offer_id: str,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Gets a specific candidate status record by analysis ID and offer ID."""
  try:
    record = bq_service.get_candidate_status(analysis_id, offer_id)
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500, detail=f"Error fetching candidate status: {str(e)}"
    ) from e

  if record is None:
    raise fastapi.HTTPException(
        status_code=404, detail="Candidate status not found"
    )

  return record
