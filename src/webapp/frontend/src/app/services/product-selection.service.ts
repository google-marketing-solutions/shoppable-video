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

import {SelectionModel} from '@angular/cdk/collections';
import {Injectable, inject} from '@angular/core';
import {Subject, of, Observable} from 'rxjs';
import {catchError, map} from 'rxjs/operators';
import {SubmissionDialogData} from '../components/submission-dialog/submission-dialog';
import {Candidate, MatchedProduct, Status, VideoAnalysis} from '../models';
import {AuthService} from './auth.service';
import {DataService} from './data.service';

/**
 * Represents a single selected product match within a specific video analysis.
 * This interface is used to keep track of which `MatchedProduct` is selected
 * in the context of its parent `VideoAnalysis`.
 */
export interface MatchedProductSelection {
  videoAnalysisUuid: string;
  identifiedProductUuid: string;
  match: MatchedProduct;
}

/**
 * A service to manage the selection of MatchedProducts across different VideoAnalysis.
 * It allows components to select multiple product matches and update their status
 * through the DataService. It also provides a way to subscribe to status update events.
 */
@Injectable()
export class ProductSelectionService {
  private dataService = inject(DataService);
  private authService = inject(AuthService);

  // Selection state
  matchedProductSelection = new SelectionModel<string>(true, []);
  private selectionMap = new Map<string, MatchedProductSelection>();

  // Event to notify components of status updates
  statusUpdated$ = new Subject<void>();

  getSelectionKey(video_uuid: string, match: MatchedProduct): string {
    return `${video_uuid}_${match.matchedProductOfferId}`;
  }

  toggleSelection(
    video: VideoAnalysis,
    identifiedProductUuid: string,
    match: MatchedProduct
  ) {
    const key = this.getSelectionKey(video.video.uuid, match);
    if (this.matchedProductSelection.isSelected(key)) {
      this.matchedProductSelection.deselect(key);
      this.selectionMap.delete(key);
    } else {
      this.matchedProductSelection.select(key);
      this.selectionMap.set(key, {
        videoAnalysisUuid: video.video.uuid,
        identifiedProductUuid,
        match,
      });
    }
  }

  isSelected(video: VideoAnalysis, match: MatchedProduct): boolean {
    return this.matchedProductSelection.isSelected(
      this.getSelectionKey(video.video.uuid, match)
    );
  }

  clearSelection() {
    this.matchedProductSelection.clear();
    this.selectionMap.clear();
  }

  getSelectedItems(): MatchedProductSelection[] {
    return this.matchedProductSelection.selected
      .map((key) => this.selectionMap.get(key))
      .filter((item) => item !== undefined) as MatchedProductSelection[];
  }

  updateStatus(
    status: Status,
    extraData?: SubmissionDialogData
  ): Observable<boolean> {
    const selectedItems = this.matchedProductSelection.selected
      .map((key) => this.selectionMap.get(key))
      .filter((item) => item !== undefined) as MatchedProductSelection[];

    if (selectedItems.length === 0) return of(false);

    const userEmail = this.authService.user()?.email;

    const candidates: Candidate[] = selectedItems.map((item) => ({
      videoAnalysisUuid: item.videoAnalysisUuid,
      identifiedProductUuid: item.identifiedProductUuid,
      candidateOfferId: item.match.matchedProductOfferId,
      candidateStatus: {
        status,
        user: userEmail,
        submissionMetadata: extraData
          ? {
              videoUuid: extraData.videoUuid,
              offerIds: extraData.offerIds,
              destinations: extraData.destinations,
              submittingUser: extraData.submittingUser,
            }
          : undefined,
      },
    }));

    return this.dataService.updateCandidates(candidates).pipe(
      map((result) => {
        if (result) {
          // Success
          selectedItems.forEach((item) => {
            item.match.status = status;
            const key = this.getSelectionKey(
              item.videoAnalysisUuid,
              item.match
            );
            this.matchedProductSelection.deselect(key);
            this.selectionMap.delete(key);
          });
          this.statusUpdated$.next();
          return true;
        }
        return false;
      }),
      catchError((err: unknown) => {
        console.error('Failed to update status:', err);
        return of(false); // Return observable to complete the flow
      })
    );
  }
}
