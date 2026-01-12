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
  IdentifiedProduct,
  MatchedProduct,
  Video,
  VideoAnalysis,
} from '../models';

interface BackendMatchedProduct {
  matched_product_offer_id: string;
  matched_product_title: string;
  matched_product_brand: string;
  timestamp: string;
  distance: number;
  status: string;
}

/**
 * Maps a backend MatchedProduct (snake_case) to the frontend model (camelCase).
 */
export function mapMatchedProduct(data: BackendMatchedProduct): MatchedProduct {
  return {
    matchedProductOfferId: data.matched_product_offer_id,
    matchedProductTitle: data.matched_product_title,
    matchedProductBrand: data.matched_product_brand,
    timestamp: data.timestamp,
    distance: data.distance,
    status: data.status,
  };
}

interface BackendIdentifiedProduct {
  title: string;
  description: string;
  relevance_reasoning: string;
  product_uuid: string;
  matched_products: BackendMatchedProduct[];
}

/**
 * Maps a backend IdentifiedProduct (snake_case) to the frontend model (camelCase).
 */
export function mapIdentifiedProduct(
  data: BackendIdentifiedProduct
): IdentifiedProduct {
  return {
    title: data.title,
    description: data.description,
    relevanceReasoning: data.relevance_reasoning,
    productUuid: data.product_uuid,
    matchedProducts: (data.matched_products || []).map(mapMatchedProduct),
  };
}

interface BackendVideo {
  video_location: string;
  video_id: string | null;
  gcs_uri: string | null;
  md5_hash: string | null;
}

/**
 * Maps a backend Video (snake_case) to the frontend model (camelCase).
 */
export function mapVideo(data: BackendVideo): Video {
  return {
    videoLocation: data.video_location,
    videoId: data.video_id,
    gcsUri: data.gcs_uri,
    md5Hash: data.md5_hash,
  };
}

interface BackendVideoAnalysis {
  video_analysis_uuid: string;
  source: string;
  video: BackendVideo;
  identified_products: BackendIdentifiedProduct[];
}

/**
 * Maps a backend VideoAnalysis (snake_case) to the frontend model (camelCase).
 */
export function mapVideoAnalysis(data: BackendVideoAnalysis): VideoAnalysis {
  return {
    videoAnalysisUuid: data.video_analysis_uuid,
    source: data.source,
    video: mapVideo(data.video),
    identifiedProducts: (data.identified_products || []).map(
      mapIdentifiedProduct
    ),
  };
}
