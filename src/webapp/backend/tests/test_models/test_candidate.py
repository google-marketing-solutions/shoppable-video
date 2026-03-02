"""Unit tests for candidate models."""

import datetime
from typing import Any
from app.models import candidate as candidate_model
import pydantic
import pytest


def test_destination_valid():
  """Test creating a valid Destination."""
  data = {
      "ad_group_id": "ag-1",
      "campaign_id": "camp-1",
      "customer_id": "cust-1",
      "ad_group_name": "Test Ad Group",
  }
  dest = candidate_model.Destination(**data)
  expected = {
      "ad_group_id": "ag-1",
      "campaign_id": "camp-1",
      "customer_id": "cust-1",
      "ad_group_name": "Test Ad Group",
  }
  assert dest.model_dump() == expected


def test_destination_missing_required():
  """Test Destination without required fields."""
  missing_data: Any = {"ad_group_id": "ag-1"}
  with pytest.raises(pydantic.ValidationError):
    candidate_model.Destination(**missing_data)


def test_submission_metadata_valid():
  """Test creating a valid SubmissionMetadata."""
  dest = candidate_model.Destination(
      ad_group_id="ag-1", campaign_id="camp-1", customer_id="cust-1"
  )
  data = {
      "request_uuid": "req-1",
      "video_uuid": "vid-1",
      "offer_ids": "offer1,offer2",
      "destinations": [dest],
      "submitting_user": "user@example.com",
      "cpc": 1.5,
  }
  metadata = candidate_model.SubmissionMetadata(**data)
  expected = {
      "request_uuid": "req-1",
      "video_uuid": "vid-1",
      "offer_ids": "offer1,offer2",
      "destinations": [{
          "ad_group_id": "ag-1",
          "campaign_id": "camp-1",
          "customer_id": "cust-1",
          "ad_group_name": None,
      }],
      "submitting_user": "user@example.com",
      "cpc": 1.5,
  }
  assert metadata.model_dump() == expected


def test_submission_metadata_negative_cpc():
  """Test SubmissionMetadata with negative CPC."""
  with pytest.raises(pydantic.ValidationError):
    candidate_model.SubmissionMetadata(cpc=-0.1)


def test_candidate_status_valid():
  """Test creating a valid CandidateStatus."""
  timestamp = datetime.datetime.now(datetime.timezone.utc)
  data = {
      "status": candidate_model.Status.APPROVED,
      "user": "reviewer@example.com",
      "is_added_by_user": True,
      "modified_timestamp": timestamp,
  }
  status = candidate_model.CandidateStatus(**data)
  expected = {
      "status": candidate_model.Status.APPROVED,
      "user": "reviewer@example.com",
      "is_added_by_user": True,
      "modified_timestamp": timestamp,
  }
  assert status.model_dump() == expected


def test_candidate_valid():
  """Test creating a valid Candidate."""
  status = candidate_model.CandidateStatus(
      status=candidate_model.Status.UNREVIEWED
  )
  data = {
      "video_analysis_uuid": "va-1",
      "identified_product_uuid": "ip-1",
      "candidate_offer_id": "offer-1",
      "candidate_status": status,
  }
  candidate = candidate_model.Candidate(**data)
  expected = {
      "video_analysis_uuid": "va-1",
      "identified_product_uuid": "ip-1",
      "candidate_offer_id": "offer-1",
      "candidate_status": {
          "status": candidate_model.Status.UNREVIEWED,
          "user": None,
          "is_added_by_user": False,
          "modified_timestamp": None,
      },
  }
  assert candidate.model_dump() == expected
