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
import {Injectable, inject, signal} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';
import {environment} from '../../environments/environment';
import {
  AdGroup,
  AdGroupInsertionStatus,
  Campaign,
  Candidate,
  Customer,
  LinkedVideoDestination,
  PaginatedAdGroupInsertionStatus,
  PaginatedVideoAnalysisSummary,
  SubmissionMetadata,
  VideoAnalysis,
} from '../models';
import {
  BackendAdGroupInsertionStatus,
  BackendLinkedVideoDestination,
  BackendPaginatedAdGroupInsertionStatus,
  BackendPaginatedVideoAnalysisSummary,
  BackendVideoAnalysis,
  mapAdGroupInsertionStatus,
  mapLinkedVideoDestination,
  mapToBackendCandidate,
  mapToBackendSubmissionMetadata,
  mapVideoAnalysis,
  mapVideoAnalysisSummary,
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
  private apiUrl = environment.apiUrl;

  activeAccount = signal<number | null>(
    localStorage.getItem('activeAccount')
      ? Number(localStorage.getItem('activeAccount'))
      : null
  );

  /**
   * Updates the active Google Ads account context and persists it to local storage.
   */
  setActiveAccount(customerId: number | null) {
    this.activeAccount.set(customerId);
    if (customerId) {
      localStorage.setItem('activeAccount', String(customerId));
    } else {
      localStorage.removeItem('activeAccount');
    }
  }

  /**
   * Fetches the list of Google Ads customer accounts accessible to the authenticated user.
   */
  getAccessibleCustomers(): Observable<{data: Customer[]}> {
    return this.http.get<{data: Customer[]}>(
      `${this.apiUrl}/reports/accessible-customers`
    );
  }

  /**
   * Retrieves a paginated list of video analysis summaries.
   */
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

  /**
   * Fetches the full analysis results for a specific video by its UUID.
   */
  getVideoAnalysis(analysisUuid: string): Observable<VideoAnalysis> {
    return this.http
      .get<BackendVideoAnalysis>(
        `${this.apiUrl}/videos/analysis/${analysisUuid}`
      )
      .pipe(map(mapVideoAnalysis));
  }

  /**
   * Updates the candidate product matches for identified products.
   */
  updateCandidates(candidates: Candidate[]): Observable<unknown> {
    return this.http.post(
      `${this.apiUrl}/candidates/update`,
      candidates.map(mapToBackendCandidate)
    );
  }

  /**
   * Searches for existing Google Ads ad groups where a specific video is already linked.
   * @param videoId The YouTube video ID.
   * @param customerId Optional customer ID to narrow the search.
   */
  getAdgroupsWithVideo(
    videoId: string,
    customerId?: number
  ): Observable<{data: LinkedVideoDestination[]}> {
    const params: {[key: string]: string} = {};
    if (this.activeAccount()) {
      params['login_customer_id'] = String(this.activeAccount()!);
    }
    if (customerId) {
      params['customer_id'] = String(customerId);
    }
    return this.http
      .get<{
        data: BackendLinkedVideoDestination[];
      }>(`${this.apiUrl}/reports/ad-groups-with-video/${videoId}`, {params})
      .pipe(
        map((response) => ({
          data: response.data.map(mapLinkedVideoDestination),
        }))
      );
  }

  /**
   * Retrieves the default CPC bid (in micros) for a specific ad group.
   */
  getAdGroupCpc(
    customerId: number,
    adGroupId: number
  ): Observable<{cpc_bid_micros: number}> {
    return this.http.get<{cpc_bid_micros: number}>(
      `${this.apiUrl}/reports/adgroup/cpc/${customerId}/${adGroupId}`
    );
  }

  /**
   * Fetches a list of campaigns for a customer, optionally filtered by type.
   */
  getCampaigns(
    customerId?: number,
    campaignTypes: string[] = ['DEMAND_GEN']
  ): Observable<{data: Campaign[]}> {
    const params: {[key: string]: string | string[]} = {};
    if (this.activeAccount()) {
      params['login_customer_id'] = String(this.activeAccount()!);
    }
    if (customerId) {
      params['customer_id'] = String(customerId);
    }
    if (campaignTypes && campaignTypes.length > 0) {
      params['campaign_types'] = campaignTypes;
    }

    return this.http.get<{data: Campaign[]}>(
      `${this.apiUrl}/reports/campaigns`,
      {
        params,
      }
    );
  }

  /**
   * Retrieves all ad groups within a specific campaign.
   */
  getAdGroupsForCampaign(
    campaignId: number,
    customerId?: number
  ): Observable<AdGroup[]> {
    const params: {[key: string]: string} = {};
    if (this.activeAccount()) {
      params['login_customer_id'] = String(this.activeAccount()!);
    }
    if (customerId) {
      params['customer_id'] = String(customerId);
    }

    return this.http.get<AdGroup[]>(
      `${this.apiUrl}/reports/ad-groups/${campaignId}`,
      {params}
    );
  }

  /**
   * Submits product-to-adgroup linking requests to the backend.
   */
  insertSubmissionRequests(
    submissionRequests: SubmissionMetadata[]
  ): Observable<unknown> {
    return this.http.post(
      `${this.apiUrl}/candidates/submission-requests`,
      submissionRequests.map(mapToBackendSubmissionMetadata)
    );
  }

  /**
   * Retrieves a paginated list of all ad group insertion statuses.
   */
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

  /**
   * Fetches insertion statuses specifically for a single video analysis.
   */
  getAdGroupInsertionStatusesForVideo(
    videoUuid: string
  ): Observable<AdGroupInsertionStatus[]> {
    return this.http
      .get<
        BackendAdGroupInsertionStatus[]
      >(`${this.apiUrl}/ad-group-insertions/status/video/${videoUuid}`)
      .pipe(map((response) => response.map(mapAdGroupInsertionStatus)));
  }

  /**
   * Lists sub-accounts under a given manager account or the current active account context.
   * @param customerId Optional customer ID to list sub-accounts for.
   * @param excludeManagers Whether to filter out manager accounts from the results.
   */
  getSubAccounts(
    customerId?: number,
    excludeManagers = false
  ): Observable<{data: Customer[]}> {
    const params: {[key: string]: string | boolean} = {};
    if (customerId) {
      params['login_customer_id'] = String(customerId);
    } else if (this.activeAccount()) {
      params['login_customer_id'] = String(this.activeAccount()!);
    }
    if (excludeManagers) {
      params['exclude_managers'] = excludeManagers;
    }
    return this.http.get<{data: Customer[]}>(
      `${this.apiUrl}/reports/sub-accounts`,
      {
        params,
      }
    );
  }
}
