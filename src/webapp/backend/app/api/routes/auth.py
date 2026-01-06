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

"""API routes for handling user authentication."""

import json
import logging
from typing import Annotated, Any, Dict, Union

from app.api.dependencies import get_session_data
from app.core.config import settings
from app.core.security import encrypt_token
from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/login", response_model=None)
def login() -> RedirectResponse:
  """Initiates the OAuth2 flow with UserInfo scopes."""

  scope = " ".join([
      "https://www.googleapis.com/auth/adwords",
      "https://www.googleapis.com/auth/userinfo.email",
      "https://www.googleapis.com/auth/userinfo.profile",
  ])

  auth_url = (
      f"https://accounts.google.com/o/oauth2/v2/auth?"
      f"client_id={settings.GOOGLE_CLIENT_ID}&"
      f"redirect_uri={settings.redirect_uri}&"
      f"response_type=code&scope={scope}&access_type=offline&prompt=consent"
  )
  return RedirectResponse(auth_url)


@router.get("/callback", response_model=None)
def auth_callback(code: str) -> Union[RedirectResponse, JSONResponse]:
  """Exchanges code for token, fetches identity, and sets secure session.

  Args:
    code: The authorization code received from Google's OAuth2 server.
  """

  token_url = "https://oauth2.googleapis.com/token"
  payload = {
      "client_id": settings.GOOGLE_CLIENT_ID,
      "client_secret": settings.GOOGLE_CLIENT_SECRET,
      "code": code,
      "grant_type": "authorization_code",
      "redirect_uri": settings.redirect_uri,
  }

  try:
    # 1. Exchange Code for Tokens.
    token_resp = requests.post(token_url, data=payload, timeout=10)
    tokens = token_resp.json()

    if "refresh_token" not in tokens:
      logger.warning("OAuth exchange successful but no Refresh Token returned.")
      return JSONResponse(
          content={
              "error": "No refresh token returned. Revoke access and try again."
          },
          status_code=400,
      )

    # 2. Fetch User Identity.
    user_info_resp = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=5,
    )
    profile = user_info_resp.json()

    # 3. Create Session Payload.
    session_data = {
        "rt": tokens["refresh_token"],
        "email": profile.get("email"),
        "picture": profile.get("picture"),
        "name": profile.get("name"),
    }

    # 4. Encrypt and Set Cookie.
    serialized_session = json.dumps(session_data)
    encrypted_token = encrypt_token(serialized_session)

    redirect_resp = RedirectResponse(url=settings.FRONTEND_URL)

    redirect_resp.set_cookie(
        key="session_token",
        value=encrypted_token,
        httponly=True,
        secure=settings._is_production,  # pylint: disable=protected-access
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 Days.
    )
    return redirect_resp

  except (RequestException, json.JSONDecodeError) as e:
    logger.exception("Auth callback failed.")
    return JSONResponse(
        content={
            "error": "Authentication failed.",
            "details": str(e)
        },
        status_code=500,
    )


@router.get("/me")
def check_session(
    session_data: Annotated[Dict[str, Any],
                            Depends(get_session_data)],
) -> Dict[str, Any]:
  """Returns user identity for the Frontend UI using the session dependency.

  Args:
    session_data: Dictionary containing user session information.
  """
  return {
      "status": "authenticated",
      "user": {
          "email": session_data.get("email"),
          "picture": session_data.get("picture"),
          "name": session_data.get("name"),
      },
  }


@router.get("/logout", response_model=None)
def logout() -> JSONResponse:
  """Logs out the user by clearing the session cookie."""

  response = JSONResponse(content={"message": "Logged out"})
  response.delete_cookie("session_token")
  return response
