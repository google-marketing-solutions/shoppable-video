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
  Candidate,
  CandidateStatus,
  IdentifiedProduct,
  MatchedProduct,
  Video,
  VideoAnalysis,
  VideoAnalysisSummary,
  Destination,
  SubmissionMetadata,
} from '../models';

/**
 * Represents a matched product object from the backend, typically with snake_case keys.
 */
export interface BackendMatchedProduct {
  matched_product_offer_id: string;
  matched_product_title: string;
  matched_product_brand: string;
  matched_product_link?: string;
  matched_product_image_link?: string;
  matched_product_availability?: string;
  matched_timestamp: string;
  distance: number;
  candidate_status: BackendCandidateStatus;
}

/**
 * Maps a backend MatchedProduct (snake_case) to the frontend model (camelCase).
 */
export function mapMatchedProduct(data: BackendMatchedProduct): MatchedProduct {
  return {
    matchedProductOfferId: data.matched_product_offer_id,
    matchedProductTitle: data.matched_product_title,
    matchedProductBrand: data.matched_product_brand,
    matchedProductLink: data.matched_product_link,
    matchedProductImageLink: data.matched_product_image_link,
    matchedProductAvailability: data.matched_product_availability,
    timestamp: data.matched_timestamp,
    distance: data.distance,
    status: data.candidate_status?.status || 'UNREVIEWED',
  };
}

/**
 * Represents a product identified from the backend, typically with snake_case keys.
 */
export interface BackendIdentifiedProduct {
  uuid: string;
  title: string;
  description: string;
  relevance_reasoning: string;
  video_timestamp: number;
  matched_products: BackendMatchedProduct[];
}

/**
 * Maps a backend IdentifiedProduct (snake_case) to the frontend model (camelCase).
 */
export function mapIdentifiedProduct(
  data: BackendIdentifiedProduct
): IdentifiedProduct {
  return {
    productUuid: data.uuid,
    title: data.title,
    description: data.description,
    relevanceReasoning: data.relevance_reasoning,
    videoTimestamp: data.video_timestamp,
    matchedProducts: (data.matched_products || []).map(mapMatchedProduct),
  };
}

/**
 * Represents metadata for a video from the backend.
 */
export interface BackendVideoMetadata {
  title?: string | null;
  description?: string | null;
}

/**
 * Represents a video object from the backend, typically with snake_case keys.
 */
export interface BackendVideo {
  uuid: string;
  source: string;
  video_id: string | null;
  gcs_uri: string | null;
  md5_hash: string | null;
  metadata?: BackendVideoMetadata | null;
}

/**
 * Maps a backend Video (snake_case) to the frontend model (camelCase).
 */
export function mapVideo(data: BackendVideo): Video {
  return {
    uuid: data.uuid,
    source: data.source,
    videoId: data.video_id,
    gcsUri: data.gcs_uri,
    md5Hash: data.md5_hash,
    metadata: data.metadata,
  };
}

/**
 * Represents a video analysis summary object from the backend.
 */
export interface BackendVideoAnalysisSummary {
  video: BackendVideo;
  identified_products_count: number;
  matched_products_count: number;
  approved_products_count: number;
  disapproved_products_count: number;
  unreviewed_products_count: number;
}

/**
 * Represents a paginated video analysis summary response from the backend.
 */
export interface BackendPaginatedVideoAnalysisSummary {
  items: BackendVideoAnalysisSummary[];
  total_count: number;
  limit: number;
  offset: number;
}

/**
 * Maps a backend VideoAnalysisSummary (snake_case) to the frontend model (camelCase).
 */
export function mapVideoAnalysisSummary(
  data: BackendVideoAnalysisSummary
): VideoAnalysisSummary {
  return {
    video: mapVideo(data.video),
    identifiedProductsCount: data.identified_products_count,
    matchedProductsCount: data.matched_products_count,
    approvedProductsCount: data.approved_products_count,
    disapprovedProductsCount: data.disapproved_products_count,
    unreviewedProductsCount: data.unreviewed_products_count,
  };
}

