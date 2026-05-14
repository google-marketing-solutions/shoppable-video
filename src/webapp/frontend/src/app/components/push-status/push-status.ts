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
import {BehaviorSubject, of} from 'rxjs';
import {catchError, map, startWith, switchMap} from 'rxjs/operators';
import {
  AdGroupInsertionStatus,
  AdGroupInsertionStatusType,
  AdsEntityStatus,
} from '../../models';
import {VideoTitlePipe} from '../../pipes/video-display.pipe';
import {AuthService} from '../../services/auth.service';
import {DataService} from '../../services/data.service';

interface FetchState {
  pageIndex: number;
  pageSize: number;
  userFilter: string | null;
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
    VideoTitlePipe,
  ],
  templateUrl: './push-status.html',
  styleUrls: ['./push-status.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PushStatusComponent {
  protected readonly StatusType = AdGroupInsertionStatusType;

  private dataService = inject(DataService);
  private authService = inject(AuthService);

  displayedColumns: string[] = [
    'thumbnail',
    'video',
    'submittingUser',
    'status',
    'timestamp',
    'destinationsCount',
    'expand',
  ];
  matDataSource = new MatTableDataSource<AdGroupInsertionStatus>();

  pageIndex = signal(0);
  pageSize = signal(10);
  totalCount = signal(0);
  userFilter = signal<string | null>(null);

  private fetchTrigger$ = new BehaviorSubject<FetchState>({
    pageIndex: 0,
    pageSize: 10,
    userFilter: null,
  });

  private dataState$ = this.fetchTrigger$.pipe(
    switchMap((state) => {
      return this.dataService
        .getAdGroupInsertionStatuses(
          state.pageSize,
          state.pageIndex * state.pageSize,
          state.userFilter
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
        this.matDataSource.data = state.data;
      }
    });
  }

  /**
   * Handles page change events from the paginator.
   * @param event The page event containing new index and size.
   */
  onPageChange(event: PageEvent) {
    this.pageIndex.set(event.pageIndex);
    this.pageSize.set(event.pageSize);

    const current = this.fetchTrigger$.value;
    this.fetchTrigger$.next({
      ...current,
      pageIndex: event.pageIndex,
      pageSize: event.pageSize,
    });
  }

  onUserFilterChange(onlyMine: boolean) {
    const current = this.fetchTrigger$.value;
    const currentUserEmail = this.authService.user()?.email || null;
    const newUserFilter = onlyMine ? currentUserEmail : null;

    if (current.userFilter === newUserFilter) return;

    this.userFilter.set(newUserFilter);
    this.pageIndex.set(0);

    this.fetchTrigger$.next({
      ...current,
      userFilter: newUserFilter,
      pageIndex: 0,
    });
  }

  loading = computed(() => this.state().loading);
  error = computed(() => this.state().error);
  expandedElement = signal<AdGroupInsertionStatus | null>(null);
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

  getSuccessCount(entity: AdsEntityStatus): number {
    return (entity.products || []).filter((p) => p.status === 'SUCCESS').length;
  }

  getPendingCount(entity: AdsEntityStatus): number {
    return (entity.products || []).filter(
      (p) => p.status === 'PENDING' || p.status === 'PROCESSING'
    ).length;
  }

  getAlreadyPresentCount(entity: AdsEntityStatus): number {
    return (entity.products || []).filter((p) => p.status === 'ALREADY_PRESENT')
      .length;
  }

  getFailedCount(entity: AdsEntityStatus): number {
    return (entity.products || []).filter((p) => p.status === 'FAILED').length;
  }
}
