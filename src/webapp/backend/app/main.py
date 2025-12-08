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

"""Main application entry point for the FastAPI server."""
import os

from app.routers import data_routes
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

# CORS Configuration
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
if not allowed_origins or allowed_origins == [""]:
  allowed_origins = ["*"]  # Default to * if not set, for safety in dev

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(data_routes.router, prefix="/api")


@app.get("/")
async def root():
  return {"message": "Shoppable Video Backend is running"}
