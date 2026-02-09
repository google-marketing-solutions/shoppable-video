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
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatIconModule} from '@angular/material/icon';
import {MatPaginatorModule, PageEvent} from '@angular/material/paginator';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSlideToggleModule} from '@angular/material/slide-toggle';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {RouterModule} from '@angular/router';
import {of, Subject} from 'rxjs';
import {catchError, map, startWith, switchMap} from 'rxjs/operators';

import {VideoAnalysisSummary} from '../../models';
import {VideoTitlePipe} from '../../pipes/video-display.pipe';
import {DataService} from '../../services/data.service';

/**
 * Component to display video analysis summaries in a table.
 * Supports server-side pagination.
 */
@Component({
  selector: 'app-all-results',
  standalone: true,
  imports: [
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
    MatCheckboxModule,
    RouterModule,
    MatIconModule,
    VideoTitlePipe
],
  templateUrl: './all-results.html',
  styleUrls: ['./all-results.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AllResults {
  private dataService = inject(DataService);

  displayedColumns: string[] = [
    'id',
    'identified',
    'matched',
    'approved',
    'disapproved',
    'unreviewed',
  ];
  matDataSource = new MatTableDataSource<VideoAnalysisSummary>();

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
        .getVideoAnalysisSummaries(
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
    this.page$.next(event);
  }

  loading = computed(() => this.state().loading);
  error = computed(() => this.state().error);
}
