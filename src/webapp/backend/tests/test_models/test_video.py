"""Unit tests for video models."""

from app.models import product as product_model
from app.models import video as video_model
import pydantic
import pytest


def test_video_metadata_valid():
  """Test creating a valid VideoMetadata."""
  data = {"title": "Test Video", "description": "A video for testing"}
  metadata = video_model.VideoMetadata(**data)
  expected = {"title": "Test Video", "description": "A video for testing"}
  assert metadata.model_dump() == expected


def test_video_valid():
  """Test creating a valid Video."""
  metadata = video_model.VideoMetadata(
      title="Test Video", description="A video for testing"
  )
  data = {
      "uuid": "vid-1",
      "source": "google_ads",
      "video_id": "yt-123",
      "metadata": metadata,
  }
  video = video_model.Video(**data)
  expected = {
      "uuid": "vid-1",
      "source": "google_ads",
      "video_id": "yt-123",
      "gcs_uri": None,
      "md5_hash": None,
      "metadata": {"title": "Test Video", "description": "A video for testing"},
  }
  assert video.model_dump() == expected


def test_video_missing_required_fields():
  """Test creating Video without required fields."""
  with pytest.raises(pydantic.ValidationError):
    video_model.Video(**{"source": "google_ads"})


def test_video_analysis_valid():
  """Test creating a valid VideoAnalysis."""
  video = video_model.Video(uuid="vid-1", source="google_ads")
  product = product_model.IdentifiedProduct(
      uuid="prod-1",
      title="Title",
      description="Desc",
      relevance_reasoning="Reason",
      video_timestamp=10,
      matched_products=[],
  )
  data = {"video": video, "identified_products": [product]}
  analysis = video_model.VideoAnalysis(**data)
  expected = {
      "video": {
          "uuid": "vid-1",
          "source": "google_ads",
          "video_id": None,
          "gcs_uri": None,
          "md5_hash": None,
          "metadata": None,
      },
      "identified_products": [{
          "uuid": "prod-1",
          "title": "Title",
          "description": "Desc",
          "relevance_reasoning": "Reason",
          "video_timestamp": 10,
          "matched_products": [],
      }],
  }
  assert analysis.model_dump() == expected


def test_video_analysis_summary_valid():
  """Test creating a valid VideoAnalysisSummary."""
  video = video_model.Video(uuid="vid-1", source="google_ads")
  data = {
      "video": video,
      "identified_products_count": 5,
      "matched_products_count": 10,
      "approved_products_count": 2,
      "disapproved_products_count": 1,
      "unreviewed_products_count": 7,
  }
  summary = video_model.VideoAnalysisSummary(**data)
  expected = {
      "video": {
          "uuid": "vid-1",
          "source": "google_ads",
          "video_id": None,
          "gcs_uri": None,
          "md5_hash": None,
          "metadata": None,
      },
      "identified_products_count": 5,
      "matched_products_count": 10,
      "approved_products_count": 2,
      "disapproved_products_count": 1,
      "unreviewed_products_count": 7,
  }
  assert summary.model_dump() == expected


def test_pagination_params_default():
  """Test PaginationParams default values."""
  params = video_model.PaginationParams()
  expected = {"limit": 10, "offset": 0}
  assert params.model_dump() == expected


def test_pagination_params_negative_limit():
  """Test PaginationParams with negative limit."""
  with pytest.raises(pydantic.ValidationError):
    video_model.PaginationParams(limit=-1)


def test_pagination_params_negative_offset():
  """Test PaginationParams with negative offset."""
  with pytest.raises(pydantic.ValidationError):
    video_model.PaginationParams(offset=-1)


def test_video_analysis_summary_negative_counts():
  """Test VideoAnalysisSummary with negative counts."""
  video = video_model.Video(uuid="vid-1", source="google_ads")
  fields = [
      "identified_products_count",
      "matched_products_count",
      "approved_products_count",
      "disapproved_products_count",
      "unreviewed_products_count",
  ]
  for field in fields:
    data = {
        "video": video,
        "identified_products_count": 0,
        "matched_products_count": 0,
        "approved_products_count": 0,
        "disapproved_products_count": 0,
        "unreviewed_products_count": 0,
    }
    data[field] = -1
    with pytest.raises(pydantic.ValidationError):
      video_model.VideoAnalysisSummary(**data)


def test_paginated_video_analysis_summary_valid():
  """Test creating a valid PaginatedVideoAnalysisSummary."""
  summary = video_model.VideoAnalysisSummary(
      video=video_model.Video(uuid="vid-1", source="google_ads"),
      identified_products_count=1,
      matched_products_count=1,
      approved_products_count=0,
      disapproved_products_count=0,
      unreviewed_products_count=1,
  )
  data = {
      "items": [summary],
      "total_count": 100,
      "limit": 10,
      "offset": 0,
  }
  paginated = video_model.PaginatedVideoAnalysisSummary(**data)
  expected = {
      "items": [{
          "video": {
              "uuid": "vid-1",
              "source": "google_ads",
              "video_id": None,
              "gcs_uri": None,
              "md5_hash": None,
              "metadata": None,
          },
          "identified_products_count": 1,
          "matched_products_count": 1,
          "approved_products_count": 0,
          "disapproved_products_count": 0,
          "unreviewed_products_count": 1,
      }],
      "total_count": 100,
      "limit": 10,
      "offset": 0,
  }
  assert paginated.model_dump() == expected
