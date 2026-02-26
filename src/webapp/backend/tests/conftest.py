"""Pytest configuration and common fixtures for backend tests."""

from app import main
from fastapi import testclient
import pytest


@pytest.fixture
def client():
  """FastAPI test client fixture."""
  with testclient.TestClient(main.app) as c:
    yield c
