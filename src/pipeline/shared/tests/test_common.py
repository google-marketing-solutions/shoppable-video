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

"""Unit tests for the common module."""

import datetime
import json
import os
from unittest import mock
import uuid
import pytest
from src.pipeline.shared import common


class TestProduct:
  """Unit tests for the Product class."""

  def test_to_json(self):
    """Tests that the to_json method returns a valid JSON string."""
    product = common.Product(
        offer_id='123',
        title='Test Product',
        brand='Test Brand',
        description='Test Description',
        product_type='Test Product Type',
        google_product_category='Test Google Product Category',
        age_group='Adult',
        color='Blue',
        gender='Male',
        material='Cotton',
        pattern='Solid',
    )
    product_json = product.to_json()
    assert isinstance(product_json, str)
    product_dict = json.loads(product_json)
    expected_product_dict = {
        'offer_id': '123',
        'title': 'Test Product',
        'brand': 'Test Brand',
        'description': 'Test Description',
        'product_type': 'Test Product Type',
        'google_product_category': 'Test Google Product Category',
        'age_group': 'Adult',
        'color': 'Blue',
        'gender': 'Male',
        'material': 'Cotton',
        'pattern': 'Solid',
    }
    assert product_dict == expected_product_dict

  def test_get_text_for_embedding_all_attributes(self):
    """Tests get_text_for_embedding with all attributes present."""
    product = common.Product(
        offer_id='123',
        title='Test Product',
        brand='Test Brand',
        description='Test Description',
        product_type='Test Product Type',
        google_product_category='Test Google Product Category',
        age_group='Adult',
        color='Blue',
        gender='Unisex',
        material='Cotton',
        pattern='Striped',
    )
    embedding_text = product.get_text_for_embedding()
    expected_text = (
        'Title: Test Product\n'
        'Brand: Test Brand\n'
        'Product Category: Test Google Product Category\n'
        'Product Type: Test Product Type\n'
        'Age Group: Adult\n'
        'Color: Blue\n'
        'Gender: Unisex\n'
        'Material: Cotton\n'
        'Pattern: Striped\n'
        'Description: Test Description'
    )
    assert embedding_text == expected_text

  def test_get_text_for_embedding_missing_attributes(self):
    """Tests get_text_for_embedding with some optional attributes missing."""
    product = common.Product(
        offer_id='123',
        title='Test Product',
        brand='Test Brand',
        description='Test Description',
        product_type='Test Product Type',
        google_product_category='Test Google Product Category',
        color='Red',
        pattern=None,  # Explicitly set to None
    )
    embedding_text = product.get_text_for_embedding()
    expected_text = (
        'Title: Test Product\n'
        'Brand: Test Brand\n'
        'Product Category: Test Google Product Category\n'
        'Product Type: Test Product Type\n'
        'Color: Red\n'
        'Description: Test Description'
    )
    assert embedding_text == expected_text

  def test_get_text_for_embedding_empty_string_attributes(self):
    """Tests get_text_for_embedding with empty strings for some attributes."""
    product = common.Product(
        offer_id='123',
        title='Test Product',
        brand='',  # Empty string
        description='Test Description',
        product_type='Test Product Type',
        google_product_category='Test Google Product Category',
    )
    embedding_text = product.get_text_for_embedding()
    expected_text = (
        'Title: Test Product\n'
        'Product Category: Test Google Product Category\n'
        'Product Type: Test Product Type\n'
        'Description: Test Description'
    )
    assert embedding_text == expected_text


class TestVideoMetadata:
  """Unit tests for the VideoMetadata class."""

  def test_init(self):
    """Tests that the VideoMetadata class can be initialized."""
    metadata = common.VideoMetadata(title='Test Title', description='Test Desc')
    assert metadata.title == 'Test Title'
    assert metadata.description == 'Test Desc'


