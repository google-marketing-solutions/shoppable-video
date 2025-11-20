# Copyright 2025 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the common module."""

import datetime
import json
import os
import unittest
from unittest import mock

from src.shared import common


class TestProduct(unittest.TestCase):
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
    self.assertIsInstance(product_json, str)
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
    self.assertDictEqual(product_dict, expected_product_dict)

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
    self.assertEqual(embedding_text, expected_text)

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
    self.assertEqual(embedding_text, expected_text)

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
    self.assertEqual(embedding_text, expected_text)


class TestVideo(unittest.TestCase):
  """Unit tests for the Video class."""

  def test_post_init_validation(self):
    """Tests that __post_init__ raises an error for invalid arguments."""
    with self.subTest(msg='Both video_id and gcs_uri are None'):
      with self.assertRaises(ValueError):
        common.Video(source=common.Source.GCS)

    with self.subTest(msg='Both video_id and gcs_uri are provided'):
      with self.assertRaises(ValueError):
        common.Video(
            source=common.Source.GCS,
            video_id='123',
            gcs_uri='gs://test/test.mp4',
        )

  def test_to_json(self):
    """Tests that the to_json method returns a valid JSON string."""
    # Test case 1: Video with GCS URI
    with self.subTest(msg='Video with GCS URI'):
      video = common.Video(
          source=common.Source.GCS, gcs_uri='gs://test/test.mp4', md5_hash='abc'
      )
      video_json = video.to_json()
      self.assertIsInstance(video_json, str)
      video_dict = json.loads(video_json)
      expected_video_dict = {
          'source': 'gcs',
          'video_id': None,
          'gcs_uri': 'gs://test/test.mp4',
          'md5_hash': 'abc',
      }
      self.assertDictEqual(video_dict, expected_video_dict)

    # Test case 2: Video with video ID
    with self.subTest(msg='Video with video ID'):
      video = common.Video(
          source=common.Source.GOOGLE_ADS, video_id='123', md5_hash='def'
      )
      video_json = video.to_json()
      self.assertIsInstance(video_json, str)
      video_dict = json.loads(video_json)
      expected_video_dict = {
          'source': 'google_ads',
          'video_id': '123',
          'gcs_uri': None,
          'md5_hash': 'def',
      }
      self.assertDictEqual(video_dict, expected_video_dict)

    # Test case 3: Video with md5_hash as None
    with self.subTest(msg='Video with md5_hash as None'):
      video = common.Video(
          source=common.Source.GCS, gcs_uri='gs://test/test.mp4', md5_hash=None
      )
      video_json = video.to_json()
      self.assertIsInstance(video_json, str)
      video_dict = json.loads(video_json)
      expected_video_dict = {
          'source': 'gcs',
          'video_id': None,
          'gcs_uri': 'gs://test/test.mp4',
          'md5_hash': None,
      }
      self.assertDictEqual(video_dict, expected_video_dict)

  def test_get_resource_id(self):
    """Tests that the get_resource_id method returns the correct ID."""
    with self.subTest(msg='GCS URI'):
      video = common.Video(
          source=common.Source.GCS, gcs_uri='gs://test/test.mp4'
      )
      self.assertEqual(video.get_resource_id(), 'gs://test/test.mp4')
    with self.subTest(msg='Video ID'):
      video = common.Video(source=common.Source.GOOGLE_ADS, video_id='123')
      self.assertEqual(video.get_resource_id(), '123')


class TestIdentifiedProduct(unittest.TestCase):
  """Unit tests for the IdentifiedProduct class."""

  def test_to_dict(self):
    """Tests that the to_dict method returns a valid dictionary."""
    with mock.patch('uuid.uuid4', return_value='test-uuid'):
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

    with self.subTest(msg='exclude_embedding=True'):
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
      self.assertDictEqual(product_dict, expected_dict)

    with self.subTest(msg='exclude_embedding=False'):
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
      self.assertDictEqual(product_dict, expected_dict)

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
    self.assertEqual(embedding_text, expected_text)

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
    self.assertEqual(embedding_text, expected_text)

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
    self.assertEqual(product.get_text_for_embedding(), '')


class TestModuleFunctions(unittest.TestCase):
  """Unit tests for the module-level functions."""

  @mock.patch.dict(os.environ, {'TEST_VAR': 'test_value'})
  def test_get_env_var(self):
    """Tests that the get_env_var function returns the correct value."""
    with self.subTest(msg='Variable is set'):
      self.assertEqual(common.get_env_var('TEST_VAR'), 'test_value')
    with self.subTest(msg='Variable is not set'):
      with self.assertRaises(ValueError):
        common.get_env_var('NON_EXISTENT_VAR')

  def test_split_gcs_uri(self):
    """Tests that the split_gcs_uri function splits the URI correctly."""
    test_cases = {
        'Standard URI with gs:// prefix': (
            'gs://test-bucket/test/path.txt',
            ('test-bucket', 'test/path.txt'),
        ),
        'URI without gs:// prefix': (
            'test-bucket/test/path.txt',
            ('test-bucket', 'test/path.txt'),
        ),
    }

    for test_name, (uri, expected) in test_cases.items():
      with self.subTest(msg=test_name):
        self.assertEqual(common.split_gcs_uri(uri), expected)

    invalid_test_cases = {
        'Completely invalid URI': 'not-a-gcs-uri',
        'URI with only a bucket (no path) and no prefix': 'test-bucket',
        'URI with only a bucket (no path) and with prefix': 'gs://test-bucket',
        'URI with a bucket and empty path (trailing slash) and no prefix': (
            'test-bucket/'
        ),
        'URI with a bucket and empty path (trailing slash) and with prefix': (
            'gs://test-bucket/'
        ),
    }

    for test_name, uri in invalid_test_cases.items():
      with self.subTest(msg=test_name):
        with self.assertRaises(ValueError):
          common.split_gcs_uri(uri)


if __name__ == '__main__':
  unittest.main()
