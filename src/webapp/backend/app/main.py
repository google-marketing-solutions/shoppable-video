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

"""Main application entry point."""

import logging
from typing import Dict

from app.api.routes import auth
from app.api.routes import candidates
from app.api.routes import reports
from app.api.routes import videos
from app.core import config
from app.core import log_setup
import fastapi
from fastapi.middleware import cors

# Initialize structured logging first.
log_setup.setup_logging()
logger = logging.getLogger(__name__)

# Configure root_path for Load Balancer scenarios.
root_path = ""

app = fastapi.FastAPI(
    title="Shoppable Video Backend",
    version="1.0.0",
    root_path=root_path,
)

# Security: Restrict Cross-Origin requests.
app.add_middleware(
    cors.CORSMiddleware,
    allow_origins=config.settings.cors_origins,  # type: ignore
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

logger.info(
    "CORS initialized with allowed origins: '%s'", config.settings.cors_origins
)
logger.info("Application Root Path set to: '%s'", root_path)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(
    candidates.router, prefix="/api/candidates", tags=["Candidates"]
)
app.include_router(reports.router, prefix="/api/reports", tags=["Reporting"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])


@app.get("/")
def health_check() -> Dict[str, str]:
  """Returns system health status."""
  logger.debug("Health check requested.")
  return {"status": "healthy", "environment": config.settings.ENVIRONMENT}


@app.on_event("startup")
async def startup_event():
  logger.info(">>> MAPPING OF ALL REGISTERED ROUTES <<<")
  for route in app.routes:
    if hasattr(route, "path"):
      logger.info(
          "Route: %s | Name: %s",
          route.path,  # type: ignore
          route.name  # type: ignore
      )
  logger.info(">>> END OF ROUTE MAPPING <<<")
