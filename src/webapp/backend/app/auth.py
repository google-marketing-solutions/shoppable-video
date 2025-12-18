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

"""Authentication using Identity Platform/Firebase SDK."""
import os

import fastapi
from fastapi import security
from fastapi import status
import firebase_admin
from firebase_admin import auth

try:
  firebase_admin.get_app()
except ValueError:
  firebase_admin.initialize_app()

security = security.HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: security.HTTPAuthorizationCredentials = fastapi.Depends(
        security
    )
):
  """Gets the current user from the authentication credentials.

  Args:
    credentials: The authorization credentials from the request header.

  Returns:
    A dictionary containing the decoded and verified Firebase ID token.

  Raises:
    HTTPException: If the user is not authenticated or the token is invalid.
  """
  if os.getenv("ENV") == "dev":
    return {"uid": "dev_user", "email": "dev@example.com"}

  if not credentials:
    raise fastapi.HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authenticated",
    )
  token = credentials.credentials
  try:
    decoded_token = auth.verify_id_token(token)
    return decoded_token
  except Exception as e:
    raise fastapi.HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid authentication credentials: {str(e)}",
        headers={"WWW-Authenticate": "Bearer"},
    ) from e
