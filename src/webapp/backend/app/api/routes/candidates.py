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
from app.core import config
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


@router.post(
    "/submission-requests", status_code=fastapi.status.HTTP_201_CREATED
)
async def insert_submission_requests(
    submission_requests: Sequence[candidate.SubmissionMetadata],
    bq_service: bigquery_service.BigQueryService = fastapi.Depends(
        dependencies.get_bigquery_service
    ),
):
  """Inserts submission requests directly into the Google Ads insertion table.

  Args:
    submission_requests: a list of SubmissionMetadata objects.
    bq_service: a BigQueryService instance.
  """
  try:
    # Populate default customer_id if missing
    for request in submission_requests:
      if request.destinations:
        for dest in request.destinations:
          if not dest.customer_id:
            dest.customer_id = config.settings.GOOGLE_ADS_CUSTOMER_ID

    bq_service.insert_submission_requests(submission_requests)
    return {
        "message": (
            f"{len(submission_requests)} Submission Request"
            f"{'s' if len(submission_requests) > 1 else ''}"
            " inserted successfully"
        )
    }
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=500,
        detail=f"Error inserting submission request(s): {str(e)}"
    ) from e