class TestVideo:
  """Unit tests for the Video class."""

  def test_uuid_generation_from_video_id(self):
    """Tests that uuid is generated correctly from video_id."""
    video = common.Video(source=common.Source.GOOGLE_ADS, video_id='123')
    assert video.uuid == '123'

  def test_uuid_generation_from_gcs_uri_and_md5_hash(self):
    """Tests that uuid is generated correctly from gcs_uri and md5_hash."""
    gcs_uri = 'gs://test/test.mp4'
    md5_hash = 'abc'
    expected_uuid = str(
        uuid.uuid5(common.uuid.NAMESPACE_URL, f'{gcs_uri}{md5_hash}')
    )
    video = common.Video(
        source=common.Source.GCS, gcs_uri=gcs_uri, md5_hash=md5_hash
    )
    assert video.uuid == expected_uuid

  def test_post_init_validation_no_video_id_or_gcs_uri(self):
    """Tests __post_init__ raises error if no video_id or gcs_uri."""
    with pytest.raises(ValueError):
      common.Video(source=common.Source.GCS)

  def test_post_init_validation_only_gcs_uri_no_md5_hash(self):
    """Tests that __post_init__ requires md5_hash for GCS URIs."""
    with pytest.raises(ValueError):
      common.Video(source=common.Source.GCS, gcs_uri='gs://test/test.mp4')

  def test_to_json_with_gcs_uri(self):
    """Tests that to_json works correctly when initialized with a GCS URI."""
    gcs_uri = 'gs://test/test.mp4'
    md5_hash = 'abc'
    expected_uuid = str(
        uuid.uuid5(common.uuid.NAMESPACE_URL, gcs_uri + md5_hash)
    )
    video = common.Video(
        source=common.Source.GCS, gcs_uri=gcs_uri, md5_hash=md5_hash
    )
    video_json = video.to_json()
    assert isinstance(video_json, str)
    video_dict = json.loads(video_json)
    expected_video_dict = {
        'uuid': expected_uuid,
        'source': 'gcs',
        'video_id': None,
        'gcs_uri': 'gs://test/test.mp4',
        'md5_hash': 'abc',
        'metadata': None,
    }
    assert video_dict == expected_video_dict

  def test_to_json_with_video_id(self):
    """Tests that to_json works correctly when initialized with a video ID."""
    video = common.Video(source=common.Source.GOOGLE_ADS, video_id='123')
    video_json = video.to_json()
    assert isinstance(video_json, str)
    video_dict = json.loads(video_json)
    expected_video_dict = {
        'uuid': '123',
        'source': 'google_ads',
        'video_id': '123',
        'gcs_uri': None,
        'md5_hash': None,
        'metadata': None,
    }
    assert video_dict == expected_video_dict

  def test_to_json_with_metadata(self):
    """Tests that to_json includes metadata when present."""
    metadata = common.VideoMetadata(title='Test Title', description='Desc')
    video = common.Video(
        source=common.Source.MANUAL_ENTRY, video_id='123', metadata=metadata
    )
    video_json = video.to_json()
    video_dict = json.loads(video_json)
    expected_video_dict = {
        'uuid': '123',
        'source': 'manual_entry',
        'video_id': '123',
        'gcs_uri': None,
        'md5_hash': None,
        'metadata': {'title': 'Test Title', 'description': 'Desc'},
    }
    assert video_dict == expected_video_dict

  def test_get_resource_id_gcs_uri(self):
    """Tests that get_resource_id returns the GCS URI when present."""
    video = common.Video(
        source=common.Source.GCS, gcs_uri='gs://test/test.mp4', md5_hash='abc'
    )
    assert video.get_resource_id() == 'gs://test/test.mp4'

  def test_get_resource_id_video_id(self):
    """Tests that get_resource_id returns the video ID when GCS URI absent."""
    video = common.Video(source=common.Source.GOOGLE_ADS, video_id='123')
    assert video.get_resource_id() == '123'


