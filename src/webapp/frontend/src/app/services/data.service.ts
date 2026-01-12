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
import {CandidateStatus, VideoAnalysis} from '../models';

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

  getAllData(): Observable<VideoAnalysis[]> {
    return this.http.get<VideoAnalysis[]>(`${this.apiUrl}/video-analysis`);
  }

  getYoutubeVideo(videoId: string): Observable<VideoAnalysis> {
    return this.http.get<VideoAnalysis>(
      `${this.apiUrl}/video-analysis/video/${videoId}`
    );
  }

  getGcsVideo(analysisUuid: string): Observable<VideoAnalysis> {
    return this.http.get<VideoAnalysis>(
      `${this.apiUrl}/video-analysis/${analysisUuid}`
    );
  }

  getCandidateStatus(): Observable<CandidateStatus[]> {
    return this.http.get<CandidateStatus[]>(
      `${this.apiUrl}/candidate-status/latest`
    );
  }

  getCandidateStatusByStatus(status: string): Observable<CandidateStatus[]> {
    return this.http.get<CandidateStatus[]>(
      `${this.apiUrl}/candidate-status/${status}`
    );
  }

  addCandidateStatus(status: CandidateStatus): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/candidate-status/add`, status);
  }

  getAnalysisCandidateStatus(
    analysisId: string
  ): Observable<CandidateStatus[]> {
    return this.http.get<CandidateStatus[]>(
      `${this.apiUrl}/candidate-status/analysis/${analysisId}`
    );
  }
}
