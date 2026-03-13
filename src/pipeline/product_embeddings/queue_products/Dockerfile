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
COPY src/pipeline/product_embeddings/queue_products ./src/pipeline/product_embeddings/queue_products

# Install dependencies using uv sync
RUN uv sync --frozen --package queue_products --no-dev

# Set the entrypoint
ENTRYPOINT ["uv", "run", "--package", "queue_products", "python", "src/pipeline/product_embeddings/queue_products/main.py"]
