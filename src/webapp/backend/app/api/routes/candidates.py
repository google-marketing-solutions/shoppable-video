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

from typing import Sequence
from app.api import dependencies
from app.models import candidate
from app.services import bigquery_service
import fastapi

router = fastapi.APIRouter()


@router.post("/update", status_code=fastapi.status.HTTP_201_CREATED)
async def update_candidates(
    candidates: Sequence[candidate.Candidate],
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Updates one or more candidates.

  Args:
    candidates: a set of Candidates to update.
    bq_service: a BigQueryService instance.
  """
  try:
    bq_service.update_candidates(candidates)
    return {
        "message": (
            f"{len(candidates)} Candidate{'s' if len(candidates) > 1 else ''}"
            " updated successfully"
        )
    }
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500, detail=f"Error updating candidate(s): {str(e)}"
    ) from e
