"""Unit tests for product models."""

import datetime
from app.models import candidate
from app.models import product as product_model
import pydantic
import pytest


def test_matched_product_valid():
  """Test creating a valid MatchedProduct."""
  status = candidate.CandidateStatus(status=candidate.Status.UNREVIEWED)
  timestamp = datetime.datetime.now(datetime.timezone.utc)
  data = {
      "matched_product_offer_id": "offer-1",
      "matched_product_title": "Product Title",
      "matched_product_brand": "Brand",
      "matched_timestamp": timestamp,
      "distance": 0.5,
      "candidate_status": status,
  }
  product = product_model.MatchedProduct(**data)

  expected = {
      "matched_product_offer_id": "offer-1",
      "matched_product_title": "Product Title",
      "matched_product_brand": "Brand",
      "matched_product_link": None,
      "matched_product_image_link": None,
      "matched_product_availability": None,
      "matched_timestamp": timestamp,
      "distance": 0.5,
      "candidate_status": {
          "status": candidate.Status.UNREVIEWED,
          "user": None,
          "is_added_by_user": False,
          "modified_timestamp": None,
      },
  }
  assert product.model_dump() == expected


def test_matched_product_invalid_distance():
  """Test MatchedProduct with invalid distance type."""
  status = candidate.CandidateStatus(status=candidate.Status.UNREVIEWED)
  data = {
      "matched_product_offer_id": "offer-1",
      "matched_product_title": "Product Title",
      "matched_product_brand": "Brand",
      "matched_timestamp": datetime.datetime.now(datetime.timezone.utc),
      "distance": "not-a-float",
      "candidate_status": status,
  }
  with pytest.raises(pydantic.ValidationError):
    product_model.MatchedProduct(**data)


def test_matched_product_negative_distance():
  """Test MatchedProduct with negative distance."""
  status = candidate.CandidateStatus(status=candidate.Status.UNREVIEWED)
  data = {
      "matched_product_offer_id": "offer-1",
      "matched_product_title": "Product Title",
      "matched_product_brand": "Brand",
      "matched_timestamp": datetime.datetime.now(datetime.timezone.utc),
      "distance": -0.1,
      "candidate_status": status,
  }
  with pytest.raises(pydantic.ValidationError):
    product_model.MatchedProduct(**data)


def test_identified_product_valid():
  """Test creating a valid IdentifiedProduct."""
  status = candidate.CandidateStatus(status=candidate.Status.UNREVIEWED)
  timestamp = datetime.datetime.now(datetime.timezone.utc)
  matched_data = {
      "matched_product_offer_id": "offer-1",
      "matched_product_title": "Product Title",
      "matched_product_brand": "Brand",
      "matched_timestamp": timestamp,
      "distance": 0.5,
      "candidate_status": status,
  }
  matched_product = product_model.MatchedProduct(**matched_data)

  identified_data = {
      "uuid": "uuid-1",
      "title": "Identified Title",
      "description": "Description",
      "relevance_reasoning": "Reasoning",
      "video_timestamp": 10,
      "matched_products": [matched_product],
  }
  product = product_model.IdentifiedProduct(**identified_data)

  expected = {
      "uuid": "uuid-1",
      "title": "Identified Title",
      "description": "Description",
      "relevance_reasoning": "Reasoning",
      "video_timestamp": 10,
      "matched_products": [{
          "matched_product_offer_id": "offer-1",
          "matched_product_title": "Product Title",
          "matched_product_brand": "Brand",
          "matched_product_link": None,
          "matched_product_image_link": None,
          "matched_product_availability": None,
          "matched_timestamp": timestamp,
          "distance": 0.5,
          "candidate_status": {
              "status": candidate.Status.UNREVIEWED,
              "user": None,
              "is_added_by_user": False,
              "modified_timestamp": None,
          },
      }],
  }
  assert product.model_dump() == expected


def test_identified_product_negative_timestamp():
  """Test IdentifiedProduct with negative video timestamp."""
  status = candidate.CandidateStatus(status=candidate.Status.UNREVIEWED)
  timestamp = datetime.datetime.now(datetime.timezone.utc)
  matched_data = {
      "matched_product_offer_id": "offer-1",
      "matched_product_title": "Product Title",
      "matched_product_brand": "Brand",
      "matched_timestamp": timestamp,
      "distance": 0.5,
      "candidate_status": status,
  }
  matched_product = product_model.MatchedProduct(**matched_data)

  identified_data = {
      "uuid": "uuid-1",
      "title": "Identified Title",
      "description": "Description",
      "relevance_reasoning": "Reasoning",
      "video_timestamp": -10,
      "matched_products": [matched_product],
  }
  with pytest.raises(pydantic.ValidationError):
    product_model.IdentifiedProduct(**identified_data)
