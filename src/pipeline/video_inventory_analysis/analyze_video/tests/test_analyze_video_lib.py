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

"""Unit tests for the analyze_video_lib module."""

import datetime
from unittest import mock

from google import genai
from google.cloud import bigquery
from google.cloud import storage
from google.genai import types
import pytest

from src.pipeline.shared import common
from src.pipeline.video_inventory_analysis.analyze_video import analyze_video_lib


class TestVideoAnalyzer:
  """Test suite for the VideoAnalyzer class."""

  @pytest.fixture
  def mock_storage_client(self):
    return mock.MagicMock(spec=storage.Client)

  @pytest.fixture
  def mock_genai_client(self):
    return mock.MagicMock(spec=genai.Client)

  def test_video_analyzer_init_with_clients(
      self, mock_storage_client, mock_genai_client
  ):
    """Test initialization of the VideoAnalyzer class with custom clients."""
    analyzer = analyze_video_lib.VideoAnalyzer(
        prompt="custom prompt",
        generative_model_name="custom-model",
        storage_client=mock_storage_client,
        genai_client=mock_genai_client,
    )
    assert analyzer.prompt.text == "custom prompt"
    assert analyzer.generative_model_name == "custom-model"
    assert analyzer.storage_client is mock_storage_client
    assert analyzer.genai_client is mock_genai_client

  @mock.patch("google.cloud.storage.Client")
  @mock.patch("google.genai.Client")
  def test_video_analyzer_init_defaults(
      self, mock_genai_client_class, mock_storage_client_class
  ):
    """Test initialization of VideoAnalyzer class with default clients."""
    mock_default_storage = mock.MagicMock()
    mock_default_genai = mock.MagicMock()
    mock_storage_client_class.return_value = mock_default_storage
    mock_genai_client_class.return_value = mock_default_genai

    analyzer = analyze_video_lib.VideoAnalyzer(
        prompt="default prompt", generative_model_name="default-model"
    )

    mock_storage_client_class.assert_called_once()
    mock_genai_client_class.assert_called_once()
    assert analyzer.prompt.text == "default prompt"
    assert analyzer.generative_model_name == "default-model"
    assert analyzer.storage_client is mock_default_storage
    assert analyzer.genai_client is mock_default_genai

  @mock.patch.object(analyze_video_lib.VideoAnalyzer, "_upload_video_from_gcs")
  def test_analyze_video_with_gcs_uri(
      self, mock_upload_video, mock_storage_client, mock_genai_client
  ):
    """Test analyzing a video from a GCS URI."""
    analyzer = analyze_video_lib.VideoAnalyzer(
        prompt="test prompt",
        generative_model_name="gemini-pro",
        storage_client=mock_storage_client,
        genai_client=mock_genai_client,
    )
    mock_file = types.File(name="uploaded_video")
    mock_upload_video.return_value = mock_file

    mock_response = mock.MagicMock()
    mock_product = common.IdentifiedProduct(
        title="Test Product",
        description="A test product",
        color_pattern_style_usage="red",
        category="test",
        subcategory="test",
        video_timestamp=datetime.timedelta(seconds=1),
        relevance_reasoning="reason",
        embedding=None,
    )
    mock_response.parsed = [mock_product]
    mock_genai_client.models.generate_content.return_value = mock_response

    video = common.Video(
        uuid="1",
        source=common.Source.GCS,
        gcs_uri="gs://bucket/video.mp4",
        md5_hash="1234",
    )
    products = analyzer.analyze_video(video)

    mock_upload_video.assert_called_once_with(gcs_uri="gs://bucket/video.mp4")
    mock_genai_client.models.generate_content.assert_called_once_with(
        model="gemini-pro",
        contents=[mock_file, types.Part(text="test prompt")],
        config=analyzer.genai_config,
    )
    mock_genai_client.files.delete.assert_called_once_with(
        name="uploaded_video"
    )
    assert products == [mock_product]

  def test_analyze_video_with_youtube_url(
      self, mock_storage_client, mock_genai_client
  ):
    """Test analyzing a video from a YouTube URL."""
    analyzer = analyze_video_lib.VideoAnalyzer(
        prompt="test prompt",
        generative_model_name="gemini-pro",
        storage_client=mock_storage_client,
        genai_client=mock_genai_client,
    )
    mock_response = mock.MagicMock()
    mock_product = common.IdentifiedProduct(
        title="YouTube Product",
        description="A youtube product",
        color_pattern_style_usage="blue",
        category="youtube",
        subcategory="youtube",
        video_timestamp=datetime.timedelta(seconds=2),
        relevance_reasoning="youtube reason",
        embedding=None,
    )
    mock_response.parsed = [mock_product]
    mock_genai_client.models.generate_content.return_value = mock_response

    video = common.Video(
        uuid="2", source=common.Source.MANUAL_ENTRY, video_id="youtube123"
    )
    products = analyzer.analyze_video(video)

    mock_genai_client.models.generate_content.assert_called_once_with(
        model="gemini-pro",
        contents=[
            types.Part(
                file_data=types.FileData(
                    file_uri="https://www.youtube.com/watch?v=youtube123"
                )
            ),
            types.Part(text="test prompt"),
        ],
        config=analyzer.genai_config,
    )
    mock_genai_client.files.delete.assert_not_called()
    assert products == [mock_product]

  def test_analyze_video_raises_generative_ai_error(
      self, mock_storage_client, mock_genai_client
  ):
    """Test that GenerativeAIError is raised on API error."""
    analyzer = analyze_video_lib.VideoAnalyzer(
        prompt="test prompt",
        generative_model_name="gemini-pro",
        storage_client=mock_storage_client,
        genai_client=mock_genai_client,
    )
    mock_genai_client.models.generate_content.side_effect = Exception(
        "API Error"
    )
    video = common.Video(
        uuid="3", source=common.Source.MANUAL_ENTRY, video_id="youtube_error"
    )
    with pytest.raises(analyze_video_lib.GenerativeAIError):
      analyzer.analyze_video(video)

  @mock.patch.object(
      analyze_video_lib.VideoAnalyzer, "_wait_for_video_processing"
  )
  def test_upload_video_from_gcs(
      self, mock_wait, mock_storage_client, mock_genai_client
  ):
    """Test uploading a video from GCS."""
    analyzer = analyze_video_lib.VideoAnalyzer(
        prompt="test prompt",
        generative_model_name="gemini-pro",
        storage_client=mock_storage_client,
        genai_client=mock_genai_client,
    )
    mock_blob = mock.MagicMock()
    mock_blob_file = mock.MagicMock()
    mock_blob.open.return_value.__enter__.return_value = mock_blob_file
    mock_storage_client.bucket.return_value.blob.return_value = mock_blob

    mock_uploaded_file = types.File(name="test_file")
    mock_genai_client.files.upload.return_value = mock_uploaded_file
    mock_wait.return_value = mock_uploaded_file

    returned_file = analyzer._upload_video_from_gcs(  # pylint: disable=protected-access
        "gs://bucket/video.mp4"
    )

    mock_storage_client.bucket.assert_called_with("bucket")
    mock_storage_client.bucket.return_value.blob.assert_called_with("video.mp4")
    mock_genai_client.files.upload.assert_called_once_with(
        file=mock_blob_file, config={"mime_type": "video/mp4"}
    )
    mock_wait.assert_called_once_with("test_file", "gs://bucket/video.mp4")
    assert returned_file is mock_uploaded_file

  def test_wait_for_video_processing_active(
      self, mock_storage_client, mock_genai_client
  ):
    """Test waiting for an active video to finish processing."""
    analyzer = analyze_video_lib.VideoAnalyzer(
        prompt="test prompt",
        generative_model_name="gemini-pro",
        storage_client=mock_storage_client,
        genai_client=mock_genai_client,
    )
    mock_file = types.File(name="active_file", state=types.FileState.ACTIVE)
    mock_genai_client.files.get.return_value = mock_file

    result = analyzer._wait_for_video_processing(  # pylint: disable=protected-access
        "active_file", "gs://b/v.mp4"
    )
    assert result == mock_file
    mock_genai_client.files.get.assert_called_once_with(name="active_file")

  def test_wait_for_video_processing_retries(
      self, mock_storage_client, mock_genai_client
  ):
    """Test the retry mechanism for video processing."""
    analyzer = analyze_video_lib.VideoAnalyzer(
        prompt="test prompt",
        generative_model_name="gemini-pro",
        storage_client=mock_storage_client,
        genai_client=mock_genai_client,
    )
    processing_file = types.File(
        name="processing_file", state=types.FileState.PROCESSING
    )
    active_file = types.File(
        name="processing_file", state=types.FileState.ACTIVE
    )
    mock_genai_client.files.get.side_effect = [
        processing_file,
        active_file,
    ]
    with mock.patch("tenacity.nap.time.sleep", return_value=None):
      result = analyzer._wait_for_video_processing(  # pylint: disable=protected-access
          "processing_file", "gs://b/v.mp4"
      )

    assert result == active_file
    assert mock_genai_client.files.get.call_count == 2


