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

# Dockerfile

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Copy the workspace configuration
COPY pyproject.toml uv.lock ./

# Copy the sub-project and shared project
COPY src/pipeline/shared ./src/pipeline/shared
COPY src/pipeline/video_inventory_analysis/queue_videos ./src/pipeline/video_inventory_analysis/queue_videos

# Install dependencies using uv sync
# We use --frozen to ensure we use the exact versions from uv.lock
RUN uv sync --frozen --package queue_videos --no-dev

# Set the entrypoint
# Using uv run ensures the virtual environment is used
ENTRYPOINT ["uv", "run", "--package", "queue_videos", "python", "src/pipeline/video_inventory_analysis/queue_videos/main.py"]
