"""Pytest configuration and common fixtures for backend tests."""

import os

import pytest

# Set mock environment variables BEFORE importing app or settings
os.environ["GOOGLE_CLIENT_ID"] = "mock-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "mock-client-secret"
os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"] = "mock-dev-token"
os.environ["GOOGLE_ADS_CUSTOMER_ID"] = "1234567890"
os.environ["PROJECT_ID"] = "mock-project-id"
os.environ["DATASET_ID"] = "mock-dataset-id"
os.environ["VIDEO_ANALYSIS_TABLE_ID"] = "mock-table"
os.environ["MATCHED_PRODUCTS_TABLE_ID"] = "mock-table"
os.environ["MATCHED_PRODUCTS_VIEW_ID"] = "mock-table"
os.environ["CANDIDATE_STATUS_TABLE_ID"] = "mock-table"
os.environ["CANDIDATE_STATUS_VIEW_ID"] = "mock-table"
os.environ["LATEST_PRODUCTS_TABLE_ID"] = "mock-table"
os.environ["GOOGLE_ADS_INSERTION_REQUESTS_TABLE_ID"] = "mock-table"
os.environ["AD_GROUP_INSERTION_STATUS_TABLE_ID"] = "mock-table"
os.environ["SESSION_SECRET_KEYS"] = (
    "lMLn0rfWx7BcYUX39DvHWC1rJmZmdzN3pm-u-cPvfJM="
)
os.environ["ENVIRONMENT"] = "testing"
os.environ["LB_DOMAIN"] = "localhost"
os.environ["FRONTEND_URL"] = "http://localhost:4200"

from app import main  # pylint: disable=wrong-import-position, g-import-not-at-top, g-bad-import-order
from fastapi import testclient  # pylint: disable=wrong-import-position, g-import-not-at-top, g-bad-import-order


@pytest.fixture
def client():
  """FastAPI test client fixture."""
  with testclient.TestClient(main.app) as c:
    yield c
