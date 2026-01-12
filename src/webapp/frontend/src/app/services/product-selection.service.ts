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
import {Subject, forkJoin, of} from 'rxjs';
import {catchError, map} from 'rxjs/operators';
import {
  CandidateStatus,
  MatchedProduct,
  Status,
  VideoAnalysis,
} from '../models';
import {DataService} from './data.service';

/**
 * Represents a single selected product match within a specific video analysis.
 * This interface is used to keep track of which `MatchedProduct` is selected
 * in the context of its parent `VideoAnalysis`.
 */
export interface MatchedProductSelection {
  videoAnalysisUuid: string;
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

  // Selection state
  matchedProductSelection = new SelectionModel<string>(true, []);
  private selectionMap = new Map<string, MatchedProductSelection>();

  // Event to notify components of status updates
  statusUpdated$ = new Subject<void>();

  getSelectionKey(video_uuid: string, match: MatchedProduct): string {
    return `${video_uuid}_${match.matchedProductOfferId}`;
  }

  toggleSelection(video: VideoAnalysis, match: MatchedProduct) {
    const key = this.getSelectionKey(video.videoAnalysisUuid, match);
    if (this.matchedProductSelection.isSelected(key)) {
      this.matchedProductSelection.deselect(key);
      this.selectionMap.delete(key);
    } else {
      this.matchedProductSelection.select(key);
      this.selectionMap.set(key, {
        videoAnalysisUuid: video.videoAnalysisUuid,
        match,
      });
    }
  }

  isSelected(video: VideoAnalysis, match: MatchedProduct): boolean {
    return this.matchedProductSelection.isSelected(
      this.getSelectionKey(video.videoAnalysisUuid, match)
    );
  }

  clearSelection() {
    this.matchedProductSelection.clear();
    this.selectionMap.clear();
  }

  updateStatus(status: Status) {
    const selectedItems = this.matchedProductSelection.selected
      .map((key) => this.selectionMap.get(key))
      .filter((item) => item !== undefined) as MatchedProductSelection[];

    if (selectedItems.length === 0) return;

    const requests = selectedItems.map((item) => {
      const candidateStatus: CandidateStatus = {
        videoAnalysisUuid: item.videoAnalysisUuid,
        candidateOfferId: item.match.matchedProductOfferId,
        status,
        timestamp: new Date().toISOString(),
      };
      return this.dataService.addCandidateStatus(candidateStatus).pipe(
        map(() => ({success: true, item})),
        catchError((err: unknown) => of({success: false, item, error: err}))
      );
    });

    forkJoin(requests).subscribe(
      (
        results: Array<{
          success: boolean;
          item: MatchedProductSelection;
          error?: unknown;
        }>
      ) => {
        const successful = results.filter((r) => r.success);
        const failed = results.filter((r) => !r.success);

        successful.forEach((result) => {
          result.item.match.status = status;
          const key = this.getSelectionKey(
            result.item.videoAnalysisUuid,
            result.item.match
          );
          this.matchedProductSelection.deselect(key);
          this.selectionMap.delete(key);
        });

        if (failed.length > 0) {
          console.error('Failed to update status for some items:', failed);
        }

        if (successful.length > 0) {
          this.statusUpdated$.next();
        }
      }
    );
  }
}
