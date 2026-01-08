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
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTableModule} from '@angular/material/table';
import {ActivatedRoute, Router} from '@angular/router';
import {forkJoin} from 'rxjs';
import {ROUTES} from '../../core/routing/routes';
import {PARAMS} from '../../core/routing/params';
import {CandidateStatus, Status} from '../../models';
import {DataService} from '../../services/data.service';
import {StatusFooterComponent} from '../status-footer/status-footer';

/**
 * Component for displaying and managing the status of candidate video analyses.
 * It allows filtering by status, selecting multiple candidates, and updating their status.
 */
@Component({
  selector: 'app-status',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatCheckboxModule,
    StatusFooterComponent,
  ],
  templateUrl: './status.html',
  styleUrls: ['./status.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatusComponent implements OnInit {
  private dataService = inject(DataService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  displayedColumns: string[] = [
    'select',
    'video_analysis_uuid',
    'candidate_offer_id',
    'status',
    'timestamp',
  ];
  dataSource = signal<CandidateStatus[]>([]);
  loading = signal(true);
  selection = new SelectionModel<CandidateStatus>(true, []);

  ngOnInit() {
    this.route.paramMap.subscribe((params) => {
      const status = params.get(PARAMS.STATUS);
      if (status) {
        const isValidStatus = Object.values(Status).some(
          (s) => s.toLowerCase() === status.toLowerCase()
        );
        if (!isValidStatus) {
          this.router.navigate(['/' + ROUTES.STATUS]);
          return;
        }
      }
      this.loadData(status);
    });
  }

  loadData(status: string | null = null) {
    this.loading.set(true);
    const request$ = status
      ? this.dataService.getCandidateStatusByStatus(status)
      : this.dataService.getCandidateStatus();

    request$.subscribe((data) => {
      this.dataSource.set(data);
      this.loading.set(false);
      this.selection.clear();
    });
  }

  isAllSelected() {
    const numSelected = this.selection.selected.length;
    const numRows = this.dataSource().length;
    return numSelected === numRows;
  }

  masterToggle() {
    if (this.isAllSelected()) {
      this.selection.clear();
    } else {
      this.dataSource().forEach((row) => this.selection.select(row));
    }
  }

  checkboxLabel(row?: CandidateStatus): string {
    if (!row) {
      return `${this.isAllSelected() ? 'deselect' : 'select'} all`;
    }
    return `${this.selection.isSelected(row) ? 'deselect' : 'select'} row ${row.candidate_offer_id}`;
  }

  getStatusClass(status: Status): string {
    switch (status) {
      case Status.COMPLETED:
        return 'status-success';
      case Status.PENDING:
        return 'status-pending';
      case Status.FAILED:
      case Status.DISAPPROVED:
        return 'status-error';
      default:
        return 'status-neutral';
    }
  }

  handleStatusUpdate(newStatus: Status) {
    if (!newStatus || this.selection.isEmpty()) return;

    const selectedItems = this.selection.selected;
    const updateRequests = selectedItems.map((item) => {
      const statusUpdate: CandidateStatus = {
        ...item,
        status: newStatus,
        timestamp: new Date().toISOString(),
      };
      return this.dataService.addCandidateStatus(statusUpdate);
    });

    this.loading.set(true);
    forkJoin(updateRequests).subscribe({
      next: () => {
        const currentStatus = this.route.snapshot.paramMap.get(PARAMS.STATUS);
        this.loadData(currentStatus);
      },
      error: (err) => {
        console.error('Error updating status', err);
        this.loading.set(false);
      },
    });
  }
}
