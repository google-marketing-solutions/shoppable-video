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

FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing pyc files to disc.
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr.
ENV PYTHONUNBUFFERED=1

# Install dependencies.
COPY src/webapp/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY src/webapp/backend/app ./app

# Run gunicorn binding to port 8080 (required by Cloud Run).
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app.main:app", "-k", "uvicorn.workers.UvicornWorker"]
