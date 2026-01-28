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

/** Represents the result of a video analysis process. */
export interface VideoAnalysis {
  video: Video;
  identifiedProducts: IdentifiedProduct[];
}

/** Represents video metadata and location. */
export interface Video {
  uuid: string;
  source: string;
  videoId: string | null;
  gcsUri: string | null;
  md5Hash: string | null;
  metadata?: VideoMetadata | null;
}

/** Represents metadata for a video. */
export interface VideoMetadata {
  title?: string | null;
  description?: string | null;
}

/** Represents a summary of a video analysis. */
export interface VideoAnalysisSummary {
  video: Video;
  identifiedProductsCount: number;
  matchedProductsCount: number;
  approvedProductsCount: number;
  disapprovedProductsCount: number;
  unreviewedProductsCount: number;
}

/** A paginated response for video analysis summaries. */
export interface PaginatedVideoAnalysisSummary {
  items: VideoAnalysisSummary[];
  totalCount: number;
  limit: number;
  offset: number;
}

/** Represents a product identified within a video. */
export interface IdentifiedProduct {
  productUuid: string;
  title: string;
  description: string;
  relevanceReasoning: string;
  videoTimestamp: number;
  matchedProducts: MatchedProduct[];
}

/** Represents a candidate product matched against an identified product. */
export interface MatchedProduct {
  matchedProductOfferId: string;
  matchedProductTitle: string;
  matchedProductBrand: string;
  timestamp: string;
  distance: number;
  status: string;
}

/** A view model for displaying product information in the UI. */
export interface VideoProductViewModel {
  identifiedProductTitle: string;
  offerId: string;
  distance: number;
}

/** Represents additional metadata for submission status. */
export interface SubmissionMetadata {
  videoUuid?: string;
  offerIds?: string;
  destinations?: string;
  submittingUser?: string;
}

/** Enum for the status of a product match or analysis step. */
export enum Status {
  APPROVED = 'APPROVED',
  DISAPPROVED = 'DISAPPROVED',
  UNREVIEWED = 'UNREVIEWED',
}

/** Represents the status of a specific candidate product. */
export interface CandidateStatus {
  status: Status;
  user?: string | null;
  isAddedByUser?: boolean | null;
  modifiedTimestamp?: string | null;
  submissionMetadata?: SubmissionMetadata | null;
}

/** Represents a candidate product to be added/updated. */
export interface Candidate {
  videoAnalysisUuid: string;
  identifiedProductUuid: string;
  candidateOfferId: string;
  candidateStatus: CandidateStatus;
}
