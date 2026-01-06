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
import {Component, OnInit, signal, WritableSignal} from '@angular/core';
import {RouterOutlet} from '@angular/router';

import {DataService} from '../../services/data.service';

import {SelectionModel} from '@angular/cdk/collections';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatPaginatorModule} from '@angular/material/paginator';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSelectChange, MatSelectModule} from '@angular/material/select';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';

/**
 * Represents a single result row in the Shoppable Video table.
 * This interface defines the structure of the data expected by the table component.
 */
export interface ShoppableVideoResult {
  result_id: number;
  youtube_id: string;
  identified_product_id: number;
  is_approved: boolean;
  pushed_to_google_ads: boolean;
}

/**
 * Component for displaying a table of ShoppableVideoResult.
 * It allows filtering, and tracking of new approvals and disapprovals
 * through checkboxes.
 */
@Component({
  selector: 'results-table',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatCheckboxModule,
    MatSelectModule,
    MatFormFieldModule,
  ],
  templateUrl: './table.html',
  styleUrls: ['./table.scss'],
})
export class Table implements OnInit {
  unsavedChanges: WritableSignal<boolean> = signal(false);
  dataSource: MatTableDataSource<ShoppableVideoResult> | undefined;
  displayedColumns: string[] = [];
  constructor(private dataService: DataService) {}

  initialSelection: ShoppableVideoResult[] = [];
  allowMultiSelect = true;
  new_approvals = new SelectionModel<ShoppableVideoResult>(
    this.allowMultiSelect,
    this.initialSelection
  );
  new_disapprovals = new SelectionModel<ShoppableVideoResult>(
    this.allowMultiSelect,
    this.initialSelection
  );

  handleCheckboxChange(row: ShoppableVideoResult) {
    !row.is_approved
      ? this.new_approvals.toggle(row)
      : this.new_disapprovals.toggle(row);
  }

  applyFilter(event: MatSelectChange) {
    const filterValue = event.value;
    if (this.dataSource) {
      this.dataSource.filter = filterValue;
    }
  }

  ngOnInit() {
    this.dataService.getData<ShoppableVideoResult[]>().subscribe((response) => {
      this.dataSource = new MatTableDataSource(response);
      this.dataSource.filterPredicate = (
        data: ShoppableVideoResult,
        filter: string
      ) => {
        if (filter === 'all') {
          return true;
        }
        const isApproved = data.is_approved ? 'true' : 'false';
        return isApproved === filter;
      };
      this.displayedColumns = Object.keys(response[0]);
    });

    this.new_approvals.changed.subscribe((change) => {
      if (this.new_approvals.selected.length > 0) {
        this.unsavedChanges.set(true);
      } else if (
        this.new_disapprovals.selected.length === 0 &&
        this.new_approvals.selected.length === 0
      ) {
        this.unsavedChanges.set(false);
      }
    });

    this.new_disapprovals.changed.subscribe((change) => {
      if (this.new_disapprovals.selected.length > 0) {
        this.unsavedChanges.set(true);
      } else if (
        this.new_disapprovals.selected.length === 0 &&
        this.new_approvals.selected.length === 0
      ) {
        this.unsavedChanges.set(false);
      }
    });
  }
}
