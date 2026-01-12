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
  ChangeDetectorRef,
  Component,
  ViewChild,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatIconModule} from '@angular/material/icon';
import {MatPaginator, MatPaginatorModule} from '@angular/material/paginator';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSlideToggleModule} from '@angular/material/slide-toggle';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {RouterModule} from '@angular/router';
import {of} from 'rxjs';
import {catchError, map, startWith} from 'rxjs/operators';

import {VideoAnalysis} from '../../models';
import {
  BrandPipe,
  IsBrandAtStartPipe,
  TitleRestPipe,
} from '../../pipes/product-display.pipe';
import {StatusClassPipe, StatusIconPipe} from '../../pipes/status-ui.pipe';
import {DataService} from '../../services/data.service';
import {ProductSelectionService} from '../../services/product-selection.service';
import {processIdentifiedProduct} from '../../utils/product.utils';
import {StatusFooterComponent} from '../status-footer/status-footer';

/**
 * Component to display all video analysis results in a table.
 * It allows filtering of results, specifically hiding videos with no matched products.
 * Users can paginate through the results and see product details.
 */
@Component({
  selector: 'app-all-results',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
    MatCheckboxModule,
    RouterModule,
    StatusFooterComponent,
    MatIconModule,
    StatusIconPipe,
    StatusClassPipe,
    BrandPipe,
    TitleRestPipe,
    IsBrandAtStartPipe,
  ],
  templateUrl: './all-results.html',
  styleUrls: ['./all-results.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ProductSelectionService],
})
export class AllResults {
  private dataService = inject(DataService);
  private cdr = inject(ChangeDetectorRef);
  selectionService = inject(ProductSelectionService);

  displayedColumns: string[] = ['id', 'products'];
  matDataSource = new MatTableDataSource<VideoAnalysis>();

  @ViewChild(MatPaginator) set paginator(paginator: MatPaginator) {
    this.matDataSource.paginator = paginator;
  }

  private dataState$ = this.dataService.getAllData().pipe(
    map((data) => {
      const sortedData = data.map((analysis) => ({
        ...analysis,
        identified_products: analysis.identified_products.map(
          processIdentifiedProduct
        ),
      }));
      return {data: sortedData, loading: false, error: null};
    }),
    startWith({data: [] as VideoAnalysis[], loading: true, error: null}),
    catchError((err) => {
      console.error('Error loading data:', err);
      return of({
        data: [] as VideoAnalysis[],
        loading: false,
        error: 'Failed to load data',
      });
    })
  );

  state = toSignal(this.dataState$, {
    initialValue: {data: [] as VideoAnalysis[], loading: true, error: null},
  });

  hideNoMatches = signal(true);

  constructor() {
    effect(() => {
      const state = this.state();
      const hideNoMatches = this.hideNoMatches();

      if (state.data) {
        let filteredData = state.data;

        if (hideNoMatches) {
          filteredData = state.data
            .map((video) => ({
              ...video,
              identified_products: video.identified_products.filter(
                (p) => p.matched_products && p.matched_products.length > 0
              ),
            }))
            .filter((video) => video.identified_products.length > 0);
        }

        this.matDataSource.data = filteredData;
      }
    });

    this.selectionService.statusUpdated$.subscribe(() => {
      this.cdr.markForCheck();
    });
  }

  loading = computed(() => this.state().loading);
  error = computed(() => this.state().error);
}
