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

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {MatIconModule} from '@angular/material/icon';
import {MatPaginatorModule, PageEvent} from '@angular/material/paginator';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {RouterModule} from '@angular/router';
import {BehaviorSubject, of} from 'rxjs';
import {
  catchError,
  debounceTime,
  map,
  startWith,
  switchMap,
} from 'rxjs/operators';

import {VideoAnalysisSummary} from '../../models';
import {VideoTitlePipe} from '../../pipes/video-display.pipe';
import {DataService} from '../../services/data.service';

/**
 * Interface for controlling the fetch pipeline trigger state.
 */
interface FetchState {
  pageIndex: number;
  pageSize: number;
  search: string;
  status: string | null;
}

/**
 * Component to display video analysis summaries in a table.
 * Supports server-side pagination, filtering, and native search.
 */
@Component({
  selector: 'app-all-results',
  standalone: true,
  imports: [
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    RouterModule,
    MatIconModule,
    VideoTitlePipe,
  ],
  templateUrl: './all-results.html',
  styleUrls: ['./all-results.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AllResults {
  private dataService = inject(DataService);

  displayedColumns: string[] = [
    'thumbnail',
    'id',
    'source',
    'identified',
    'matched',
    'approved',
    'status',
  ];
  matDataSource = new MatTableDataSource<VideoAnalysisSummary>();

  pageIndex = signal(0);
  pageSize = signal(10);
  totalCount = signal(0);
  searchQuery = signal('');
  statusFilter = signal<string | null>(null);

  private fetchTrigger$ = new BehaviorSubject<FetchState>({
    pageIndex: 0,
    pageSize: 10,
    search: '',
    status: null,
  });

  private dataState$ = this.fetchTrigger$.pipe(
    debounceTime(300), // Wait for typeahead pause before launching query
    switchMap((state) => {
      return this.dataService
        .getVideoAnalysisSummaries(
          state.pageSize,
          state.pageIndex * state.pageSize,
          state.search,
          state.status
        )
        .pipe(
          map((response) => {
            this.totalCount.set(response.totalCount);
            return {data: response.items, loading: false, error: null};
          }),
          catchError((err) => {
            console.error('Error loading data:', err);
            return of({
              data: [] as VideoAnalysisSummary[],
              loading: false,
              error: 'Failed to load data',
            });
          })
        );
    }),
    startWith({
      data: [] as VideoAnalysisSummary[],
      loading: true,
      error: null,
    })
  );

  state = toSignal(this.dataState$, {
    initialValue: {
      data: [] as VideoAnalysisSummary[],
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
    this.pageIndex.set(event.pageIndex);
    this.pageSize.set(event.pageSize);

    const current = this.fetchTrigger$.value;
    this.fetchTrigger$.next({
      ...current,
      pageIndex: event.pageIndex,
      pageSize: event.pageSize,
    });
  }

  onSearchChange(value: string) {
    const current = this.fetchTrigger$.value;
    if (current.search === value) return;

    this.searchQuery.set(value);
    this.pageIndex.set(0);

    this.fetchTrigger$.next({
      ...current,
      search: value,
      pageIndex: 0, // Reset pagination on searching
    });
  }

  onFilterChange(value: string | null) {
    const current = this.fetchTrigger$.value;
    const parsedValue = value === 'null' ? null : value;
    if (current.status === parsedValue) return;

    this.statusFilter.set(parsedValue);
    this.pageIndex.set(0);

    this.fetchTrigger$.next({
      ...current,
      status: parsedValue,
      pageIndex: 0, // Reset pagination on filtering
    });
  }

  loading = computed(() => this.state().loading);
  error = computed(() => this.state().error);
}