class TestIdentifiedProduct:
  """Unit tests for the IdentifiedProduct class."""

  @mock.patch('uuid.uuid4', return_value='test-uuid')
  def test_to_dict_exclude_embedding(self, _):
    """Tests that the to_dict method returns a valid dictionary."""
    product = common.IdentifiedProduct(
        title='Test Product',
        description='Test Description',
        color_pattern_style_usage='Blue, striped, casual',
        category='Apparel',
        subcategory='Shirts',
        video_timestamp=datetime.timedelta(seconds=10),
        relevance_reasoning='It looks like a shirt.',
        embedding=[1.0, 2.0, 3.0],
    )
    product_dict = product.to_dict(exclude_embedding=True)
    expected_dict = {
        'title': 'Test Product',
        'description': 'Test Description',
        'color_pattern_style_usage': 'Blue, striped, casual',
        'category': 'Apparel',
        'subcategory': 'Shirts',
        'video_timestamp': 10000,
        'relevance_reasoning': 'It looks like a shirt.',
        'uuid': 'test-uuid',
    }
    assert product_dict == expected_dict

  @mock.patch('uuid.uuid4', return_value='test-uuid')
  def test_to_dict_include_embedding(self, _):
    """Tests that the to_dict method returns a valid dictionary."""
    product = common.IdentifiedProduct(
        title='Test Product',
        description='Test Description',
        color_pattern_style_usage='Blue, striped, casual',
        category='Apparel',
        subcategory='Shirts',
        video_timestamp=datetime.timedelta(seconds=10),
        relevance_reasoning='It looks like a shirt.',
        embedding=[1.0, 2.0, 3.0],
    )
    product_dict = product.to_dict(exclude_embedding=False)
    expected_dict = {
        'title': 'Test Product',
        'description': 'Test Description',
        'color_pattern_style_usage': 'Blue, striped, casual',
        'category': 'Apparel',
        'subcategory': 'Shirts',
        'video_timestamp': 10000,
        'relevance_reasoning': 'It looks like a shirt.',
        'embedding': [1.0, 2.0, 3.0],
        'uuid': 'test-uuid',
    }
    assert product_dict == expected_dict

  def test_get_text_for_embedding_all_attributes(self):
    """Tests get_text_for_embedding with all attributes present."""
    product = common.IdentifiedProduct(
        title='Test Product',
        description='Test Description',
        color_pattern_style_usage='Blue, striped, casual',
        category='Apparel',
        subcategory='Shirts',
        video_timestamp=datetime.timedelta(seconds=10),
        relevance_reasoning='It looks like a shirt.',
        embedding=None,
    )
    embedding_text = product.get_text_for_embedding()
    expected_text = (
        'Title: Test Product\n'
        'Description: Test Description\n'
        'Color, Pattern, Style, Usage: Blue, striped, casual\n'
        'Category: Apparel\n'
        'Subcategory: Shirts'
    )
    assert embedding_text == expected_text

  def test_get_text_for_embedding_missing_attributes(self):
    """Tests get_text_for_embedding with missing optional attributes."""
    product = common.IdentifiedProduct(
        title='Test Product',
        description='Test Description',
        color_pattern_style_usage='Blue, striped, casual',
        category='Apparel',
        subcategory=None,
        video_timestamp=datetime.timedelta(seconds=10),
        relevance_reasoning='It looks like a shirt.',
        embedding=None,
    )
    embedding_text = product.get_text_for_embedding()
    expected_text = (
        'Title: Test Product\n'
        'Description: Test Description\n'
        'Color, Pattern, Style, Usage: Blue, striped, casual\n'
        'Category: Apparel'
    )
    assert embedding_text == expected_text

  def test_get_text_for_embedding_all_falsy_attributes(self):
    """Tests get_text_for_embedding with all falsy attributes."""
    product = common.IdentifiedProduct(
        title='',
        description='',
        color_pattern_style_usage='',
        category='',
        subcategory=None,
        video_timestamp=datetime.timedelta(seconds=10),
        relevance_reasoning='It looks like a shirt.',
        embedding=None,
    )
    assert not product.get_text_for_embedding()


class TestModuleFunctions:
  """Unit tests for the module-level functions."""

  @mock.patch.dict(os.environ, {'TEST_VAR': 'test_value'})
  def test_get_env_var_set(self):
    """Tests that the get_env_var function returns the correct value."""
    assert common.get_env_var('TEST_VAR') == 'test_value'

  def test_get_env_var_not_set(self):
    with pytest.raises(ValueError):
      common.get_env_var('NON_EXISTENT_VAR')

  @pytest.mark.parametrize(
      'uri,expected',
      [
          ('gs://test-bucket/test/path.txt', ('test-bucket', 'test/path.txt')),
          ('test-bucket/test/path.txt', ('test-bucket', 'test/path.txt')),
      ],
  )
  def test_split_gcs_uri_valid(self, uri, expected):
    """Tests that the split_gcs_uri function splits the URI correctly."""
    assert common.split_gcs_uri(uri) == expected

  @pytest.mark.parametrize(
      'uri',
      [
          'not-a-gcs-uri',
          'test-bucket',
          'gs://test-bucket',
          'test-bucket/',
          'gs://test-bucket/',
      ],
  )
  def test_split_gcs_uri_invalid(self, uri):
    """Tests that the split_gcs_uri function raises error for invalid URIs."""
    with pytest.raises(ValueError):
      common.split_gcs_uri(uri)
