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

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY src/pipeline/product_embeddings/queue_products/requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Copy the source code
COPY src/pipeline/product_embeddings/queue_products/. .
COPY src/pipeline/shared/. ./shared

# Set the entrypoint
ENTRYPOINT ["python", "main.py"]
