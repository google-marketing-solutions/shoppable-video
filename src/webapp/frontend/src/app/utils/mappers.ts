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
  CandidateStatus,
  Status,
} from '../models';

/**
 * Represents a matched product object from the backend, typically with snake_case keys.
 */
export interface BackendMatchedProduct {
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

/**
 * Represents a product identified from the backend, typically with snake_case keys.
 */
export interface BackendIdentifiedProduct {
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

/**
 * Represents a video object from the backend, typically with snake_case keys.
 */
export interface BackendVideo {
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

/**
 * Represents a video analysis object from the backend, typically with snake_case keys.
 */
export interface BackendVideoAnalysis {
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

/**
 * Represents a candidate status object from the backend, typically with snake_case keys.
 */
export interface BackendCandidateStatus {
  video_analysis_uuid: string;
  candidate_offer_id: string;
  status: string;
  timestamp: string;
}

/**
 * Maps a backend CandidateStatus (snake_case) to the frontend model (camelCase).
 */
export function mapCandidateStatus(
  data: BackendCandidateStatus
): CandidateStatus {
  return {
    videoAnalysisUuid: data.video_analysis_uuid,
    candidateOfferId: data.candidate_offer_id,
    status: data.status as Status, // Cast to Status enum if needed
    timestamp: data.timestamp,
  };
}

/**
 * Maps a frontend CandidateStatus (camelCase) to the backend model (snake_case).
 */
export function mapToBackendCandidateStatus(
  data: CandidateStatus
): BackendCandidateStatus {
  return {
    video_analysis_uuid: data.videoAnalysisUuid,
    candidate_offer_id: data.candidateOfferId,
    status: data.status,
    timestamp: data.timestamp,
  };
}
