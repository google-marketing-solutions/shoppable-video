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

"""Dependencies for API routes, including Authentication and BigQuery Service."""

import functools

from app.core import config
from app.services import bigquery_service
import fastapi
from fastapi import security
import firebase_admin
from firebase_admin import auth


# Initialize Firebase
try:
  firebase_admin.get_app()
except ValueError:
  firebase_admin.initialize_app()

security_scheme = security.HTTPBearer(auto_error=False)


@functools.lru_cache()
def get_bigquery_service() -> bigquery_service.BigQueryService:
  """Creates and caches a singleton instance of the BigQueryService.

  This ensures that the BigQuery client is reused across requests,
  optimizing connection management.
  """
  return bigquery_service.BigQueryService(
      project_id=config.settings.PROJECT_ID,
      dataset_id=config.settings.DATASET_ID,
      analysis_table_id=config.settings.ANALYSIS_TABLE_ID,
      status_table_id=config.settings.STATUS_TABLE_ID,
      status_view_id=config.settings.STATUS_VIEW_ID,
  )


async def get_current_user(
    credentials: security.HTTPAuthorizationCredentials = fastapi.Depends(
        security_scheme
    ),
):
  """Gets the current user from the authentication credentials.

  Args:
    credentials: The authorization credentials from the request header.

  Returns:
    A dictionary containing the decoded and verified Firebase ID token.

  Raises:
    HTTPException: If the user is not authenticated or the token is invalid.
  """
  # Allow bypass in local dev environment
  if config.settings.ENVIRONMENT in ["local", "dev"]:
    return {"uid": "dev_user", "email": "dev@example.com"}

  if not credentials:
    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_403_FORBIDDEN,
        detail="Not authenticated",
    )
  token = credentials.credentials
  try:
    decoded_token = auth.verify_id_token(token)
    return decoded_token
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid authentication credentials: {str(e)}",
        headers={"WWW-Authenticate": "Bearer"},
    ) from e
