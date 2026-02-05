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

import {HttpClient} from '@angular/common/http';
import {Injectable, inject} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';
import {
  Candidate,
  VideoAnalysis,
  PaginatedVideoAnalysisSummary,
  SubmissionMetadata,
  PaginatedAdGroupInsertionStatus,
} from '../models';
import {
  BackendVideoAnalysis,
  mapVideoAnalysis,
  mapVideoAnalysisSummary,
  BackendPaginatedVideoAnalysisSummary,
  mapToBackendCandidate,
  mapToBackendSubmissionMetadata,
  BackendPaginatedAdGroupInsertionStatus,
  mapAdGroupInsertionStatus,
} from '../utils/mappers';

// TODO: add tests
/**
 * Service for handling data operations, including fetching data from a
 * backend API and sharing data between different parts of the application.
 */
@Injectable({
  providedIn: 'root',
})
export class DataService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:8000/api';

  getVideoAnalysisSummaries(
    limit = 10,
    offset = 0
  ): Observable<PaginatedVideoAnalysisSummary> {
    return this.http
      .get<BackendPaginatedVideoAnalysisSummary>(
        `${this.apiUrl}/videos/analysis/summary`,
        {
          params: {
            limit: limit.toString(),
            offset: offset.toString(),
          },
        }
      )
      .pipe(
        map((response) => ({
          items: response.items.map(mapVideoAnalysisSummary),
          totalCount: response.total_count,
          limit: response.limit,
          offset: response.offset,
        }))
      );
  }

  getVideoAnalysis(analysisUuid: string): Observable<VideoAnalysis> {
    return this.http
      .get<BackendVideoAnalysis>(
        `${this.apiUrl}/videos/analysis/${analysisUuid}`
      )
      .pipe(map(mapVideoAnalysis));
  }

  updateCandidates(candidates: Candidate[]): Observable<unknown> {
    return this.http.post(
      `${this.apiUrl}/candidates/update`,
      candidates.map(mapToBackendCandidate)
    );
  }

  getAdGroupsForVideo(analysisUuid: string): Observable<
    Array<{
      id: string;
      name: string;
      status: string;
      campaign_id: string;
      customer_id: string;
    }>
  > {
    return this.http.get<
      Array<{
        id: string;
        name: string;
        status: string;
        campaign_id: string;
        customer_id: string;
      }>
    >(`${this.apiUrl}/videos/analysis/${analysisUuid}/ad-groups`);
  }

  insertSubmissionRequests(
    submissionRequests: SubmissionMetadata[]
  ): Observable<unknown> {
    return this.http.post(
      `${this.apiUrl}/candidates/submission-requests`,
      submissionRequests.map(mapToBackendSubmissionMetadata)
    );
  }

  getAdGroupInsertionStatuses(
    limit = 10,
    offset = 0
  ): Observable<PaginatedAdGroupInsertionStatus> {
    return this.http
      .get<BackendPaginatedAdGroupInsertionStatus>(
        `${this.apiUrl}/ad-group-insertions/status`,
        {
          params: {
            limit: limit.toString(),
            offset: offset.toString(),
          },
        }
      )
      .pipe(
        map((response) => ({
          items: response.items.map(mapAdGroupInsertionStatus),
          totalCount: response.total_count,
          limit: response.limit,
          offset: response.offset,
        }))
      );
  }
}
