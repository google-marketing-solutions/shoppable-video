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

"""Routes for managing candidate statuses."""

from typing import Sequence

from app.api import dependencies
from app.models import candidate
from app.services import firestore_service
import fastapi

router = fastapi.APIRouter(
    dependencies=[fastapi.Depends(dependencies.get_session_data)]
)


@router.post("/update", status_code=fastapi.status.HTTP_201_CREATED)
def update_candidates(
    candidates: Sequence[candidate.Candidate],
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
):
  """Updates one or more candidates.

  Args:
    candidates: a set of Candidates to update.
    fs_service: a FirestoreService instance.
  """
  fs_service.update_candidates(candidates)
  suffix = "s" if len(candidates) != 1 else ""
  return {
      "message": f"{len(candidates)} Candidate{suffix} updated successfully"
  }


@router.post(
    "/submission-requests", status_code=fastapi.status.HTTP_201_CREATED
)
def insert_submission_requests(
    submission_requests: Sequence[candidate.SubmissionMetadata],
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
):
  """Inserts submission requests directly into the Google Ads insertion table.

  Args:
    submission_requests: a list of SubmissionMetadata objects.
    fs_service: a FirestoreService instance.
  """
  fs_service.insert_submission_requests(submission_requests)
  suffix = "s" if len(submission_requests) != 1 else ""
  return {
      "message": (
          f"{len(submission_requests)} Submission Request{suffix}"
          " inserted successfully"
      )
  }
