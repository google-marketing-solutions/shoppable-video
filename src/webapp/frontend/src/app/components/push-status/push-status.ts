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
} from '../../models';
import {DataService} from '../../services/data.service';

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
export class PushStatusComponents {
  protected readonly StatusType = AdGroupInsertionStatusType;

  private dataService = inject(DataService);

  displayedColumns: string[] = ['requestUuid', 'videoAnalysisUuid', 'timestamp', 'status', 'expand'];
  matDataSource = new MatTableDataSource<AdGroupInsertionStatus>();

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
        this.matDataSource.data = state.data;
      }
    });
  }

  onPageChange(event: PageEvent) {
    this.page$.next(event);
  }

  loading = computed(() => this.state().loading);
  error = computed(() => this.state().error);
  expandedElement = signal<AdGroupInsertionStatus | null>(null);
  expandedErrors = signal(new Set<AdsEntityStatus>());

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
}
