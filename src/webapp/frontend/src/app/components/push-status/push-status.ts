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

import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatPaginatorModule, PageEvent} from '@angular/material/paginator';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {RouterModule} from '@angular/router';
import {of, Subject} from 'rxjs';
import {catchError, map, startWith, switchMap} from 'rxjs/operators';
import {
  AdGroupInsertionStatus,
  AdGroupInsertionStatusType,
  AdsEntityStatus,
  ProductInsertionStatus,
} from '../../models';
import {DataService} from '../../services/data.service';

interface FlattenedAdsEntityStatus {
  requestUuid: string;
  videoAnalysisUuid: string;
  timestamp: string;
  status: string;
  customerId: number | 'N/A';
  campaignId: number | 'N/A';
  adGroupId: number | 'N/A';
  products: ProductInsertionStatus[];
  errorMessage?: string;
  parentItem: AdGroupInsertionStatus;
}

/**
 * Component to display Ad Group insertion statuses.
 */
@Component({
  selector: 'app-push-status',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatButtonModule,
    RouterModule,
  ],
  templateUrl: './push-status.html',
  styleUrls: ['./push-status.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PushStatusComponent {
  protected readonly StatusType = AdGroupInsertionStatusType;

  private dataService = inject(DataService);

  displayedColumns: string[] = [
    'requestUuid',
    'videoAnalysisUuid',
    'customerId',
    'campaignId',
    'adGroupId',
    'status',
    'timestamp',
    'expand',
  ];
  matDataSource = new MatTableDataSource<FlattenedAdsEntityStatus>();

  pageIndex = signal(0);
  pageSize = signal(10);
  totalCount = signal(0);
  private page$ = new Subject<PageEvent>();

  private dataState$ = this.page$.pipe(
    startWith({pageIndex: 0, pageSize: 10} as PageEvent),
    switchMap((page) => {
      this.pageIndex.set(page.pageIndex);
      this.pageSize.set(page.pageSize);
      return this.dataService
        .getAdGroupInsertionStatuses(
          page.pageSize,
          page.pageIndex * page.pageSize
        )
        .pipe(
          map((response) => {
            this.totalCount.set(response.totalCount);
            return {data: response.items, loading: false, error: null};
          }),
          catchError((err) => {
            console.error('Error loading data:', err);
            return of({
              data: [] as AdGroupInsertionStatus[],
              loading: false,
              error: 'Failed to load data',
            });
          })
        );
    }),
    startWith({
      data: [] as AdGroupInsertionStatus[],
      loading: true,
      error: null,
    })
  );

  state = toSignal(this.dataState$, {
    initialValue: {
      data: [] as AdGroupInsertionStatus[],
      loading: true,
      error: null,
    },
  });

  constructor() {
    effect(() => {
      const state = this.state();
      if (state.data) {
        const flattenedRows: FlattenedAdsEntityStatus[] = [];
        state.data.forEach((item) => {
          if (item.adsEntities && item.adsEntities.length > 0) {
            item.adsEntities.forEach((entity) => {
              flattenedRows.push({
                requestUuid: item.requestUuid,
                videoAnalysisUuid: item.videoAnalysisUuid,
                timestamp: item.timestamp,
                status: item.status, // Top-line status for insert request
                customerId: entity.customerId,
                campaignId: entity.campaignId,
                adGroupId: entity.adGroupId,
                products: entity.products || [],
                errorMessage: entity.errorMessage,
                parentItem: item, // Keep reference if needed
              });
            });
          } else {
            flattenedRows.push({
              requestUuid: item.requestUuid,
              videoAnalysisUuid: item.videoAnalysisUuid,
              timestamp: item.timestamp,
              status: item.status,
              customerId: 'N/A',
              campaignId: 'N/A',
              adGroupId: 'N/A',
              products: [],
              parentItem: item,
            });
          }
        });
        this.matDataSource.data = flattenedRows;
      }
    });
  }

  /**
   * Handles page change events from the paginator.
   * @param event The page event containing new index and size.
   */
  onPageChange(event: PageEvent) {
    this.page$.next(event);
  }

  loading = computed(() => this.state().loading);
  error = computed(() => this.state().error);
  expandedElement = signal<FlattenedAdsEntityStatus | null>(null);
  expandedErrors = signal(new Set<AdsEntityStatus>());

  /**
   * Toggles the expanded state of an error message for a specific entity.
   * @param entity The Ads entity status to toggle.
   * @param event The click event to stop propagation.
   */
  toggleError(entity: AdsEntityStatus, event: Event) {
    event.stopPropagation();
    const current = this.expandedErrors();
    const newSet = new Set(current);
    if (newSet.has(entity)) {
      newSet.delete(entity);
    } else {
      newSet.add(entity);
    }
    this.expandedErrors.set(newSet);
  }

  /**
   * Checks if an error message is currently expanded for a given entity.
   * @param entity The Ads entity status to check.
   * @return True if expanded, false otherwise.
   */
  isErrorExpanded(entity: AdsEntityStatus): boolean {
    return this.expandedErrors().has(entity);
  }
}
