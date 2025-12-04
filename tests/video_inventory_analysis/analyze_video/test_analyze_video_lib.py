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
import unittest
from unittest import mock

from google import genai
from google.cloud import bigquery
from google.cloud import storage
from google.genai import types
from src.pipeline.shared import common
from src.pipeline.video_inventory_analysis.analyze_video import analyze_video_lib


class VideoAnalyzerTest(unittest.TestCase):
  """Test suite for the VideoAnalyzer class."""

  def setUp(self):
    """Set up the test environment before each test."""
    super().setUp()
    self.mock_storage_client = mock.MagicMock(spec=storage.Client)
    self.mock_genai_client = mock.MagicMock(spec=genai.Client)
    self.video_analyzer = analyze_video_lib.VideoAnalyzer(
        prompt="test prompt",
        generative_model_name="gemini-pro",
        storage_client=self.mock_storage_client,
        genai_client=self.mock_genai_client,
    )

  def test_video_analyzer_init(self):
    """Test the initialization of the VideoAnalyzer class."""
    # Test with custom clients provided
    analyzer_with_clients = analyze_video_lib.VideoAnalyzer(
        prompt="custom prompt",
        generative_model_name="custom-model",
        storage_client=self.mock_storage_client,
        genai_client=self.mock_genai_client,
    )
    self.assertEqual(analyzer_with_clients.prompt.text, "custom prompt")
    self.assertEqual(
        analyzer_with_clients.generative_model_name, "custom-model"
    )
    self.assertIs(
        analyzer_with_clients.storage_client, self.mock_storage_client
    )
    self.assertIs(analyzer_with_clients.genai_client, self.mock_genai_client)

    # Test with default clients
    with (
        mock.patch("google.cloud.storage.Client") as mock_storage_client_class,
        mock.patch("google.genai.Client") as mock_genai_client_class,
    ):
      mock_default_storage = mock.MagicMock()
      mock_default_genai = mock.MagicMock()
      mock_storage_client_class.return_value = mock_default_storage
      mock_genai_client_class.return_value = mock_default_genai

      analyzer_defaults = analyze_video_lib.VideoAnalyzer(
          prompt="default prompt", generative_model_name="default-model"
      )

      mock_storage_client_class.assert_called_once()
      mock_genai_client_class.assert_called_once()
      self.assertEqual(analyzer_defaults.prompt.text, "default prompt")
      self.assertEqual(analyzer_defaults.generative_model_name, "default-model")
      self.assertIs(analyzer_defaults.storage_client, mock_default_storage)
      self.assertIs(analyzer_defaults.genai_client, mock_default_genai)

  @mock.patch.object(analyze_video_lib.VideoAnalyzer, "_upload_video_from_gcs")
  def test_analyze_video_with_gcs_uri(self, mock_upload_video):
    """Test analyzing a video from a GCS URI."""
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
    self.mock_genai_client.models.generate_content.return_value = mock_response

    video = common.Video(
        uuid="1",
        source=common.Source.GCS,
        gcs_uri="gs://bucket/video.mp4",
        md5_hash="1234",
    )
    products = self.video_analyzer.analyze_video(video)

    mock_upload_video.assert_called_once_with(gcs_uri="gs://bucket/video.mp4")
    self.mock_genai_client.models.generate_content.assert_called_once_with(
        model="gemini-pro",
        contents=[mock_file, types.Part(text="test prompt")],
        config=self.video_analyzer.genai_config,
    )
    self.mock_genai_client.files.delete.assert_called_once_with(
        name="uploaded_video"
    )
    self.assertEqual(products, [mock_product])

  def test_analyze_video_with_youtube_url(self):
    """Test analyzing a video from a YouTube URL."""
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
    self.mock_genai_client.models.generate_content.return_value = mock_response

    video = common.Video(
        uuid="2", source=common.Source.MANUAL_ENTRY, video_id="youtube123"
    )
    products = self.video_analyzer.analyze_video(video)

    self.mock_genai_client.models.generate_content.assert_called_once_with(
        model="gemini-pro",
        contents=[
            types.Part(
                file_data=types.FileData(
                    file_uri="https://www.youtube.com/watch?v=youtube123"
                )
            ),
            types.Part(text="test prompt"),
        ],
        config=self.video_analyzer.genai_config,
    )
    self.mock_genai_client.files.delete.assert_not_called()
    self.assertEqual(products, [mock_product])

  def test_analyze_video_raises_generative_ai_error(self):
    """Test that GenerativeAIError is raised on API error."""
    self.mock_genai_client.models.generate_content.side_effect = Exception(
        "API Error"
    )
    video = common.Video(
        uuid="3", source=common.Source.MANUAL_ENTRY, video_id="youtube_error"
    )
    with self.assertRaises(analyze_video_lib.GenerativeAIError):
      self.video_analyzer.analyze_video(video)

  @mock.patch.object(
      analyze_video_lib.VideoAnalyzer, "_wait_for_video_processing"
  )
  def test_upload_video_from_gcs(self, mock_wait):
    """Test uploading a video from GCS."""
    mock_blob = mock.MagicMock()
    mock_blob_file = mock.MagicMock()
    mock_blob.open.return_value.__enter__.return_value = mock_blob_file
    self.mock_storage_client.bucket.return_value.blob.return_value = mock_blob

    mock_uploaded_file = types.File(name="test_file")
    self.mock_genai_client.files.upload.return_value = mock_uploaded_file
    mock_wait.return_value = mock_uploaded_file

    returned_file = self.video_analyzer._upload_video_from_gcs(  # pylint: disable=protected-access
        "gs://bucket/video.mp4"
    )

    self.mock_storage_client.bucket.assert_called_with("bucket")
    self.mock_storage_client.bucket.return_value.blob.assert_called_with(
        "video.mp4"
    )
    self.mock_genai_client.files.upload.assert_called_once_with(
        file=mock_blob_file, config={"mime_type": "video/mp4"}
    )
    mock_wait.assert_called_once_with("test_file", "gs://bucket/video.mp4")
    self.assertIs(returned_file, mock_uploaded_file)

  def test_wait_for_video_processing_active(self):
    """Test waiting for an active video to finish processing."""
    mock_file = types.File(name="active_file", state=types.FileState.ACTIVE)
    self.mock_genai_client.files.get.return_value = mock_file

    result = self.video_analyzer._wait_for_video_processing(  # pylint: disable=protected-access
        "active_file", "gs://b/v.mp4"
    )
    self.assertEqual(result, mock_file)
    self.mock_genai_client.files.get.assert_called_once_with(name="active_file")

  def test_wait_for_video_processing_retries(self):
    """Test the retry mechanism for video processing."""
    processing_file = types.File(
        name="processing_file", state=types.FileState.PROCESSING
    )
    active_file = types.File(
        name="processing_file", state=types.FileState.ACTIVE
    )
    self.mock_genai_client.files.get.side_effect = [
        processing_file,
        active_file,
    ]
    with mock.patch("tenacity.nap.time.sleep", return_value=None):
      result = self.video_analyzer._wait_for_video_processing(  # pylint: disable=protected-access
          "processing_file", "gs://b/v.mp4"
      )

    self.assertEqual(result, active_file)
    self.assertEqual(self.mock_genai_client.files.get.call_count, 2)


