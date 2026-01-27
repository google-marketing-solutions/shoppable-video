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
"""Unit tests for the queue_videos_lib module."""

import base64
import json
import unittest
from unittest import mock
from google.auth import credentials
from google.cloud import bigquery
from google.cloud import storage
from google.cloud import tasks_v2
from src.pipeline.shared import common
from src.pipeline.video_inventory_analysis.queue_videos import queue_videos_lib


class TestVideoQueuer(unittest.TestCase):
  """Unit tests for the VideoQueuer class."""

  def setUp(self):
    """Set up mock clients and test data."""
    super().setUp()
    self.project_id = 'test_project'
    self.dataset_id = 'test_dataset'
    self.location = 'us-central1'
    self.queue_id = 'test_queue'
    self.customer_id = 'test_customer_id'
    self.spreadsheet_id = 'test_spreadsheet_id'
    self.cloud_function_url = 'https://test-function.url'
    # Mock clients that will be passed to the constructor
    self.mock_bigquery_client = mock.MagicMock(spec=bigquery.Client)
    self.mock_storage_client = mock.MagicMock(spec=storage.Client)
    self.mock_tasks_client = mock.MagicMock(spec=tasks_v2.CloudTasksClient)
    # The tasks client's queue_path method needs to return a string
    self.mock_tasks_client.queue_path.return_value = f'projects/{self.project_id}/locations/{self.location}/queues/{self.queue_id}'
    self.mock_auth = mock.patch(
        'google.auth.default',
        return_value=(
            mock.MagicMock(spec=credentials.Credentials),
            'test-project',
        ),
    ).start()
    self.mock_build = mock.patch('googleapiclient.discovery.build').start()

  def test_init_raises_error_on_no_ids(self):
    """Tests that a ValueError is raised when no customer_id or spreadsheet_id is provided."""
    with self.assertRaises(ValueError):
      queue_videos_lib.VideoQueuer(
          project_id=self.project_id,
          dataset_id=self.dataset_id,
          location=self.location,
          queue_id=self.queue_id,
      )

  @mock.patch.object(queue_videos_lib.VideoQueuer, '_get_processed_videos')
  @mock.patch.object(
      queue_videos_lib.VideoQueuer, '_get_videos_from_google_sheet'
  )
  @mock.patch.object(
      queue_videos_lib.VideoQueuer, '_get_videos_from_google_ads'
  )
  def test_get_videos(self, mock_get_ads, mock_get_sheet, mock_get_processed):
    """Tests that get_videos returns a unique, unprocessed, and limited list of videos."""
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
    )
    v_ads1 = common.Video(source=common.Source.GOOGLE_ADS, video_id='ads1')
    v_ads2_proc = common.Video(
        source=common.Source.GOOGLE_ADS, video_id='ads2_proc'
    )
    v_sheet1 = common.Video(
        source=common.Source.MANUAL_ENTRY, video_id='sheet1'
    )
    v_sheet2_dupe = common.Video(
        source=common.Source.MANUAL_ENTRY, video_id='ads1'
    )  # same id as v_ads1
    v_gcs1 = common.Video(
        source=common.Source.MANUAL_ENTRY,
        gcs_uri='gs://b/v1.mp4',
        md5_hash='h1',
    )
    v_gcs2_proc = common.Video(
        source=common.Source.MANUAL_ENTRY,
        gcs_uri='gs://b/v2_proc.mp4',
        md5_hash='h2',
    )
    mock_get_ads.return_value = [v_ads1, v_ads2_proc]
    mock_get_sheet.return_value = [v_sheet1, v_sheet2_dupe, v_gcs1, v_gcs2_proc]
    mock_get_processed.return_value = (['ads2_proc'], ['gs://b/v2_proc.mp4'])
    videos = queuer.get_videos(video_limit=2)
    video_uuids = {v.uuid for v in videos}
    self.assertEqual(len(videos), 2)
    self.assertIn(v_sheet1.uuid, video_uuids)
    self.assertIn(v_ads1.uuid, video_uuids)
    self.assertNotIn(v_ads2_proc.uuid, video_uuids)
    self.assertNotIn(v_gcs2_proc.uuid, video_uuids)

  @mock.patch.object(queue_videos_lib.VideoQueuer, '_get_processed_videos')
  @mock.patch.object(
      queue_videos_lib.VideoQueuer, '_get_videos_from_google_sheet'
  )
  @mock.patch.object(
      queue_videos_lib.VideoQueuer, '_get_videos_from_google_ads'
  )
  @mock.patch.object(queue_videos_lib.VideoQueuer, '_get_youtube_video_info')
  def test_get_videos_filters_non_public_youtube_videos(
      self,
      mock_get_info,
      mock_get_ads,
      mock_get_sheet,
      mock_get_processed,
  ):
    """Tests that get_videos filters out non-public YouTube videos."""
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
    )
    v_public = common.Video(
        source=common.Source.MANUAL_ENTRY, video_id='public_video'
    )
    v_private = common.Video(
        source=common.Source.MANUAL_ENTRY, video_id='private_video'
    )
    mock_get_ads.return_value = []
    mock_get_sheet.return_value = [v_public, v_private]
    mock_get_processed.return_value = ([], [])
    mock_get_info.return_value = {
        'public_video': ('public', 'Public Title'),
        'private_video': ('unlisted', 'Private Title'),
    }
    videos = queuer.get_videos(video_limit=10)
    self.assertEqual(len(videos), 1)
    self.assertEqual(videos[0].video_id, 'public_video')
    self.assertEqual(videos[0].metadata.title, 'Public Title')  # type: ignore

  def test_push_videos(self):
    """Tests that videos are correctly formatted and pushed to the Cloud Tasks queue."""
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
    )
    video1 = common.Video(source=common.Source.GOOGLE_ADS, video_id='vid1')
    video2 = common.Video(
        source=common.Source.MANUAL_ENTRY,
        gcs_uri='gs://b/v2.mp4',
        md5_hash='h2',
    )
    queuer.push_videos([video1, video2], self.cloud_function_url)
    self.assertEqual(self.mock_tasks_client.create_task.call_count, 2)
    expected_calls = []
    for video in [video1, video2]:
      payload = {'video': common.dataclasses.asdict(video)}
      task = tasks_v2.Task(
          http_request=tasks_v2.HttpRequest(
              http_method=tasks_v2.HttpMethod.POST,
              url=self.cloud_function_url,
              body=json.dumps(payload).encode('utf-8'),
              headers={'Content-type': 'application/json'},
          )
      )
      # The parent queue path is mocked in setUp
      request = tasks_v2.CreateTaskRequest(
          parent=self.mock_tasks_client.queue_path.return_value, task=task
      )
      expected_calls.append(mock.call(request))
    self.mock_tasks_client.create_task.assert_has_calls(
        expected_calls, any_order=True
    )

  def test_is_queue_empty(self):
    """Tests the queue emptiness check."""
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
    )
    self.mock_tasks_client.list_tasks.return_value = mock.MagicMock(tasks=[])
    self.assertTrue(queuer.is_queue_empty())
    self.mock_tasks_client.list_tasks.assert_called_once_with(
        request=tasks_v2.ListTasksRequest(parent=queuer.parent_queue)
    )
    self.mock_tasks_client.reset_mock()
    self.mock_tasks_client.list_tasks.return_value = mock.MagicMock(
        tasks=[mock.MagicMock()]
    )
    self.assertFalse(queuer.is_queue_empty())

  def test_get_videos_from_google_ads_success(self):
    """Tests successful retrieval of video IDs from Google Ads via BigQuery."""
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
    )
    mock_row = mock.MagicMock()
    mock_row.video_id = 'ad_vid_1'
    self.mock_bigquery_client.query.return_value.result.return_value = [
        mock_row
    ]
    videos = queuer._get_videos_from_google_ads()  # pylint: disable=protected-access
    self.assertEqual(len(videos), 1)
    self.assertEqual(videos[0].video_id, 'ad_vid_1')
    self.assertEqual(videos[0].source, common.Source.GOOGLE_ADS)
    self.mock_bigquery_client.query.assert_called_once()

  def test_get_videos_from_google_ads_raises_error(self):
    """Tests that BigQueryReadError is raised on query failure."""
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
    )
    self.mock_bigquery_client.query.side_effect = Exception('BQ Error')
    with self.assertRaises(queue_videos_lib.BigQueryReadError):
      queuer._get_videos_from_google_ads()  # pylint: disable=protected-access

  @mock.patch.object(
      queue_videos_lib.VideoQueuer, '_get_youtube_ids_from_sheet'
  )
  @mock.patch.object(queue_videos_lib.VideoQueuer, '_get_gcs_uris_from_sheet')
  @mock.patch.object(queue_videos_lib.VideoQueuer, '_process_gcs_uri')
  def test_get_videos_from_google_sheet(
      self, mock_process_gcs, mock_get_gcs, mock_get_yt
  ):
    """Tests aggregation of videos from different sheets."""
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
    )
    mock_get_yt.return_value = [
        common.Video(source=common.Source.MANUAL_ENTRY, video_id='yt1')
    ]
    mock_get_gcs.return_value = ['gs://b/folder/']
    mock_process_gcs.return_value = [
        common.Video(
            source=common.Source.MANUAL_ENTRY,
            gcs_uri='gs://b/v1.mp4',
            md5_hash='h1',
        )
    ]
    videos = queuer._get_videos_from_google_sheet()  # pylint: disable=protected-access
    self.assertEqual(len(videos), 2)
    mock_process_gcs.assert_called_once_with('gs://b/folder/')

  def test_process_gcs_uri(self):
    """Tests processing of a GCS URI into Video objects."""
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
    )
    mock_blob = mock.MagicMock(spec=storage.Blob)
    mock_blob.name = 'folder/video.mp4'
    # The blob's md5_hash is a base64 encoded string.
    # The library decodes it and then hex encodes it.
    raw_hash_bytes = b'test hash bytes'
    mock_blob.md5_hash = base64.b64encode(raw_hash_bytes).decode('utf-8')
    mock_blob.reload = mock.MagicMock()  # Mock the reload call
    self.mock_storage_client.list_blobs.return_value = [mock_blob]
    videos = queuer._process_gcs_uri('gs://test-bucket/folder/')  # pylint: disable=protected-access
    self.assertEqual(len(videos), 1)
    video = videos[0]
    self.assertEqual(video.gcs_uri, 'gs://test-bucket/folder/video.mp4')
    self.assertEqual(video.md5_hash, raw_hash_bytes.hex())
    self.assertEqual(video.metadata.title, 'video.mp4')  # type: ignore
    mock_blob.reload.assert_called_once()

  def test_get_processed_videos(self):
    """Tests retrieval of processed video identifiers from BigQuery."""
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
    )
    mock_rows = [
        mock.MagicMock(video_id='vid1', gcs_uri=None),
        mock.MagicMock(video_id=None, gcs_uri='gs://b/v2.mp4'),
    ]
    self.mock_bigquery_client.query.return_value.result.return_value = mock_rows
    video_ids, gcs_uris = queuer._get_processed_videos()  # pylint: disable=protected-access
    self.assertEqual(video_ids, ['vid1'])
    self.assertEqual(gcs_uris, ['gs://b/v2.mp4'])

  def test_get_youtube_video_info(self):
    """Tests that video info (status and title) are correctly retrieved."""
    video_ids = ['vid1', 'vid2', 'vid3']
    mock_response = {
        'items': [
            {
                'id': 'vid1',
                'status': {'privacyStatus': 'public'},
                'snippet': {'title': 'Title 1'},
            },
            {
                'id': 'vid2',
                'status': {'privacyStatus': 'private'},
                'snippet': {'title': 'Title 2'},
            },
            {
                'id': 'vid3',
                'status': {'privacyStatus': 'unlisted'},
                'snippet': {'title': 'Title 3'},
            },
        ]
    }
    mock_youtube_service = mock.MagicMock()
    mock_youtube_service.videos.return_value.list.return_value.execute.return_value = (
        mock_response
    )
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
        youtube_service=mock_youtube_service,
    )
    info = queuer._get_youtube_video_info(video_ids)  # pylint: disable=protected-access
    self.assertEqual(
        info,
        {
            'vid1': ('public', 'Title 1'),
            'vid2': ('private', 'Title 2'),
            'vid3': ('unlisted', 'Title 3'),
        },
    )
    mock_youtube_service.videos.return_value.list.assert_called_once_with(
        part='status,snippet', id='vid1,vid2,vid3'
    )

  def test_get_youtube_video_info_with_chunking(self):
    """Tests that video info requests are chunked correctly."""
    video_ids = [f'vid{i}' for i in range(52)]
    mock_response_1 = {
        'items': [
            {
                'id': f'vid{i}',
                'status': {'privacyStatus': 'public'},
                'snippet': {'title': f'Title {i}'},
            }
            for i in range(50)
        ]
    }
    mock_response_2 = {
        'items': [
            {
                'id': 'vid50',
                'status': {'privacyStatus': 'private'},
                'snippet': {'title': 'Title 50'},
            },
            {
                'id': 'vid51',
                'status': {'privacyStatus': 'unlisted'},
                'snippet': {'title': 'Title 51'},
            },
        ]
    }
    mock_youtube_service = mock.MagicMock()
    (
        mock_youtube_service.videos.return_value.list.return_value.execute.side_effect
    ) = [mock_response_1, mock_response_2]
    queuer = queue_videos_lib.VideoQueuer(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        location=self.location,
        queue_id=self.queue_id,
        customer_id=self.customer_id,
        spreadsheet_id=self.spreadsheet_id,
        bigquery_client=self.mock_bigquery_client,
        storage_client=self.mock_storage_client,
        tasks_client=self.mock_tasks_client,
        youtube_service=mock_youtube_service,
    )
    info = queuer._get_youtube_video_info(video_ids)  # pylint: disable=protected-access
    self.assertEqual(len(info), 52)
    self.assertEqual(info['vid0'], ('public', 'Title 0'))
    self.assertEqual(info['vid50'], ('private', 'Title 50'))
    self.assertEqual(info['vid51'], ('unlisted', 'Title 51'))
    self.assertEqual(
        mock_youtube_service.videos.return_value.list.call_count, 2
    )


if __name__ == '__main__':
  unittest.main()
