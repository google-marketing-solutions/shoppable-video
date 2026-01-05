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

"""Logging configuration module.

Configures the Python standard logging library to output logs in structured JSON
format. This is essential for observability in cloud environments like Google
Cloud Run.
"""

import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def setup_logging() -> None:
  """Configures the root logger to output JSON structured logs to stdout.

  The configuration includes:
  - Log Level: INFO by default.
  - Handler: StreamHandler (stdout).
  - Formatter: JSON formatter including timestamp, level, name, and message.
  """
  logger = logging.getLogger()

  # Avoid duplicate handlers if function is called multiple times.
  if logger.handlers:
    return

  handler = logging.StreamHandler(sys.stdout)

  # Define JSON structure mapping.
  formatter = JsonFormatter(
      "%(asctime)s %(levelname)s %(name)s %(message)s",
      datefmt="%Y-%m-%dT%H:%M:%SZ",
      rename_fields={"levelname": "severity", "asctime": "timestamp"},
  )

  handler.setFormatter(formatter)
  logger.addHandler(handler)
  logger.setLevel(logging.INFO)
