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
  mapToBackendSubmissionMetadata,
  mapVideo,
  mapVideoAnalysis,
  mapAdGroupInsertionStatus,
} from './mappers';

describe('Mappers Utils', () => {
  it('should map MatchedProduct correctly', () => {
    const input = {
      matched_product_offer_id: '123',
      matched_product_title: 'Test Product',
      matched_product_brand: 'Test Brand',
      matched_timestamp: '2023-01-01',
      distance: 0.5,
      candidate_status: {
        status: 'pending',
      },
    };

    const result = mapMatchedProduct(input);

    expect(result).toEqual({
      matchedProductOfferId: '123',
      matchedProductTitle: 'Test Product',
      matchedProductBrand: 'Test Brand',
      matchedProductLink: undefined,
      matchedProductImageLink: undefined,
      matchedProductAvailability: undefined,
      timestamp: '2023-01-01',
      distance: 0.5,
      status: 'pending',
    });
  });

  it('should map IdentifiedProduct correctly', () => {
    const input = {
      uuid: 'uuid-1',
      title: 'Identified Product',
      description: 'Desc',
      relevance_reasoning: 'Reason',
      video_timestamp: 1234,
      matched_products: [],
    };

    const result = mapIdentifiedProduct(input);

    expect(result).toEqual({
      productUuid: 'uuid-1',
      title: 'Identified Product',
      description: 'Desc',
      relevanceReasoning: 'Reason',
      videoTimestamp: 1234,
      matchedProducts: [],
    });
  });

  it('should map Video correctly', () => {
    const input = {
      uuid: 'vid-uuid-1',
      source: 'youtube',
      video_id: 'vid-1',
      gcs_uri: null,
      md5_hash: 'hash',
    };

    const result = mapVideo(input);

    expect(result).toEqual({
      uuid: 'vid-uuid-1',
      source: 'youtube',
      videoId: 'vid-1',
      gcsUri: null,
      md5Hash: 'hash',
      metadata: undefined,
    });
  });

  it('should map VideoAnalysis correctly', () => {
    const input = {
      video: {
        uuid: 'analysis-1',
        source: 'src',
        video_id: 'vid-1',
        gcs_uri: null,
        md5_hash: 'hash',
      },
      identified_products: [
        {
          uuid: 'uuid-1',
          title: 'Prod 1',
          description: 'Desc 1',
          relevance_reasoning: 'Reason 1',
          video_timestamp: 1234,
          matched_products: [
            {
              matched_product_offer_id: '123',
              matched_product_title: 'Test Product',
              matched_product_brand: 'Test Brand',
              matched_timestamp: '2023-01-01',
              distance: 0.5,
              candidate_status: {
                status: 'pending',
              },
            },
          ],
        },
      ],
    };

    const result = mapVideoAnalysis(input);

    expect(result.video.uuid).toBe('analysis-1');
    expect(result.video.source).toBe('src');
    expect(result.identifiedProducts.length).toBe(1);
    expect(result.identifiedProducts[0].productUuid).toBe('uuid-1');
    expect(result.identifiedProducts[0].matchedProducts.length).toBe(1);
    expect(
      result.identifiedProducts[0].matchedProducts[0].matchedProductOfferId
    ).toBe('123');
  });

  it('should map mapToBackendSubmissionMetadata correctly', () => {
    const input = {
      videoUuid: 'vid-1',
      offerIds: 'offer-1,offer-2',
      destinations: [
        {
          adGroupId: 'ad-group-1',
          campaignId: 'campaign-1',
          customerId: 'customer-1',
          adGroupName: 'Ad Group 1',
        },
      ],
      submittingUser: 'user@example.com',
      cpc: 1.52,
    };

    const result = mapToBackendSubmissionMetadata(input);

    expect(result).toEqual({
      video_uuid: 'vid-1',
      offer_ids: 'offer-1,offer-2',
      destinations: [
        {
          ad_group_id: 'ad-group-1',
          campaign_id: 'campaign-1',
          customer_id: 'customer-1',
          ad_group_name: 'Ad Group 1',
        },
      ],
      submitting_user: 'user@example.com',
      cpc: 1.52,
    });
  });

  it('should map AdGroupInsertionStatus correctly', () => {
    const input = {
      request_uuid: 'req-1',
      video_analysis_uuid: 'video-1',
      status: 'SUCCESS',
      ads_entities: [],
      timestamp: '2025-01-01T00:00:00Z',
    };

    const result = mapAdGroupInsertionStatus(input);

    expect(result).toEqual({
      requestUuid: 'req-1',
      videoAnalysisUuid: 'video-1',
      status: 'SUCCESS',
      adsEntities: [],
      timestamp: '2025-01-01T00:00:00Z',
    });
  });
});