class TestBigQueryConnector:
  """Test suite for the BigQueryConnector class."""

  @pytest.fixture
  def mock_bigquery_client(self):
    return mock.MagicMock(spec=bigquery.Client)

  @mock.patch("datetime.datetime")
  def test_insert_video_analysis(self, mock_datetime, mock_bigquery_client):
    """Test inserting a successful video analysis into BigQuery."""
    bq_connector = analyze_video_lib.BigQueryConnector(
        table_id="test-project.test_dataset.test_table",
        bigquery_client=mock_bigquery_client,
    )
    mock_now = mock.MagicMock()
    mock_now.strftime.return_value = "2025-01-01 12:00:00"
    mock_datetime.now.return_value = mock_now

    mock_bigquery_client.insert_rows_json.return_value = []
    video = common.Video(
        uuid="1",
        source=common.Source.GCS,
        gcs_uri="gs://b/v.mp4",
        md5_hash="4321",
        metadata=common.VideoMetadata(title="Test Video", description="Desc"),
    )
    product = common.IdentifiedProduct(
        title="Prod",
        description="A product",
        color_pattern_style_usage="green",
        category="test",
        subcategory="test",
        video_timestamp=datetime.timedelta(seconds=3),
        relevance_reasoning="reason",
        embedding=None,
    )
    products = [product]

    bq_connector.insert_video_analysis(
        video, products, "test-embedding-model", "test-generative-model"
    )

    expected_row = {
        "uuid": "1",
        "timestamp": "2025-01-01 12:00:00",
        "source": "gcs",
        "video_id": None,
        "metadata": {"title": "Test Video", "description": "Desc"},
        "gcs_uri": "gs://b/v.mp4",
        "md5_hash": "4321",
        "status": "SUCCESS",
        "error_message": None,
        "embedding_model_id": "test-embedding-model",
        "generative_model_id": "test-generative-model",
        "identified_products": [product.to_dict()],
    }
    mock_bigquery_client.insert_rows_json.assert_called_once_with(
        "test-project.test_dataset.test_table", [expected_row]
    )

  def test_insert_video_analysis_with_errors(self, mock_bigquery_client):
    """Test that BigQueryError is raised on insertion errors."""
    bq_connector = analyze_video_lib.BigQueryConnector(
        table_id="test-project.test_dataset.test_table",
        bigquery_client=mock_bigquery_client,
    )
    mock_bigquery_client.insert_rows_json.return_value = [
        {"errors": "Test Error"}
    ]
    video = common.Video(
        uuid="1",
        source=common.Source.GCS,
        gcs_uri="gs://b/v.mp4",
        md5_hash="123",
    )

    with pytest.raises(analyze_video_lib.BigQueryError):
      bq_connector.insert_video_analysis(
          video, [], "test-embedding-model", "test-generative-model"
      )
