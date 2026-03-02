"""Unit tests for ad_group_insertion models."""

import datetime
from app.models import ad_group_insertion
import pydantic
import pytest


def test_product_insertion_status_valid():
  """Test creating a valid ProductInsertionStatus."""
  data = {"offer_id": "offer-1", "status": "SUCCESS"}
  status = ad_group_insertion.ProductInsertionStatus(**data)
  expected = {"offer_id": "offer-1", "status": "SUCCESS"}
  assert status.model_dump() == expected


def test_ads_entity_status_valid():
  """Test creating a valid AdsEntityStatus."""
  prod_status = ad_group_insertion.ProductInsertionStatus(
      offer_id="offer-1", status="SUCCESS"
  )
  data = {
      "customer_id": 12345,
      "campaign_id": 67890,
      "ad_group_id": 11111,
      "products": [prod_status],
      "error_message": "Some error",
  }
  entity = ad_group_insertion.AdsEntityStatus(**data)
  expected = {
      "customer_id": 12345,
      "campaign_id": 67890,
      "ad_group_id": 11111,
      "products": [{"offer_id": "offer-1", "status": "SUCCESS"}],
      "error_message": "Some error",
  }
  assert entity.model_dump() == expected


def test_ad_group_insertion_status_valid():
  """Test creating a valid AdGroupInsertionStatus."""
  timestamp = datetime.datetime.now(datetime.timezone.utc)
  entity = ad_group_insertion.AdsEntityStatus(
      customer_id=123, campaign_id=456, ad_group_id=789, products=[]
  )
  data = {
      "request_uuid": "req-1",
      "video_analysis_uuid": "va-1",
      "status": "COMPLETED",
      "ads_entities": [entity],
      "timestamp": timestamp,
  }
  status = ad_group_insertion.AdGroupInsertionStatus(**data)
  expected = {
      "request_uuid": "req-1",
      "video_analysis_uuid": "va-1",
      "status": "COMPLETED",
      "ads_entities": [{
          "customer_id": 123,
          "campaign_id": 456,
          "ad_group_id": 789,
          "products": [],
          "error_message": None,
      }],
      "timestamp": timestamp,
  }
  assert status.model_dump() == expected


def test_paginated_ad_group_insertion_status_valid():
  """Test creating a valid PaginatedAdGroupInsertionStatus."""
  timestamp = datetime.datetime.now(datetime.timezone.utc)
  status = ad_group_insertion.AdGroupInsertionStatus(
      request_uuid="req-1",
      video_analysis_uuid="va-1",
      status="COMPLETED",
      ads_entities=[],
      timestamp=timestamp,
  )
  data = {
      "items": [status],
      "total_count": 1,
      "limit": 10,
      "offset": 0,
  }
  paginated = ad_group_insertion.PaginatedAdGroupInsertionStatus(**data)
  expected = {
      "items": [{
          "request_uuid": "req-1",
          "video_analysis_uuid": "va-1",
          "status": "COMPLETED",
          "ads_entities": [],
          "timestamp": timestamp,
      }],
      "total_count": 1,
      "limit": 10,
      "offset": 0,
  }
  assert paginated.model_dump() == expected


def test_paginated_ad_group_insertion_status_negative_pagination():
  """Test PaginatedAdGroupInsertionStatus with negative pagination fields."""
  fields = ["total_count", "limit", "offset"]
  for field in fields:
    data = {
        "items": [],
        "total_count": 0,
        "limit": 10,
        "offset": 0,
    }
    data[field] = -1
    with pytest.raises(pydantic.ValidationError):
      ad_group_insertion.PaginatedAdGroupInsertionStatus(**data)
