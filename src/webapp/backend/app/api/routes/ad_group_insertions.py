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

"""Routes for managing Ad Group Insertion Status."""

from typing import Sequence

from app.api import dependencies
from app.models import ad_group_insertion
from app.models import video
from app.services import firestore_service
import fastapi

router = fastapi.APIRouter(
    dependencies=[fastapi.Depends(dependencies.get_session_data)]
)


@router.get(
    "/status",
    response_model=ad_group_insertion.PaginatedAdGroupInsertionStatus,
)
def get_all_ad_group_insertion_statuses(
    pagination: video.PaginationParams = fastapi.Depends(),
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
):
  """Retrieves all Ad Group insertion statuses with pagination.

  Args:
    pagination: Pagination parameters (limit, offset).
    fs_service: The Firestore service instance.

  Returns:
    A paginated list of Ad Group insertion status records.
  """
  return fs_service.get_all_ad_group_insertion_statuses(pagination)


@router.get(
    "/status/{request_uuid}",
    response_model=Sequence[ad_group_insertion.AdGroupInsertionStatus],
)
def get_ad_group_insertion_status(
    request_uuid: str,
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
):
  """Retrieves the status of an Ad Group insertion request.

  Args:
    request_uuid: The UUID of the request.
    fs_service: The Firestore service instance.

  Returns:
    A list of Ad Group insertion status records.
  """
  return fs_service.get_ad_group_insertion_status(request_uuid)


@router.get(
    "/status/video/{video_uuid}",
    response_model=Sequence[ad_group_insertion.AdGroupInsertionStatus],
)
def get_ad_group_insertion_statuses_for_video(
    video_uuid: str,
    fs_service: firestore_service.FirestoreService = fastapi.Depends(
        dependencies.get_firestore_service
    ),
):
  """Retrieves the Ad Group insertion statuses for a specific video.

  Args:
    video_uuid: The UUID of the video.
    fs_service: The Firestore service instance.

  Returns:
    A list of Ad Group insertion status records.
  """
  return fs_service.get_ad_group_insertion_statuses_for_video(video_uuid)