/**
 * Represents a video analysis object from the backend, typically with snake_case keys.
 */
export interface BackendVideoAnalysis {
  video: BackendVideo;
  identified_products: BackendIdentifiedProduct[];
}

/**
 * Maps a backend VideoAnalysis (snake_case) to the frontend model (camelCase).
 */
export function mapVideoAnalysis(data: BackendVideoAnalysis): VideoAnalysis {
  return {
    video: mapVideo(data.video),
    identifiedProducts: (data.identified_products || []).map(
      mapIdentifiedProduct
    ),
  };
}

/**
 * Represents a Destination object from the backend, used within submission metadata.
 * These typically contain identifiers for ad campaigns.
 */
export interface BackendDestination {
  ad_group_id: string;
  campaign_id: string;
  customer_id: string;
  ad_group_name?: string;
}

/**
 * Represents the submission metadata for a candidate status from the backend,
 * typically with snake_case keys. This provides details about why a specific
 * candidate was approved or disapproved.
 */
export interface BackendSubmissionMetadata {
  video_uuid?: string;
  offer_ids?: string;
  destinations?: BackendDestination[];
  submitting_user?: string;
  cpc?: number;
}

/**
 * Represents a candidate status object from the backend.
 */
export interface BackendCandidateStatus {
  status: string;
  user?: string | null;
  is_added_by_user?: boolean | null;
  modified_timestamp?: string | null;
  submission_metadata?: BackendSubmissionMetadata;
}

/**
 * Represents a candidate object from the backend.
 */
export interface BackendCandidate {
  video_analysis_uuid: string;
  identified_product_uuid: string;
  candidate_offer_id: string;
  candidate_status: BackendCandidateStatus;
}

/**
 * Maps a frontend Destination (camelCase) to the backend model (snake_case).
 */
export function mapToBackendDestination(data: Destination): BackendDestination {
  return {
    ad_group_id: data.adGroupId,
    campaign_id: data.campaignId,
    customer_id: data.customerId,
    ad_group_name: data.adGroupName,
  };
}

/**
 * Maps a frontend CandidateStatus (camelCase) to the backend model (snake_case).
 */
export function mapToBackendCandidateStatus(
  data: CandidateStatus
): BackendCandidateStatus {
  return {
    status: data.status,
    user: data.user,
    is_added_by_user: data.isAddedByUser,
    modified_timestamp: data.modifiedTimestamp,
    submission_metadata: data.submissionMetadata
      ? {
          video_uuid: data.submissionMetadata.videoUuid,
          offer_ids: data.submissionMetadata.offerIds,
          destinations: data.submissionMetadata.destinations?.map(
            mapToBackendDestination
          ),
          submitting_user: data.submissionMetadata.submittingUser,
          cpc: data.submissionMetadata.cpc,
        }
      : undefined,
  };
}

/**
 * Maps a frontend Candidate (camelCase) to the backend model (snake_case).
 */
export function mapToBackendCandidate(data: Candidate): BackendCandidate {
  return {
    video_analysis_uuid: data.videoAnalysisUuid,
    identified_product_uuid: data.identifiedProductUuid,
    candidate_offer_id: data.candidateOfferId,
    candidate_status: mapToBackendCandidateStatus(data.candidateStatus),
  };
}

/**
 * Maps a frontend SubmissionMetadata (camelCase) to the backend model (snake_case).
 */
export function mapToBackendSubmissionMetadata(
  data: SubmissionMetadata
): BackendSubmissionMetadata {
  return {
    video_uuid: data.videoUuid,
    offer_ids: data.offerIds,
    destinations: data.destinations?.map(mapToBackendDestination),
    submitting_user: data.submittingUser,
    cpc: data.cpc,
  };
}
