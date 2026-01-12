// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import {
  mapIdentifiedProduct,
  mapMatchedProduct,
  mapVideo,
  mapVideoAnalysis,
} from './mappers';

describe('Mappers Utils', () => {
  it('should map MatchedProduct correctly', () => {
    const input = {
      matched_product_offer_id: '123',
      matched_product_title: 'Test Product',
      matched_product_brand: 'Test Brand',
      timestamp: '2023-01-01',
      distance: 0.5,
      status: 'pending',
    };

    const result = mapMatchedProduct(input);

    expect(result).toEqual({
      matchedProductOfferId: '123',
      matchedProductTitle: 'Test Product',
      matchedProductBrand: 'Test Brand',
      timestamp: '2023-01-01',
      distance: 0.5,
      status: 'pending',
    });
  });

  it('should map IdentifiedProduct correctly', () => {
    const input = {
      title: 'Identified Product',
      description: 'Desc',
      relevance_reasoning: 'Reason',
      product_uuid: 'uuid-1',
      matched_products: [],
    };

    const result = mapIdentifiedProduct(input);

    expect(result).toEqual({
      title: 'Identified Product',
      description: 'Desc',
      relevanceReasoning: 'Reason',
      productUuid: 'uuid-1',
      matchedProducts: [],
    });
  });

  it('should map Video correctly', () => {
    const input = {
      video_location: 'youtube',
      video_id: 'vid-1',
      gcs_uri: null,
      md5_hash: 'hash',
    };

    const result = mapVideo(input);

    expect(result).toEqual({
      videoLocation: 'youtube',
      videoId: 'vid-1',
      gcsUri: null,
      md5Hash: 'hash',
    });
  });

  it('should map VideoAnalysis correctly', () => {
    const input = {
      video_analysis_uuid: 'analysis-1',
      source: 'src',
      video: {
        video_location: 'youtube',
        video_id: 'vid-1',
        gcs_uri: null,
        md5_hash: 'hash',
      },
      identified_products: [
        {
          title: 'Prod 1',
          description: 'Desc 1',
          relevance_reasoning: 'Reason 1',
          product_uuid: 'uuid-1',
          matched_products: [
            {
              matched_product_offer_id: '123',
              matched_product_title: 'Test Product',
              matched_product_brand: 'Test Brand',
              timestamp: '2023-01-01',
              distance: 0.5,
              status: 'pending',
            },
          ],
        },
      ],
    };

    const result = mapVideoAnalysis(input);

    expect(result.videoAnalysisUuid).toBe('analysis-1');
    expect(result.video.videoLocation).toBe('youtube');
    expect(result.identifiedProducts.length).toBe(1);
    expect(result.identifiedProducts[0].productUuid).toBe('uuid-1');
    expect(result.identifiedProducts[0].matchedProducts.length).toBe(1);
    expect(
      result.identifiedProducts[0].matchedProducts[0].matchedProductOfferId
    ).toBe('123');
  });
});
