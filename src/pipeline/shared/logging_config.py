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

"""Centralized logging configuration for pipeline jobs."""

import logging
import os
import sys

from google.cloud.logging.handlers import StructuredLogHandler


def configure_logging() -> None:
  """Configures appropriate logging backend based on runtime environment."""

  log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
  is_cloud = (
      "K_SERVICE" in os.environ or os.environ.get("ENVIRONMENT") == "production"
  )

  if is_cloud:
    logging.basicConfig(
        level=log_level,
        handlers=[StructuredLogHandler()],
        force=True,
    )
  else:
    local_handler = logging.StreamHandler(sys.stdout)
    local_handler.setFormatter(
        logging.Formatter("%(levelname)s - %(name)s - %(message)s")
    )
    logging.basicConfig(
        level=log_level,
        handlers=[local_handler],
        force=True,
    )
