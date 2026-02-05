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

"""Routes for managing Ad Group Insertion Status."""

from typing import Sequence
from app.api import dependencies
from app.models import ad_group_insertion
from app.models import video
from app.services import bigquery_service
import fastapi

router = fastapi.APIRouter()


@router.get(
    "/status",
    response_model=ad_group_insertion.PaginatedAdGroupInsertionStatus,
)
async def get_all_ad_group_insertion_statuses(
    pagination: video.PaginationParams = fastapi.Depends(),
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Retrieves all Ad Group insertion statuses with pagination.

  Args:
    pagination: Pagination parameters (limit, offset).
    bq_service: The BigQuery service instance.

  Returns:
    A paginated list of Ad Group insertion status records.
  """
  try:
    return bq_service.get_all_ad_group_insertion_statuses(pagination)
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500,
        detail=f"Error retrieving ad group insertion statuses: {str(e)}",
    ) from e


@router.get(
    "/status/{request_uuid}",
    response_model=Sequence[ad_group_insertion.AdGroupInsertionStatus],
)
async def get_ad_group_insertion_status(
    request_uuid: str,
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Retrieves the status of an Ad Group insertion request.

  Args:
    request_uuid: The UUID of the request.
    bq_service: The BigQuery service instance.

  Returns:
    A list of Ad Group insertion status records.
  """
  try:
    return bq_service.get_ad_group_insertion_status(request_uuid)
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500,
        detail=f"Error retrieving ad group insertion status: {str(e)}",
    ) from e
