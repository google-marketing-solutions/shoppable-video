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
  videoAnalysisUuid: string;
  source: string;
  video: Video;
  identifiedProducts: IdentifiedProduct[];
}

/** Represents video metadata and location. */
export interface Video {
  videoLocation: string;
  videoId: string | null;
  gcsUri: string | null;
  md5Hash: string | null;
}

/** Represents a product identified within a video. */
export interface IdentifiedProduct {
  title: string;
  description: string;
  relevanceReasoning: string;
  productUuid: string;
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

/** Enum for the status of a product match or analysis step. */
export enum Status {
  PENDING = 'Pending',
  COMPLETED = 'Completed',
  FAILED = 'Failed',
  DISAPPROVED = 'Disapproved',
  UNREVIEWED = 'Unreviewed',
}

/** Represents the status of a specific candidate product for a video analysis. */
export interface CandidateStatus {
  videoAnalysisUuid: string;
  candidateOfferId: string;
  status: Status;
  timestamp: string;
}