class BigQueryConnectorTest(unittest.TestCase):
  """Test suite for the BigQueryConnector class."""

  def setUp(self):
    """Set up the test environment before each test."""
    super().setUp()
    self.mock_bigquery_client = mock.MagicMock(spec=bigquery.Client)
    self.bq_connector = analyze_video_lib.BigQueryConnector(
        table_id="test-project.test_dataset.test_table",
        bigquery_client=self.mock_bigquery_client,
    )

  def test_insert_video_analysis(self):
    """Test inserting a successful video analysis into BigQuery."""
    self.mock_bigquery_client.insert_rows_json.return_value = []
    video = common.Video(
        uuid="1",
        source=common.Source.GCS,
        gcs_uri="gs://b/v.mp4",
        md5_hash="4321",
    )
    product = common.IdentifiedProduct(
        uuid="prod_uuid",
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

    self.bq_connector.insert_video_analysis(video, products)

    expected_row = {
        "uuid": "1",
        "source": "gcs",
        "video_id": None,
        "gcs_uri": "gs://b/v.mp4",
        "md5_hash": "4321",
        "status": "SUCCESS",
        "error_message": None,
        "identified_products": [product.to_dict()],
    }
    self.mock_bigquery_client.insert_rows_json.assert_called_once_with(
        "test-project.test_dataset.test_table", [expected_row]
    )

  def test_insert_video_analysis_with_errors(self):
    """Test that BigQueryError is raised on insertion errors."""
    self.mock_bigquery_client.insert_rows_json.return_value = [
        {"errors": "Test Error"}
    ]
    video = common.Video(
        uuid="1",
        source=common.Source.GCS,
        gcs_uri="gs://b/v.mp4",
        md5_hash="123",
    )

    with self.assertRaises(analyze_video_lib.BigQueryError):
      self.bq_connector.insert_video_analysis(video, [])


if __name__ == "__main__":
  unittest.main()
